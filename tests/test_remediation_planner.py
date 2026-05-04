# Unit tests for budget-aware remediation planning in CRIS-SME.
from cris_sme.controls.compute_controls import evaluate_compute_controls
from cris_sme.controls.data_controls import evaluate_data_controls
from cris_sme.controls.governance_controls import evaluate_governance_controls
from cris_sme.controls.iam_controls import evaluate_iam_controls
from cris_sme.controls.monitoring_controls import evaluate_monitoring_controls
from cris_sme.controls.network_controls import evaluate_network_controls
from cris_sme.engine.action_plan import build_30_day_action_plan
from cris_sme.engine.remediation import build_budget_aware_remediation_plan
from cris_sme.engine.remediation_simulator import (
    RemediationSimulationRequest,
    build_custom_remediation_simulation,
    build_custom_report_remediation_simulation,
    build_remediation_simulation,
)
from cris_sme.engine.scoring import score_findings
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
    """Create a compact profile for remediation-planner testing."""
    return CloudProfile(
        organization_id="sme-remed-001",
        organization_name="Budget Test SME Ltd",
        provider="azure",
        sector="Financial Services",
        tenant_scope="Tenant root / Entra ID",
        iam=IamProfile(
            privileged_accounts=3,
            privileged_accounts_without_mfa=1,
            overprivileged_accounts=1,
            stale_service_principals=0,
            rbac_review_age_days=120,
            conditional_access_enforced_for_admins=False,
        ),
        network=NetworkProfile(
            internet_exposed_rdp_assets=1,
            internet_exposed_ssh_assets=1,
            permissive_nsg_rules=2,
            public_storage_endpoints=1,
            private_endpoints_required=2,
            private_endpoints_configured=0,
        ),
        data=DataProfile(
            public_storage_assets=1,
            unencrypted_data_stores=1,
            backup_coverage_ratio=0.5,
            retention_policy_coverage_ratio=0.6,
            key_vault_mfa_enabled=False,
            key_vault_purge_protection_enabled=False,
        ),
        monitoring=MonitoringProfile(
            activity_log_retention_days=30,
            critical_alert_coverage_ratio=0.4,
            defender_coverage_ratio=0.5,
            centralized_logging_enabled=False,
            incident_response_runbooks_enabled=False,
        ),
        compute=ComputeProfile(
            unpatched_critical_vms=1,
            endpoint_protection_coverage_ratio=0.4,
            hardened_baseline_coverage_ratio=0.5,
            workload_backup_agent_coverage_ratio=0.4,
            linux_password_auth_enabled_vms=1,
        ),
        governance=GovernanceProfile(
            tagging_coverage_ratio=0.5,
            budget_alerts_enabled=False,
            policy_assignment_coverage_ratio=0.4,
            orphaned_resource_count=3,
        ),
        metadata={"profile_source": "test"},
    )


def test_budget_aware_remediation_plan_builds_expected_action_packs() -> None:
    profiles = [make_profile()]
    findings = [
        *evaluate_iam_controls(profiles),
        *evaluate_network_controls(profiles),
        *evaluate_data_controls(profiles),
        *evaluate_monitoring_controls(profiles),
        *evaluate_compute_controls(profiles),
        *evaluate_governance_controls(profiles),
    ]
    scoring_result = score_findings(findings)

    plan = build_budget_aware_remediation_plan(scoring_result.prioritized_findings)

    assert len(plan.budget_profiles) == 3
    free_profile = next(
        profile for profile in plan.budget_profiles if profile.profile_id == "free_this_week"
    )
    lean_profile = next(
        profile for profile in plan.budget_profiles if profile.profile_id == "under_200_month"
    )

    assert free_profile.max_monthly_cost_gbp == 0
    assert "free" in free_profile.allowed_cost_tiers
    assert free_profile.total_recommended >= 1
    assert lean_profile.total_recommended >= free_profile.total_recommended
    assert lean_profile.average_value_score >= 0.0
    assert all(
        recommendation.remediation_cost_tier in {"free", "low"}
        for recommendation in lean_profile.recommended_actions
    )


def test_30_day_action_plan_phases_free_and_low_effort_work_first() -> None:
    profiles = [make_profile()]
    findings = [
        *evaluate_iam_controls(profiles),
        *evaluate_network_controls(profiles),
        *evaluate_data_controls(profiles),
        *evaluate_monitoring_controls(profiles),
        *evaluate_compute_controls(profiles),
        *evaluate_governance_controls(profiles),
    ]
    scoring_result = score_findings(findings)

    plan = build_30_day_action_plan(scoring_result.prioritized_findings)
    phases = {phase.phase_id: phase for phase in plan.phases}

    assert phases["days_1_7"].total_actions >= 1
    assert all(action.remediation_cost_tier == "free" for action in phases["days_1_7"].actions)
    assert phases["days_8_30"].total_actions >= 1


def test_remediation_simulation_builds_before_after_scenarios() -> None:
    profiles = [make_profile()]
    findings = [
        *evaluate_iam_controls(profiles),
        *evaluate_network_controls(profiles),
        *evaluate_data_controls(profiles),
        *evaluate_monitoring_controls(profiles),
        *evaluate_compute_controls(profiles),
        *evaluate_governance_controls(profiles),
    ]
    scoring_result = score_findings(findings)

    simulation = build_remediation_simulation(scoring_result)
    scenarios = {scenario.scenario_id: scenario for scenario in simulation.scenarios}

    assert simulation.simulation_model == "cris_sme_deterministic_remediation_simulator_v1"
    assert set(scenarios) == {
        "fix_free_this_week",
        "fix_under_200_month",
        "fix_under_750_month",
        "fix_top_5_risks",
    }
    assert scenarios["fix_free_this_week"].selected_action_count >= 1
    assert scenarios["fix_free_this_week"].simulated_overall_risk_score <= (
        scoring_result.overall_risk_score
    )
    assert scenarios["fix_under_750_month"].expected_risk_reduction >= (
        scenarios["fix_free_this_week"].expected_risk_reduction
    )
    assert scenarios["fix_top_5_risks"].selected_action_count == 5
    assert scenarios["fix_top_5_risks"].selected_actions[0].finding_id.startswith("fdg_")


def test_custom_remediation_simulation_selects_control_ids() -> None:
    profiles = [make_profile()]
    findings = [
        *evaluate_iam_controls(profiles),
        *evaluate_network_controls(profiles),
        *evaluate_data_controls(profiles),
        *evaluate_monitoring_controls(profiles),
        *evaluate_compute_controls(profiles),
        *evaluate_governance_controls(profiles),
    ]
    scoring_result = score_findings(findings)
    request = RemediationSimulationRequest(
        scenario_id="fix_net_001",
        label="Fix internet admin exposure",
        control_ids=["NET-001"],
    )

    scenario = build_custom_remediation_simulation(scoring_result, request)

    assert scenario.scenario_id == "fix_net_001"
    assert scenario.selected_action_count >= 1
    assert scenario.expected_risk_reduction > 0
    assert all(action.control_id == "NET-001" for action in scenario.selected_actions)


def test_custom_report_remediation_simulation_selects_categories() -> None:
    report = {
        "overall_risk_score": 50.0,
        "category_scores": {
            "IAM": 60.0,
            "Network": 40.0,
        },
        "prioritized_risks": [
            {
                "finding_id": "fdg_iam",
                "control_id": "IAM-001",
                "category": "IAM",
                "title": "IAM issue",
                "organization": "SME",
                "score": 60.0,
                "remediation_cost_tier": "free",
                "remediation_value_score": 60.0,
            },
            {
                "finding_id": "fdg_net",
                "control_id": "NET-001",
                "category": "Network",
                "title": "Network issue",
                "organization": "SME",
                "score": 40.0,
                "remediation_cost_tier": "medium",
                "remediation_value_score": 21.62,
            },
        ],
    }
    request = RemediationSimulationRequest(
        scenario_id="fix_iam",
        label="Fix IAM",
        categories=["IAM"],
    )

    scenario = build_custom_report_remediation_simulation(report, request)

    assert scenario["selected_action_count"] == 1
    assert scenario["simulated_non_compliant_findings"] == 1
    assert scenario["selected_actions"][0]["finding_id"] == "fdg_iam"
    assert scenario["expected_risk_reduction"] > 0
