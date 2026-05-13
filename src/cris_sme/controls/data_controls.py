# Data governance controls that convert synthetic cloud posture into explainable findings.
from __future__ import annotations

from cris_sme.models.cloud_profile import CloudProfile
from cris_sme.models.finding import Finding, FindingSeverity
from cris_sme.controls.common import build_control_finding


def evaluate_data_controls(profiles: list[CloudProfile]) -> list[Finding]:
    """Evaluate data protection controls across synthetic SME profiles."""
    findings: list[Finding] = []

    for profile in profiles:
        findings.extend(_evaluate_public_storage_access(profile))
        findings.extend(_evaluate_encryption_posture(profile))
        findings.extend(_evaluate_backup_and_retention(profile))
        findings.extend(_evaluate_key_vault_protections(profile))

    return findings


def _evaluate_public_storage_access(profile: CloudProfile) -> list[Finding]:
    """Check whether storage services are publicly accessible."""
    count = profile.data.public_storage_assets
    if count == 0:
        return []

    severity = FindingSeverity.CRITICAL if count >= 2 else FindingSeverity.HIGH
    return [
        build_control_finding(
            profile=profile,
            control_id="DATA-001",
            severity=severity,
            evidence=[f"{count} storage asset(s) allow public access"],
            is_compliant=False,
            confidence=0.92,
            exposure=0.95,
            remediation_effort=0.3,
            generated_by="data_controls",
        )
    ]


def _evaluate_encryption_posture(profile: CloudProfile) -> list[Finding]:
    """Check whether data stores lack encryption safeguards."""
    count = profile.data.unencrypted_data_stores
    if count == 0:
        return []

    severity = FindingSeverity.HIGH if count == 1 else FindingSeverity.CRITICAL
    return [
        build_control_finding(
            profile=profile,
            control_id="DATA-002",
            severity=severity,
            evidence=[f"{count} data store(s) appear to be unencrypted at rest"],
            is_compliant=False,
            confidence=0.9,
            exposure=0.7,
            remediation_effort=0.4,
            generated_by="data_controls",
        )
    ]


def _evaluate_backup_and_retention(profile: CloudProfile) -> list[Finding]:
    """Check backup and retention coverage for business-critical data."""
    backup_ratio = profile.data.backup_coverage_ratio
    retention_ratio = profile.data.retention_policy_coverage_ratio

    if backup_ratio >= 0.9 and retention_ratio >= 0.9:
        return []

    evidence = []
    if backup_ratio < 0.9:
        evidence.append(f"Backup coverage is only {backup_ratio:.0%}")
    if retention_ratio < 0.9:
        evidence.append(f"Retention policy coverage is only {retention_ratio:.0%}")

    severity = FindingSeverity.HIGH if min(backup_ratio, retention_ratio) < 0.7 else FindingSeverity.MEDIUM
    return [
        build_control_finding(
            profile=profile,
            control_id="DATA-003",
            severity=severity,
            evidence=evidence,
            is_compliant=False,
            confidence=0.85,
            exposure=0.5,
            remediation_effort=0.55,
            generated_by="data_controls",
        )
    ]


def _evaluate_key_vault_protections(profile: CloudProfile) -> list[Finding]:
    """Check whether sensitive key management controls are adequately protected."""
    data_profile = profile.data
    evidence: list[str] = []
    metadata = {
        "key_vault_count": data_profile.key_vault_count,
        "key_vault_purge_protected_count": (
            data_profile.key_vault_purge_protected_count
        ),
        "key_vault_posture_state": data_profile.key_vault_posture_state,
    }

    if data_profile.key_vault_posture_state == "not_applicable":
        return []

    if not data_profile.key_vault_mfa_enabled:
        evidence.append("Key vault administrative access is not protected with MFA")
    if not data_profile.key_vault_purge_protection_enabled:
        if data_profile.key_vault_posture_state == "unavailable":
            evidence.append("Key vault purge protection could not be verified")
        elif data_profile.key_vault_count > 0:
            evidence.append(
                (
                    f"{data_profile.key_vault_purge_protected_count} of "
                    f"{data_profile.key_vault_count} key vault(s) have purge "
                    "protection enabled"
                )
            )
        else:
            evidence.append("Key vault purge protection is not enabled")

    if not evidence:
        return []

    severity = (
        FindingSeverity.HIGH
        if not data_profile.key_vault_mfa_enabled
        else FindingSeverity.MEDIUM
    )
    return [
        build_control_finding(
            profile=profile,
            control_id="DATA-004",
            severity=severity,
            evidence=evidence,
            is_compliant=False,
            confidence=0.88,
            exposure=0.6,
            remediation_effort=0.35,
            generated_by="data_controls",
            metadata=metadata,
        )
    ]
