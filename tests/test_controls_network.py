# Unit tests for the network control evaluation layer in CRIS-SME.
from cris_sme.controls.network_controls import evaluate_network_controls
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
    organization_id: str = "sme-net-001",
    organization_name: str = "Network Test SME Ltd",
    sector: str = "Financial Services",
    internet_exposed_rdp_assets: int = 0,
    internet_exposed_ssh_assets: int = 0,
    permissive_nsg_rules: int = 0,
    public_storage_endpoints: int = 0,
    private_endpoints_required: int = 0,
    private_endpoints_configured: int = 0,
) -> CloudProfile:
    """Create compact synthetic cloud profiles for network control testing."""
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
            internet_exposed_rdp_assets=internet_exposed_rdp_assets,
            internet_exposed_ssh_assets=internet_exposed_ssh_assets,
            permissive_nsg_rules=permissive_nsg_rules,
            public_storage_endpoints=public_storage_endpoints,
            private_endpoints_required=private_endpoints_required,
            private_endpoints_configured=private_endpoints_configured,
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


def test_evaluate_network_controls_returns_no_findings_for_strong_posture() -> None:
    findings = evaluate_network_controls([make_profile(private_endpoints_required=2, private_endpoints_configured=2)])

    assert findings == []


def test_evaluate_network_controls_flags_public_admin_exposure_as_critical() -> None:
    findings = evaluate_network_controls([make_profile(internet_exposed_rdp_assets=1)])

    remote_admin = next(item for item in findings if item.control_id == "NET-001")
    assert remote_admin.severity == FindingSeverity.CRITICAL
    assert remote_admin.is_compliant is False


def test_evaluate_network_controls_generates_multiple_findings_for_broader_weakness() -> None:
    findings = evaluate_network_controls(
        [
            make_profile(
                internet_exposed_ssh_assets=2,
                permissive_nsg_rules=2,
                public_storage_endpoints=1,
                private_endpoints_required=3,
                private_endpoints_configured=1,
            )
        ]
    )

    control_ids = {item.control_id for item in findings}
    assert {"NET-001", "NET-002", "NET-003", "NET-004"} <= control_ids
