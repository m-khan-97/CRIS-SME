# Unit tests for the compliance mapping layer in CRIS-SME.
from cris_sme.controls.compute_controls import evaluate_compute_controls
from cris_sme.controls.data_controls import evaluate_data_controls
from cris_sme.controls.governance_controls import evaluate_governance_controls
from cris_sme.controls.iam_controls import evaluate_iam_controls
from cris_sme.controls.monitoring_controls import evaluate_monitoring_controls
from cris_sme.controls.network_controls import evaluate_network_controls
from cris_sme.engine.compliance import assess_compliance_mappings, load_compliance_mappings
from cris_sme.models.cloud_profile import (
    CloudProfile,
    ComputeProfile,
    DataProfile,
    GovernanceProfile,
    IamProfile,
    MonitoringProfile,
    NetworkProfile,
)


def make_profile() -> CloudProfile:
    """Create a compact synthetic profile for compliance mapping tests."""
    return CloudProfile(
        organization_id="sme-comp-001",
        organization_name="Compliance Test SME Ltd",
        provider="azure",
        sector="Financial Services",
        tenant_scope="Tenant root / Entra ID",
        iam=IamProfile(
            privileged_accounts=3,
            privileged_accounts_without_mfa=1,
            overprivileged_accounts=1,
            stale_service_principals=0,
            rbac_review_age_days=30,
            conditional_access_enforced_for_admins=True,
        ),
        network=NetworkProfile(
            internet_exposed_rdp_assets=0,
            internet_exposed_ssh_assets=1,
            permissive_nsg_rules=1,
            public_storage_endpoints=0,
            private_endpoints_required=1,
            private_endpoints_configured=0,
        ),
        data=DataProfile(
            public_storage_assets=1,
            unencrypted_data_stores=1,
            backup_coverage_ratio=0.7,
            retention_policy_coverage_ratio=0.8,
            key_vault_mfa_enabled=True,
            key_vault_purge_protection_enabled=False,
        ),
        monitoring=MonitoringProfile(
            activity_log_retention_days=30,
            critical_alert_coverage_ratio=0.5,
            defender_coverage_ratio=0.6,
            centralized_logging_enabled=False,
            incident_response_runbooks_enabled=False,
        ),
        compute=ComputeProfile(
            unpatched_critical_vms=1,
            endpoint_protection_coverage_ratio=0.6,
            hardened_baseline_coverage_ratio=0.65,
            workload_backup_agent_coverage_ratio=0.75,
        ),
        governance=GovernanceProfile(
            tagging_coverage_ratio=0.6,
            budget_alerts_enabled=False,
            policy_assignment_coverage_ratio=0.5,
            orphaned_resource_count=4,
        ),
        metadata={"profile_source": "test"},
    )


def test_load_compliance_mappings_returns_expected_controls() -> None:
    mappings = load_compliance_mappings()

    assert "IAM-001" in mappings
    assert "NET-001" in mappings


def test_assess_compliance_mappings_summarizes_frameworks_and_findings() -> None:
    profiles = [make_profile()]
    findings = [
        *evaluate_iam_controls(profiles),
        *evaluate_network_controls(profiles),
        *evaluate_data_controls(profiles),
        *evaluate_monitoring_controls(profiles),
        *evaluate_compute_controls(profiles),
        *evaluate_governance_controls(profiles),
    ]
    mappings = load_compliance_mappings()

    result = assess_compliance_mappings(findings, mappings)

    assert "ISO 27001" in result.frameworks_covered
    assert "NIST CSF 2.0" in result.frameworks_covered
    assert result.findings_by_framework["ISO 27001"] >= 1
    assert any(item["control_id"] == "IAM-001" for item in result.mapped_findings)
