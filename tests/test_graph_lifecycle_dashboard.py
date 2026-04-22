# Unit tests for graph-context reasoning, finding lifecycle, and dashboard exports.
from pathlib import Path

from cris_sme.controls.compute_controls import evaluate_compute_controls
from cris_sme.controls.data_controls import evaluate_data_controls
from cris_sme.controls.governance_controls import evaluate_governance_controls
from cris_sme.controls.iam_controls import evaluate_iam_controls
from cris_sme.controls.monitoring_controls import evaluate_monitoring_controls
from cris_sme.controls.network_controls import evaluate_network_controls
from cris_sme.engine.graph_context import build_graph_context_summary
from cris_sme.engine.lifecycle import enrich_report_finding_lifecycle
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
from cris_sme.reporting.dashboard import (
    build_dashboard_html,
    build_dashboard_payload,
    write_dashboard_html,
    write_dashboard_payload,
)


def _profile() -> CloudProfile:
    return CloudProfile(
        organization_id="sme-dash-001",
        organization_name="Dashboard Test SME",
        provider="azure",
        sector="Financial Services",
        tenant_scope="Tenant root / Entra ID",
        iam=IamProfile(
            privileged_accounts=3,
            privileged_accounts_without_mfa=2,
            overprivileged_accounts=1,
            stale_service_principals=1,
            rbac_review_age_days=180,
            conditional_access_enforced_for_admins=False,
        ),
        network=NetworkProfile(
            internet_exposed_rdp_assets=1,
            internet_exposed_ssh_assets=1,
            permissive_nsg_rules=2,
            public_storage_endpoints=1,
            private_endpoints_required=2,
            private_endpoints_configured=1,
        ),
        data=DataProfile(
            public_storage_assets=1,
            unencrypted_data_stores=1,
            backup_coverage_ratio=0.6,
            retention_policy_coverage_ratio=0.65,
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
            endpoint_protection_coverage_ratio=0.5,
            hardened_baseline_coverage_ratio=0.5,
            workload_backup_agent_coverage_ratio=0.5,
            linux_password_auth_enabled_vms=1,
        ),
        governance=GovernanceProfile(
            tagging_coverage_ratio=0.6,
            budget_alerts_enabled=False,
            policy_assignment_coverage_ratio=0.6,
            orphaned_resource_count=4,
        ),
        metadata={"profile_source": "test"},
    )


def _scoring():
    profiles = [_profile()]
    findings = [
        *evaluate_iam_controls(profiles),
        *evaluate_network_controls(profiles),
        *evaluate_data_controls(profiles),
        *evaluate_monitoring_controls(profiles),
        *evaluate_compute_controls(profiles),
        *evaluate_governance_controls(profiles),
    ]
    return profiles, findings, score_findings(findings)


def test_build_graph_context_summary_detects_toxic_combinations() -> None:
    profiles, _findings, scoring_result = _scoring()

    context = build_graph_context_summary(profiles, scoring_result.prioritized_findings)

    assert context["asset_count"] >= 1
    assert context["relationship_count"] >= 1
    assert context["blast_radius"]["score"] > 0
    assert context["toxic_combinations"]


def test_enrich_report_finding_lifecycle_sets_first_seen_from_history() -> None:
    _profiles, _findings, scoring_result = _scoring()
    report = {
        "generated_at": "2026-04-22T12:00:00Z",
        "prioritized_risks": [
            {
                "control_id": item.finding.control_id,
                "provider": item.finding.metadata.get("provider", "azure"),
                "organization": item.finding.metadata.get("organization_name"),
                "resource_scope": item.finding.resource_scope,
                "score": item.score,
            }
            for item in scoring_result.prioritized_findings[:2]
        ],
    }
    previous = [
        {
            "generated_at": "2026-04-21T12:00:00Z",
            "prioritized_risks": [
                {
                    "control_id": scoring_result.prioritized_findings[0].finding.control_id,
                    "provider": scoring_result.prioritized_findings[0].finding.metadata.get("provider", "azure"),
                    "organization": scoring_result.prioritized_findings[0].finding.metadata.get("organization_name"),
                    "resource_scope": scoring_result.prioritized_findings[0].finding.resource_scope,
                    "score": scoring_result.prioritized_findings[0].score,
                }
            ],
        }
    ]

    summary = enrich_report_finding_lifecycle(report, previous, exception_registry=[])

    assert summary["new_findings"] >= 1
    assert report["prioritized_risks"][0]["lifecycle"]["first_seen"] == "2026-04-21T12:00:00Z"
    assert report["prioritized_risks"][0]["lifecycle"]["is_new"] is False


def test_dashboard_payload_and_html_are_written(tmp_path: Path) -> None:
    _profiles, _findings, scoring_result = _scoring()
    report = {
        "generated_at": "2026-04-22T12:00:00Z",
        "collector_mode": "mock",
        "overall_risk_score": scoring_result.overall_risk_score,
        "evaluation_context": {
            "evaluated_profiles": 1,
        },
        "prioritized_risks": [
            {
                "control_id": item.finding.control_id,
                "title": item.finding.title,
                "category": item.finding.category.value,
                "priority": item.priority,
                "score": item.score,
                "organization": item.finding.metadata.get("organization_name"),
                "evidence": item.finding.evidence,
                "confidence_calibration": {
                    "observed_confidence": item.breakdown.observed_confidence,
                    "calibrated_confidence": item.breakdown.calibrated_confidence,
                },
                "lifecycle": {"status": "open"},
                "evidence_quality": {"observation_class": "observed"},
            }
            for item in scoring_result.prioritized_findings[:5]
        ],
        "category_scores": scoring_result.category_scores,
        "history_comparison": {"overall_trend": []},
        "compliance": {"frameworks_covered": ["ISO 27001"]},
        "cyber_essentials_readiness": {"overall_readiness_score": 60.0},
        "collector_coverage": [],
        "graph_context": {
            "blast_radius": {"score": 55.0, "band": "medium"},
            "toxic_combinations": [],
            "top_exposure_chains": [],
            "assets": [],
            "relationships": [],
        },
        "budget_aware_remediation": {"budget_profiles": []},
        "action_plan_30_day": {"phases": []},
    }

    payload = build_dashboard_payload(report, [])
    payload_path = write_dashboard_payload(payload, tmp_path)
    html = build_dashboard_html(payload)
    html_path = write_dashboard_html(html, tmp_path / "dashboard.html")

    assert payload_path.exists()
    assert html_path.exists()
    assert "Risk Decision Console" in html
