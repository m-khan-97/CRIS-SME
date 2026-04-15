# Unit tests for the monitoring control evaluation layer in CRIS-SME.
from cris_sme.controls.monitoring_controls import evaluate_monitoring_controls
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
    organization_id: str = "sme-mon-001",
    organization_name: str = "Monitoring Test SME Ltd",
    sector: str = "Financial Services",
    activity_log_retention_days: int = 180,
    critical_alert_coverage_ratio: float = 0.95,
    defender_coverage_ratio: float = 0.95,
    centralized_logging_enabled: bool = True,
    incident_response_runbooks_enabled: bool = True,
) -> CloudProfile:
    """Create compact synthetic cloud profiles for monitoring control testing."""
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
            activity_log_retention_days=activity_log_retention_days,
            critical_alert_coverage_ratio=critical_alert_coverage_ratio,
            defender_coverage_ratio=defender_coverage_ratio,
            centralized_logging_enabled=centralized_logging_enabled,
            incident_response_runbooks_enabled=incident_response_runbooks_enabled,
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


def test_evaluate_monitoring_controls_returns_no_findings_for_strong_posture() -> None:
    findings = evaluate_monitoring_controls([make_profile()])
    assert findings == []


def test_evaluate_monitoring_controls_flags_short_log_retention() -> None:
    findings = evaluate_monitoring_controls([make_profile(activity_log_retention_days=30)])
    retention = next(item for item in findings if item.control_id == "MON-001")
    assert retention.severity == FindingSeverity.HIGH
    assert retention.is_compliant is False


def test_evaluate_monitoring_controls_generates_multiple_findings_for_broader_weakness() -> None:
    findings = evaluate_monitoring_controls(
        [
            make_profile(
                activity_log_retention_days=45,
                critical_alert_coverage_ratio=0.5,
                defender_coverage_ratio=0.6,
                centralized_logging_enabled=False,
                incident_response_runbooks_enabled=False,
            )
        ]
    )

    control_ids = {item.control_id for item in findings}
    assert {"MON-001", "MON-002", "MON-003", "MON-004"} <= control_ids
