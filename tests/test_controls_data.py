# Unit tests for the data control evaluation layer in CRIS-SME.
from cris_sme.controls.data_controls import evaluate_data_controls
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
    organization_id: str = "sme-data-001",
    organization_name: str = "Data Test SME Ltd",
    sector: str = "Financial Services",
    public_storage_assets: int = 0,
    unencrypted_data_stores: int = 0,
    backup_coverage_ratio: float = 1.0,
    retention_policy_coverage_ratio: float = 1.0,
    key_vault_mfa_enabled: bool = True,
    key_vault_purge_protection_enabled: bool = True,
    key_vault_count: int = 1,
    key_vault_purge_protected_count: int = 1,
    key_vault_posture_state: str = "observed",
) -> CloudProfile:
    """Create compact synthetic cloud profiles for data control testing."""
    return CloudProfile(
        organization_id=organization_id,
        organization_name=organization_name,
        provider="azure",
        sector=sector,
        tenant_scope="Tenant root / Entra ID",
        iam=IamProfile(
            privileged_accounts=2,
            privileged_accounts_without_mfa=0,
            overprivileged_accounts=0,
            stale_service_principals=0,
            rbac_review_age_days=30,
            conditional_access_enforced_for_admins=True,
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
            public_storage_assets=public_storage_assets,
            unencrypted_data_stores=unencrypted_data_stores,
            backup_coverage_ratio=backup_coverage_ratio,
            retention_policy_coverage_ratio=retention_policy_coverage_ratio,
            key_vault_mfa_enabled=key_vault_mfa_enabled,
            key_vault_purge_protection_enabled=key_vault_purge_protection_enabled,
            key_vault_count=key_vault_count,
            key_vault_purge_protected_count=key_vault_purge_protected_count,
            key_vault_posture_state=key_vault_posture_state,
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


def test_evaluate_data_controls_returns_no_findings_for_strong_posture() -> None:
    findings = evaluate_data_controls([make_profile()])
    assert findings == []


def test_evaluate_data_controls_flags_public_storage_access() -> None:
    findings = evaluate_data_controls([make_profile(public_storage_assets=1)])
    storage_finding = next(item for item in findings if item.control_id == "DATA-001")
    assert storage_finding.severity == FindingSeverity.HIGH
    assert storage_finding.is_compliant is False


def test_evaluate_data_controls_generates_multiple_findings_for_broader_weakness() -> None:
    findings = evaluate_data_controls(
        [
            make_profile(
                public_storage_assets=1,
                unencrypted_data_stores=1,
                backup_coverage_ratio=0.6,
                retention_policy_coverage_ratio=0.65,
                key_vault_mfa_enabled=False,
                key_vault_purge_protection_enabled=False,
            )
        ]
    )

    control_ids = {item.control_id for item in findings}
    assert {"DATA-001", "DATA-002", "DATA-003", "DATA-004"} <= control_ids


def test_evaluate_data_controls_requires_all_key_vaults_to_have_purge_protection() -> None:
    findings = evaluate_data_controls(
        [
            make_profile(
                key_vault_purge_protection_enabled=False,
                key_vault_count=5,
                key_vault_purge_protected_count=1,
            )
        ]
    )

    key_vault_finding = next(item for item in findings if item.control_id == "DATA-004")
    assert key_vault_finding.is_compliant is False
    assert key_vault_finding.metadata["key_vault_count"] == 5
    assert key_vault_finding.metadata["key_vault_purge_protected_count"] == 1
    assert any("1 of 5 key vault" in item for item in key_vault_finding.evidence)


def test_evaluate_data_controls_treats_no_key_vaults_as_not_applicable() -> None:
    findings = evaluate_data_controls(
        [
            make_profile(
                key_vault_count=0,
                key_vault_purge_protected_count=0,
                key_vault_posture_state="not_applicable",
            )
        ]
    )

    assert all(item.control_id != "DATA-004" for item in findings)
