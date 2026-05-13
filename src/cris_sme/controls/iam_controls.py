# IAM governance controls that convert synthetic Azure posture into explainable findings.
from __future__ import annotations

from cris_sme.controls.common import build_control_finding
from cris_sme.models.cloud_profile import CloudProfile
from cris_sme.models.finding import Finding, FindingSeverity


def evaluate_iam_controls(profiles: list[CloudProfile]) -> list[Finding]:
    """Evaluate IAM controls across synthetic SME profiles."""
    findings: list[Finding] = []

    for profile in profiles:
        findings.extend(_evaluate_privileged_mfa(profile))
        findings.extend(_evaluate_overprivileged_accounts(profile))
        findings.extend(_evaluate_stale_service_principals(profile))
        findings.extend(_evaluate_rbac_review_freshness(profile))
        findings.extend(_evaluate_identity_observability(profile))

    return findings


def _evaluate_privileged_mfa(profile: CloudProfile) -> list[Finding]:
    """Check whether privileged identities are protected with MFA and admin CA."""
    iam = profile.iam
    conditional_access_accessible = profile.metadata.get("conditional_access_accessible")
    conditional_access_unobservable = conditional_access_accessible is False
    conditional_access_metadata = {
        "conditional_access_accessible": conditional_access_accessible,
        "conditional_access_policy_count": profile.metadata.get(
            "conditional_access_policy_count"
        ),
        "conditional_access_enforced_for_admins": (
            iam.conditional_access_enforced_for_admins
        ),
    }

    if (
        iam.privileged_accounts_without_mfa == 0
        and iam.conditional_access_enforced_for_admins
    ):
        return [
            build_control_finding(
                profile=profile,
                control_id="IAM-001",
                severity=FindingSeverity.MEDIUM,
                evidence=[
                    "No privileged accounts without MFA were identified",
                    "Conditional access is enforced for privileged administrators",
                ],
                is_compliant=True,
                confidence=0.95,
                exposure=0.35,
                remediation_effort=0.2,
                generated_by="iam_controls",
                metadata=conditional_access_metadata,
                title_override="Privileged role assignments are protected with MFA enforcement",
            )
        ]

    evidence = []
    if iam.privileged_accounts_without_mfa > 0:
        evidence.append(
            f"{iam.privileged_accounts_without_mfa} privileged account(s) do not have MFA enabled"
        )
    if conditional_access_unobservable:
        evidence.append(
            "Conditional access for privileged administrators was not observable and is treated as unmet for deterministic scoring"
        )
    elif not iam.conditional_access_enforced_for_admins:
        evidence.append("Conditional access is not enforced for privileged administrators")

    severity = (
        FindingSeverity.CRITICAL
        if iam.privileged_accounts_without_mfa >= 2
        or not iam.conditional_access_enforced_for_admins
        else FindingSeverity.HIGH
    )

    return [
        build_control_finding(
            profile=profile,
            control_id="IAM-001",
            severity=severity,
            evidence=evidence,
            is_compliant=False,
            confidence=0.96,
            exposure=0.9,
            remediation_effort=0.35,
            generated_by="iam_controls",
            metadata=conditional_access_metadata,
        )
    ]


def _evaluate_overprivileged_accounts(profile: CloudProfile) -> list[Finding]:
    """Check for excessive privilege assignment concentration."""
    count = profile.iam.overprivileged_accounts
    if count == 0:
        return []

    privileged_user_assignments = profile.iam.privileged_user_assignments
    privileged_service_principal_assignments = (
        profile.iam.privileged_service_principal_assignments
    )

    severity = FindingSeverity.HIGH if count >= 2 else FindingSeverity.MEDIUM

    return [
        build_control_finding(
            profile=profile,
            control_id="IAM-002",
            severity=severity,
            evidence=[
                f"{count} account(s) appear to hold privileges above operational need",
                (
                    f"Observed privileged assignment mix: "
                    f"{privileged_user_assignments} user assignment(s), "
                    f"{privileged_service_principal_assignments} service principal assignment(s)"
                ),
            ],
            is_compliant=False,
            confidence=0.84,
            exposure=0.75,
            remediation_effort=0.45,
            generated_by="iam_controls",
        )
    ]


def _evaluate_stale_service_principals(profile: CloudProfile) -> list[Finding]:
    """Check for stale non-human identities that may increase attack surface."""
    stale_count = profile.iam.stale_service_principals
    disabled_count = profile.iam.disabled_service_principals
    total_count = stale_count + disabled_count
    if total_count == 0:
        return []

    severity = FindingSeverity.HIGH if total_count >= 3 else FindingSeverity.MEDIUM

    evidence = []
    if stale_count:
        evidence.append(
            f"{stale_count} stale service principal(s) or credential set(s) were identified"
        )
    if disabled_count:
        evidence.append(
            f"{disabled_count} role-assigned service principal(s) were disabled and should be reviewed"
        )

    return [
        build_control_finding(
            profile=profile,
            control_id="IAM-003",
            severity=severity,
            evidence=evidence,
            is_compliant=False,
            confidence=0.8,
            exposure=0.65,
            remediation_effort=0.55,
            generated_by="iam_controls",
        )
    ]


def _evaluate_identity_observability(profile: CloudProfile) -> list[Finding]:
    """Flag when the identity evidence path is partial rather than fully tenant-observed."""
    if profile.iam.identity_observability == "full":
        return []

    return [
        build_control_finding(
            profile=profile,
            control_id="IAM-005",
            severity=FindingSeverity.LOW,
            evidence=_build_identity_observability_evidence(profile),
            is_compliant=False,
            confidence=0.92,
            exposure=0.3,
            remediation_effort=0.2,
            generated_by="iam_controls",
        )
    ]


def _build_identity_observability_evidence(profile: CloudProfile) -> list[str]:
    """Build explicit evidence for the current identity observability boundary."""
    iam = profile.iam
    evidence = [
        "Subscription-scoped evidence was collected for privileged role assignments",
        "Tenant-wide Entra controls such as conditional access were not directly observable in this run",
    ]
    if iam.signed_in_user_directory_roles > 0:
        evidence.append(
            f"The signed-in assessment identity exposed {iam.signed_in_user_directory_roles} Entra directory role(s)"
        )
    if iam.signed_in_user_is_directory_admin:
        evidence.append(
            "The signed-in assessment identity appears to hold a privileged Entra directory role"
        )
    if iam.directory_role_catalog_visible:
        evidence.append(
            f"The tenant directory-role catalog was partially visible with {iam.visible_directory_role_catalog_entries} active role entry(ies)"
        )
    return evidence


def _evaluate_rbac_review_freshness(profile: CloudProfile) -> list[Finding]:
    """Check whether privileged access reviews appear operationally current."""
    iam = profile.iam
    age_days = iam.rbac_review_age_days
    if age_days <= 90:
        return []

    severity = FindingSeverity.MEDIUM if age_days <= 180 else FindingSeverity.HIGH
    evidence = [
        f"Last RBAC review is approximately {age_days} day(s) old",
    ]
    if iam.rbac_review_api_accessible:
        evidence.append(
            (
                f"Observed {iam.rbac_review_definition_count} access review "
                f"definition(s); scope classified as {iam.rbac_review_scope}"
            )
        )
        if iam.rbac_review_scope == "generic_or_unknown":
            evidence.append(
                "Access review evidence is generic; privileged Azure RBAC coverage should be manually confirmed"
            )
    else:
        evidence.append("Access review evidence was not observable from Microsoft Graph")

    return [
        build_control_finding(
            profile=profile,
            control_id="IAM-004",
            severity=severity,
            evidence=evidence,
            is_compliant=False,
            confidence=0.78,
            exposure=0.5,
            remediation_effort=0.3,
            generated_by="iam_controls",
            metadata={
                "rbac_review_api_accessible": iam.rbac_review_api_accessible,
                "rbac_review_definition_count": iam.rbac_review_definition_count,
                "rbac_review_privileged_scope_count": (
                    iam.rbac_review_privileged_scope_count
                ),
                "rbac_review_scope": iam.rbac_review_scope,
            },
        )
    ]
