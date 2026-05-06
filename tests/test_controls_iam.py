# Unit tests for the IAM control evaluation layer in CRIS-SME.
from cris_sme.controls.iam_controls import evaluate_iam_controls
from cris_sme.models.cloud_profile import (
    CloudProfile,
    ComputeProfile,
    DataProfile,
    GovernanceProfile,
    IamProfile,
    MonitoringProfile,
    NetworkProfile,
)
from cris_sme.models.finding import FindingSeverity


def make_profile(
    *,
    organization_id: str = "sme-test-001",
    organization_name: str = "Test SME Ltd",
    sector: str = "Financial Services",
    privileged_accounts: int = 3,
    privileged_accounts_without_mfa: int = 0,
    overprivileged_accounts: int = 0,
    stale_service_principals: int = 0,
    disabled_service_principals: int = 0,
    rbac_review_age_days: int = 30,
    conditional_access_enforced_for_admins: bool = True,
    privileged_user_assignments: int = 0,
    privileged_service_principal_assignments: int = 0,
    signed_in_user_directory_roles: int = 0,
    signed_in_user_is_directory_admin: bool = False,
    visible_directory_role_catalog_entries: int = 0,
    directory_role_catalog_visible: bool = False,
    identity_observability: str = "full",
) -> CloudProfile:
    """Create compact synthetic cloud profiles for IAM control testing."""
    return CloudProfile(
        organization_id=organization_id,
        organization_name=organization_name,
        provider="azure",
        sector=sector,
        tenant_scope="Tenant root / Entra ID",
        iam=IamProfile(
            privileged_accounts=privileged_accounts,
            privileged_accounts_without_mfa=privileged_accounts_without_mfa,
            overprivileged_accounts=overprivileged_accounts,
            stale_service_principals=stale_service_principals,
            disabled_service_principals=disabled_service_principals,
            rbac_review_age_days=rbac_review_age_days,
            conditional_access_enforced_for_admins=conditional_access_enforced_for_admins,
            privileged_user_assignments=privileged_user_assignments,
            privileged_service_principal_assignments=privileged_service_principal_assignments,
            signed_in_user_directory_roles=signed_in_user_directory_roles,
            signed_in_user_is_directory_admin=signed_in_user_is_directory_admin,
            visible_directory_role_catalog_entries=visible_directory_role_catalog_entries,
            directory_role_catalog_visible=directory_role_catalog_visible,
            identity_observability=identity_observability,
        ),
        network=NetworkProfile(
            internet_exposed_rdp_assets=0,
            internet_exposed_ssh_assets=0,
            permissive_nsg_rules=0,
            public_storage_endpoints=0,
            private_endpoints_required=0,
            private_endpoints_configured=0,
        ),
        data=DataProfile(
            public_storage_assets=0,
            unencrypted_data_stores=0,
            backup_coverage_ratio=1.0,
            retention_policy_coverage_ratio=1.0,
            key_vault_mfa_enabled=True,
            key_vault_purge_protection_enabled=True,
        ),
        monitoring=MonitoringProfile(
            activity_log_retention_days=180,
            critical_alert_coverage_ratio=1.0,
            defender_coverage_ratio=1.0,
            centralized_logging_enabled=True,
            incident_response_runbooks_enabled=True,
        ),
        compute=ComputeProfile(
            unpatched_critical_vms=0,
            endpoint_protection_coverage_ratio=1.0,
            hardened_baseline_coverage_ratio=1.0,
            workload_backup_agent_coverage_ratio=1.0,
        ),
        governance=GovernanceProfile(
            tagging_coverage_ratio=1.0,
            budget_alerts_enabled=True,
            policy_assignment_coverage_ratio=1.0,
            orphaned_resource_count=0,
        ),
        metadata={"profile_source": "test"},
    )


def test_evaluate_iam_controls_returns_compliant_mfa_finding_for_strong_posture() -> None:
    findings = evaluate_iam_controls([make_profile()])

    assert len(findings) == 1
    assert findings[0].control_id == "IAM-001"
    assert findings[0].is_compliant is True


def test_evaluate_iam_controls_flags_missing_mfa_as_high_priority_risk() -> None:
    findings = evaluate_iam_controls(
        [
            make_profile(
                privileged_accounts_without_mfa=2,
                conditional_access_enforced_for_admins=False,
            )
        ]
    )

    mfa_finding = next(item for item in findings if item.control_id == "IAM-001")
    assert mfa_finding.is_compliant is False
    assert mfa_finding.severity == FindingSeverity.CRITICAL


def test_evaluate_iam_controls_treats_unobservable_conditional_access_as_unmet() -> None:
    profile = make_profile(
        privileged_accounts_without_mfa=0,
        conditional_access_enforced_for_admins=False,
    )
    profile.metadata["conditional_access_accessible"] = False
    profile.metadata["conditional_access_policy_count"] = 0

    findings = evaluate_iam_controls([profile])

    mfa_finding = next(item for item in findings if item.control_id == "IAM-001")
    assert mfa_finding.is_compliant is False
    assert mfa_finding.metadata["conditional_access_accessible"] is False
    assert any("not observable" in item for item in mfa_finding.evidence)


def test_evaluate_iam_controls_generates_multiple_findings_for_broader_iam_weakness() -> None:
    findings = evaluate_iam_controls(
        [
            make_profile(
                privileged_accounts_without_mfa=1,
                overprivileged_accounts=2,
                stale_service_principals=3,
                rbac_review_age_days=200,
                identity_observability="partial",
            )
        ]
    )

    control_ids = {item.control_id for item in findings}
    assert {"IAM-001", "IAM-002", "IAM-003", "IAM-004", "IAM-005"} <= control_ids


def test_evaluate_iam_controls_flags_partial_identity_observability() -> None:
    findings = evaluate_iam_controls(
        [
            make_profile(
                identity_observability="partial",
                signed_in_user_directory_roles=2,
                signed_in_user_is_directory_admin=True,
                visible_directory_role_catalog_entries=4,
                directory_role_catalog_visible=True,
            )
        ]
    )

    observability_finding = next(item for item in findings if item.control_id == "IAM-005")
    assert observability_finding.is_compliant is False
    assert observability_finding.severity == FindingSeverity.LOW
    assert any("Entra directory role" in evidence for evidence in observability_finding.evidence)
    assert any("directory-role catalog" in evidence for evidence in observability_finding.evidence)


def test_evaluate_iam_controls_includes_disabled_service_principals_in_hygiene_risk() -> None:
    findings = evaluate_iam_controls(
        [
            make_profile(
                stale_service_principals=1,
                disabled_service_principals=1,
            )
        ]
    )

    hygiene_finding = next(item for item in findings if item.control_id == "IAM-003")
    assert hygiene_finding.is_compliant is False
    assert any("disabled" in evidence for evidence in hygiene_finding.evidence)
