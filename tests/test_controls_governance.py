# Unit tests for the governance control evaluation layer in CRIS-SME.
from cris_sme.controls.governance_controls import evaluate_governance_controls
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
    organization_id: str = "sme-gov-001",
    organization_name: str = "Governance Test SME Ltd",
    sector: str = "Financial Services",
    tagging_coverage_ratio: float = 1.0,
    budget_alerts_enabled: bool = True,
    budget_api_accessible: bool = True,
    budget_alert_count: int = 1,
    budget_evidence_state: str = "observed",
    policy_assignment_coverage_ratio: float = 1.0,
    orphaned_resource_count: int = 0,
) -> CloudProfile:
    """Create compact synthetic cloud profiles for governance control testing."""
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
            unpatched_critical_vms=0,
            endpoint_protection_coverage_ratio=1.0,
            hardened_baseline_coverage_ratio=1.0,
            workload_backup_agent_coverage_ratio=1.0,
        ),
        governance=GovernanceProfile(
            tagging_coverage_ratio=tagging_coverage_ratio,
            budget_alerts_enabled=budget_alerts_enabled,
            budget_api_accessible=budget_api_accessible,
            budget_alert_count=budget_alert_count,
            budget_evidence_state=budget_evidence_state,
            policy_assignment_coverage_ratio=policy_assignment_coverage_ratio,
            orphaned_resource_count=orphaned_resource_count,
        ),
        metadata={"profile_source": "test"},
    )


def test_evaluate_governance_controls_returns_no_findings_for_strong_posture() -> None:
    findings = evaluate_governance_controls([make_profile()])
    assert findings == []


def test_evaluate_governance_controls_flags_low_policy_coverage() -> None:
    findings = evaluate_governance_controls([make_profile(policy_assignment_coverage_ratio=0.5)])
    policy = next(item for item in findings if item.control_id == "GOV-003")
    assert policy.severity == FindingSeverity.HIGH
    assert policy.is_compliant is False


def test_evaluate_governance_controls_generates_multiple_findings_for_broader_weakness() -> None:
    findings = evaluate_governance_controls(
        [
            make_profile(
                tagging_coverage_ratio=0.6,
                budget_alerts_enabled=False,
                policy_assignment_coverage_ratio=0.5,
                orphaned_resource_count=6,
            )
        ]
    )

    control_ids = {item.control_id for item in findings}
    assert {"GOV-001", "GOV-002", "GOV-003", "GOV-004"} <= control_ids


def test_evaluate_governance_controls_distinguishes_budget_api_gap() -> None:
    findings = evaluate_governance_controls(
        [
            make_profile(
                budget_alerts_enabled=False,
                budget_api_accessible=False,
                budget_alert_count=0,
                budget_evidence_state="unavailable",
            )
        ]
    )

    budget_finding = next(item for item in findings if item.control_id == "GOV-002")
    assert budget_finding.is_compliant is False
    assert budget_finding.confidence == 0.62
    assert budget_finding.metadata["budget_api_accessible"] is False
    assert any("could not be verified" in item for item in budget_finding.evidence)
