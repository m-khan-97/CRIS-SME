# Unit tests for the compute control evaluation layer in CRIS-SME.
from cris_sme.controls.compute_controls import evaluate_compute_controls
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
    organization_id: str = "sme-cmp-001",
    organization_name: str = "Compute Test SME Ltd",
    sector: str = "Financial Services",
    unpatched_critical_vms: int = 0,
    endpoint_protection_coverage_ratio: float = 1.0,
    hardened_baseline_coverage_ratio: float = 1.0,
    workload_backup_agent_coverage_ratio: float = 1.0,
    linux_password_auth_enabled_vms: int = 0,
) -> CloudProfile:
    """Create compact synthetic cloud profiles for compute control testing."""
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
            unpatched_critical_vms=unpatched_critical_vms,
            endpoint_protection_coverage_ratio=endpoint_protection_coverage_ratio,
            hardened_baseline_coverage_ratio=hardened_baseline_coverage_ratio,
            workload_backup_agent_coverage_ratio=workload_backup_agent_coverage_ratio,
            linux_password_auth_enabled_vms=linux_password_auth_enabled_vms,
        ),
        governance=GovernanceProfile(
            tagging_coverage_ratio=1.0,
            budget_alerts_enabled=True,
            policy_assignment_coverage_ratio=1.0,
            orphaned_resource_count=0,
        ),
        metadata={"profile_source": "test"},
    )


def test_evaluate_compute_controls_returns_no_findings_for_strong_posture() -> None:
    findings = evaluate_compute_controls([make_profile()])
    assert findings == []


def test_evaluate_compute_controls_flags_unpatched_critical_workloads() -> None:
    findings = evaluate_compute_controls([make_profile(unpatched_critical_vms=2)])
    patching = next(item for item in findings if item.control_id == "CMP-001")
    assert patching.severity == FindingSeverity.CRITICAL
    assert patching.is_compliant is False


def test_evaluate_compute_controls_generates_multiple_findings_for_broader_weakness() -> None:
    findings = evaluate_compute_controls(
        [
            make_profile(
                unpatched_critical_vms=1,
                endpoint_protection_coverage_ratio=0.6,
                hardened_baseline_coverage_ratio=0.65,
                workload_backup_agent_coverage_ratio=0.7,
                linux_password_auth_enabled_vms=2,
            )
        ]
    )

    control_ids = {item.control_id for item in findings}
    assert {"CMP-001", "CMP-002", "CMP-003", "CMP-004", "CMP-005"} <= control_ids
