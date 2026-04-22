# Unit tests for CRIS-SME JSON and summary reporting outputs.
import json
from datetime import UTC, datetime

from cris_sme.controls.compute_controls import evaluate_compute_controls
from cris_sme.controls.data_controls import evaluate_data_controls
from cris_sme.controls.governance_controls import evaluate_governance_controls
from cris_sme.controls.iam_controls import evaluate_iam_controls
from cris_sme.controls.monitoring_controls import evaluate_monitoring_controls
from cris_sme.controls.network_controls import evaluate_network_controls
from cris_sme.engine.compliance import assess_compliance_mappings, load_compliance_mappings
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
from cris_sme.reporting import (
    archive_report_snapshot,
    build_html_report,
    build_cyber_insurance_evidence_pack,
    build_history_comparison,
    build_json_report,
    build_summary_report,
    load_report_history,
    write_appendix_tables,
    write_cyber_insurance_evidence_pack,
    write_history_figures,
    write_html_report,
    write_json_report,
    write_report_figures,
    write_summary_report,
)


def make_profile(
    *,
    organization_id: str = "sme-report-001",
    organization_name: str = "Reporting SME Ltd",
    sector: str = "Financial Services",
    privileged_accounts_without_mfa: int = 1,
    overprivileged_accounts: int = 1,
    stale_service_principals: int = 0,
    rbac_review_age_days: int = 120,
    conditional_access_enforced_for_admins: bool = True,
) -> CloudProfile:
    """Create compact synthetic profiles for reporting tests."""
    return CloudProfile(
        organization_id=organization_id,
        organization_name=organization_name,
        provider="azure",
        sector=sector,
        tenant_scope="Tenant root / Entra ID",
        iam=IamProfile(
            privileged_accounts=3,
            privileged_accounts_without_mfa=privileged_accounts_without_mfa,
            overprivileged_accounts=overprivileged_accounts,
            stale_service_principals=stale_service_principals,
            rbac_review_age_days=rbac_review_age_days,
            conditional_access_enforced_for_admins=conditional_access_enforced_for_admins,
            privileged_user_assignments=2,
            privileged_service_principal_assignments=1,
            disabled_service_principals=1,
            signed_in_user_directory_roles=2,
            signed_in_user_is_directory_admin=True,
            visible_directory_role_catalog_entries=4,
            directory_role_catalog_visible=True,
            identity_observability="partial",
        ),
        network=NetworkProfile(
            internet_exposed_rdp_assets=0,
            internet_exposed_ssh_assets=1,
            permissive_nsg_rules=1,
            public_storage_endpoints=0,
            private_endpoints_required=2,
            private_endpoints_configured=1,
        ),
        data=DataProfile(
            public_storage_assets=1,
            unencrypted_data_stores=0,
            backup_coverage_ratio=0.8,
            retention_policy_coverage_ratio=0.85,
            key_vault_mfa_enabled=True,
            key_vault_purge_protection_enabled=False,
        ),
        monitoring=MonitoringProfile(
            activity_log_retention_days=45,
            critical_alert_coverage_ratio=0.6,
            defender_coverage_ratio=0.7,
            centralized_logging_enabled=True,
            incident_response_runbooks_enabled=False,
        ),
        compute=ComputeProfile(
            unpatched_critical_vms=1,
            endpoint_protection_coverage_ratio=0.7,
            hardened_baseline_coverage_ratio=0.75,
            workload_backup_agent_coverage_ratio=0.8,
            linux_password_auth_enabled_vms=1,
        ),
        governance=GovernanceProfile(
            tagging_coverage_ratio=0.7,
            budget_alerts_enabled=False,
            policy_assignment_coverage_ratio=0.75,
            orphaned_resource_count=2,
        ),
        metadata={
            "profile_source": "azure_live",
            "dataset_source_type": "live_real",
            "authorization_basis": "authorized_tenant_access",
            "dataset_use": "live_case_study",
            "iam_collection_mode": "azure_role_assignments_and_graph",
            "identity_observability": "partial",
            "privileged_assignment_count": 3,
            "privileged_principal_count": 2,
            "privileged_user_assignment_count": 2,
            "privileged_service_principal_assignment_count": 1,
            "disabled_service_principal_count": 1,
            "signed_in_user_directory_role_count": 2,
            "signed_in_user_is_directory_admin": True,
            "signed_in_user_directory_roles_visible": True,
            "visible_directory_role_catalog_count": 4,
            "directory_role_catalog_visible": True,
            "network_collection_mode": "azure_network_management",
            "data_collection_mode": "azure_sql_inventory",
            "monitoring_collection_mode": "azure_monitor_cli_inventory",
            "compute_collection_mode": "azure_compute_cli_inventory",
            "governance_collection_mode": "azure_resource_inventory",
            "virtual_machine_count": 3,
            "sql_database_count": 2,
            "policy_assignment_count": 2,
        },
    )


def test_build_json_report_includes_context_and_prioritized_risks() -> None:
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
    compliance_result = assess_compliance_mappings(findings, load_compliance_mappings())

    report = build_json_report(
        profiles=profiles,
        findings=findings,
        scoring_result=scoring_result,
        compliance_result=compliance_result,
    )

    assert report["overall_risk_score"] == scoring_result.overall_risk_score
    assert report["report_schema_version"] == "2.0.0"
    assert report["collector_coverage"]
    assert report["graph_context"]["graph_model"] == "cris_sme_lightweight_asset_context_v1"
    assert report["evaluation_dataset"]["source_types"] == ["live_real"]
    assert report["evaluation_dataset"]["authorization_bases"] == [
        "authorized_tenant_access"
    ]
    assert report["evaluation_dataset"]["dataset_uses"] == ["live_case_study"]
    assert report["confidence_calibration"]["controls_with_calibration"] >= 1
    assert report["native_validation"]["controls_mapped"] >= 1
    assert report["benchmark_observation"]["provider"] == "azure"
    assert report["benchmark_comparison"]["dataset_size"] >= 1
    assert report["cyber_essentials_readiness"]["pillar_count"] == 5
    assert report["executive_pack"]["pack_name"] == "CRIS-SME Executive Pack"
    assert report["evaluation_context"]["evaluated_profiles"] == 1
    assert report["evaluation_context"]["generated_findings"] == len(findings)
    assert len(report["prioritized_risks"]) == scoring_result.non_compliant_findings
    organization = report["organizations"][0]
    assert organization["collection_details"]["iam_collection_mode"] == "azure_role_assignments_and_graph"
    assert organization["collection_details"]["dataset_source_type"] == "live_real"
    assert organization["collection_details"]["authorization_basis"] == "authorized_tenant_access"
    assert organization["collection_details"]["compute_collection_mode"] == "azure_compute_cli_inventory"
    assert organization["collection_details"]["identity_observability"] == "partial"
    assert organization["collection_details"]["evidence_counts"]["virtual_machine_count"] == 3
    assert organization["collection_details"]["evidence_counts"]["privileged_assignment_count"] == 3
    assert organization["collection_details"]["evidence_counts"]["signed_in_user_directory_role_count"] == 2
    first_risk = report["prioritized_risks"][0]
    assert first_risk["finding_id"].startswith("fdg_")
    assert first_risk["finding_trace"]["finding_id"] == first_risk["finding_id"]
    assert first_risk["lifecycle"]["status"] == "open"
    assert first_risk["remediation_summary"]
    assert first_risk["remediation_cost_tier"] in {"free", "low", "medium", "high"}
    assert first_risk["remediation_value_score"] is not None
    assert first_risk["confidence_calibration"]["calibrated_confidence"] is not None
    assert isinstance(first_risk["budget_fit_profiles"], list)
    assert report["budget_aware_remediation"]["budget_profiles"]
    assert report["action_plan_30_day"]["phases"]
    assert report["cyber_insurance_evidence"]["readiness_summary"]["question_count"] >= 1
    assert report["compliance"]["uk_sme_profile"]["mapped_control_count"] >= 1


def test_build_summary_report_mentions_profiles_score_and_priority_distribution() -> None:
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

    summary = build_summary_report(
        profiles=profiles,
        scoring_result=scoring_result,
    )

    assert "Reporting SME Ltd" in summary
    assert "overall risk score" in summary
    assert "Collection context" in summary
    assert "Confidence calibration" in summary
    assert "Native validation" in summary
    assert "Budget-aware remediation" in summary
    assert "30-day action plan" in summary
    assert "Cyber insurance evidence" in summary
    assert "Benchmarking" in summary
    assert "UK readiness" in summary
    assert "Priority distribution" in summary


def test_build_html_report_includes_risk_and_provenance_content() -> None:
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
    compliance_result = assess_compliance_mappings(findings, load_compliance_mappings())
    report = build_json_report(
        profiles=profiles,
        findings=findings,
        scoring_result=scoring_result,
        compliance_result=compliance_result,
    )
    report["executive_summary"] = build_summary_report(
        profiles=profiles,
        scoring_result=scoring_result,
    )

    html = build_html_report(report)

    assert "CRIS-SME Risk Intelligence Report" in html
    assert "Reporting SME Ltd" in html
    assert "Collection Provenance" in html
    assert "Confidence Calibration" in html
    assert "Native Recommendation Validation" in html
    assert "Run Comparison" in html
    assert "UK Regulatory Mapping" in html
    assert "Budget-Aware Remediation" in html
    assert "30-Day SME Action Plan" in html
    assert "Cyber Insurance Evidence Pack" in html
    assert "Benchmark Scaffold" in html
    assert "Cyber Essentials Readiness" in html
    assert "Executive Pack" in html
    assert "Plain-Language Narrator" in html
    assert "Cyber Essentials" in html
    assert "Access security" in html
    assert "azure_compute_cli_inventory" in html


def test_cyber_insurance_pack_builds_and_writes_artifacts(tmp_path) -> None:
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
    report = build_json_report(
        profiles=profiles,
        findings=findings,
        scoring_result=scoring_result,
    )

    insurance_pack = build_cyber_insurance_evidence_pack(report)
    artifact_paths = write_cyber_insurance_evidence_pack(insurance_pack, tmp_path)

    assert insurance_pack["pack_name"] == "CRIS-SME Cyber Insurance Evidence Pack"
    assert insurance_pack["readiness_summary"]["question_count"] >= 1
    assert artifact_paths["cyber_insurance_markdown"].exists()
    assert artifact_paths["cyber_insurance_json"].exists()
    assert "CRIS-SME Cyber Insurance Evidence Pack" in artifact_paths["cyber_insurance_markdown"].read_text(encoding="utf-8")


def test_report_writers_persist_json_and_summary_outputs(tmp_path) -> None:
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
    report = build_json_report(
        profiles=profiles,
        findings=findings,
        scoring_result=scoring_result,
    )
    summary = build_summary_report(
        profiles=profiles,
        scoring_result=scoring_result,
    )
    report["executive_summary"] = summary
    html = build_html_report(report)

    json_path = write_json_report(report, tmp_path / "report.json")
    html_path = write_html_report(html, tmp_path / "report.html")
    summary_path = write_summary_report(summary, tmp_path / "summary.txt")

    assert json.loads(json_path.read_text(encoding="utf-8"))["overall_risk_score"] == scoring_result.overall_risk_score
    assert "CRIS-SME Risk Intelligence Report" in html_path.read_text(encoding="utf-8")
    assert "Reporting SME Ltd" in summary_path.read_text(encoding="utf-8")


def test_write_report_figures_persists_svg_outputs(tmp_path) -> None:
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
    report = build_json_report(
        profiles=profiles,
        findings=findings,
        scoring_result=scoring_result,
    )

    figure_paths = write_report_figures(report, tmp_path / "figures")

    category_svg = figure_paths["category_scores"].read_text(encoding="utf-8")
    priority_svg = figure_paths["priority_distribution"].read_text(encoding="utf-8")
    trend_svg = figure_paths["risk_trend"].read_text(encoding="utf-8")
    category_png = figure_paths["category_scores_png"]
    comparison_png = figure_paths["run_comparison_png"]

    assert "CRIS-SME Category Risk Scores" in category_svg
    assert "Compute/Workloads" in category_svg
    assert "CRIS-SME Priority Distribution" in priority_svg
    assert "Planned" in priority_svg
    assert "CRIS-SME Overall Risk Trend" in trend_svg
    assert category_png.exists()
    assert comparison_png.exists()


def test_report_history_archive_and_history_figures_work(tmp_path) -> None:
    report_one = {
        "generated_at": "2026-04-14T10:00:00Z",
        "collector_mode": "mock",
        "overall_risk_score": 41.2,
    }
    report_two = {
        "generated_at": "2026-04-15T10:00:00Z",
        "collector_mode": "azure",
        "overall_risk_score": 33.12,
    }

    archive_report_snapshot(
        report_one,
        tmp_path / "reports",
        timestamp=datetime(2026, 4, 14, 10, 0, tzinfo=UTC),
    )
    archive_report_snapshot(
        report_two,
        tmp_path / "reports",
        timestamp=datetime(2026, 4, 15, 10, 0, tzinfo=UTC),
    )

    history = load_report_history(tmp_path / "reports" / "history")
    comparison = build_history_comparison(history)
    figure_paths = write_history_figures(history, tmp_path / "figures")
    appendix_paths = write_appendix_tables(
        {
            "generated_at": "2026-04-15T10:00:00Z",
            "overall_risk_score": 33.12,
            "summary": "Overall risk score: 33.12/100 across 16 non-compliant findings.",
            "category_scores": {"IAM": 14.64, "Network": 47.41},
            "prioritized_risks": [
                {
                    "control_id": "NET-001",
                    "title": "Administrative services are exposed to the public internet",
                    "category": "Network",
                    "priority": "High",
                    "severity": "High",
                    "score": 50.33,
                    "organization": "Azure SME Tenant",
                }
            ],
            "history_comparison": comparison,
        },
        tmp_path / "reports",
    )

    trend_svg = figure_paths["risk_trend"].read_text(encoding="utf-8")
    comparison_svg = figure_paths["run_comparison"].read_text(encoding="utf-8")
    trend_png = figure_paths["risk_trend_png"]
    appendix_md = appendix_paths["results_appendix_markdown"].read_text(encoding="utf-8")
    appendix_csv = appendix_paths["prioritized_risks_csv"].read_text(encoding="utf-8")

    assert len(history) == 2
    assert comparison["overall_risk_delta"] == -8.08
    assert comparison["previous_distinct_mode"] == "mock"
    assert comparison["overall_risk_delta_vs_distinct_mode"] == -8.08
    assert "CRIS-SME Overall Risk Trend" in trend_svg
    assert "CRIS-SME Run Comparison" in comparison_svg
    assert trend_png.exists()
    assert "CRIS-SME Results Appendix" in appendix_md
    assert (
        "control_id,title,category,priority,severity,score,organization,remediation_cost_tier,remediation_value_score,budget_fit_profiles,remediation_summary"
        in appendix_csv
    )
