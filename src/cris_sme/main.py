# Command-line entrypoint for running the CRIS-SME MVP pipeline on collected cloud posture.
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from cris_sme.collectors.azure_collector import AzureCollector
from cris_sme.collectors.mock_collector import MockCollector
from cris_sme.config import (
    get_azure_collector_settings,
    get_collector_mode,
    get_narrator_settings,
)
from cris_sme.controls import (
    evaluate_compute_controls,
    evaluate_data_controls,
    evaluate_governance_controls,
    evaluate_iam_controls,
    evaluate_monitoring_controls,
    evaluate_network_controls,
)
from cris_sme.engine import (
    assess_compliance_mappings,
    build_30_day_action_plan,
    build_assessment_assurance,
    build_assurance_case,
    build_claim_bound_narrative,
    build_claim_verification_pack,
    build_ce_evaluation_metrics,
    build_ce_review_console,
    build_ce_self_assessment_pack,
    build_collector_coverage,
    build_control_drift_attribution,
    build_decision_ledger,
    build_decision_provenance_graph,
    build_decision_review_queue,
    build_evidence_snapshot,
    build_report_replay_summary,
    build_report_trust_badge,
    build_risk_bill_of_materials,
    build_remediation_simulation,
    build_run_metadata,
    build_selective_disclosure_package,
    enrich_report_finding_lifecycle,
    load_compliance_mappings,
    load_exception_registry,
    write_risk_bill_of_materials,
    write_claim_verification_pack,
    write_assurance_case,
    write_ce_evaluation_metrics,
    write_ce_review_console,
    write_ce_self_assessment_pack,
    write_claim_bound_narrative,
    write_decision_provenance_graph,
    write_selective_disclosure_package,
)
from cris_sme.engine.benchmark import (
    build_benchmark_comparison,
    build_benchmark_observation,
    load_benchmark_dataset,
)
from cris_sme.engine.scoring import score_findings
from cris_sme.engine.uk_readiness import build_cyber_essentials_readiness
from cris_sme.policies import load_policy_pack_metadata
from cris_sme.reporting import (
    archive_report_snapshot,
    build_assurance_portal_html,
    build_cyber_insurance_evidence_pack,
    build_ce_evaluation_metrics_html,
    build_ce_review_console_html,
    build_ce_self_assessment_html,
    build_dashboard_html,
    build_dashboard_payload,
    build_evaluation_mode_summary,
    build_executive_pack,
    build_evidence_room_html,
    build_history_comparison,
    build_risk_drift_analysis,
    build_html_report,
    build_json_report,
    build_summary_report,
    load_report_history,
    maybe_generate_plain_language_narrative,
    write_action_plan_outputs,
    write_assurance_portal_html,
    write_appendix_tables,
    write_benchmark_outputs,
    write_cyber_insurance_evidence_pack,
    write_ce_evaluation_metrics_html,
    write_ce_paper_exports,
    write_ce_review_console_html,
    write_ce_self_assessment_html,
    write_dashboard_html,
    write_dashboard_payload,
    write_executive_pack,
    write_evidence_room_html,
    write_history_figures,
    write_html_report,
    write_json_report,
    write_plain_language_reports,
    write_report_figures,
    write_summary_report,
)


DEFAULT_OUTPUT_DIR = Path("outputs/reports")
DEFAULT_FIGURE_DIR = Path("outputs/figures")


def main() -> None:
    """Run the MVP flow from posture collection to scored risk output."""
    collector_mode = get_collector_mode()
    profiles = _collect_profiles()
    findings = [
        *evaluate_iam_controls(profiles),
        *evaluate_network_controls(profiles),
        *evaluate_data_controls(profiles),
        *evaluate_monitoring_controls(profiles),
        *evaluate_compute_controls(profiles),
        *evaluate_governance_controls(profiles),
    ]
    result = score_findings(findings)
    mapping_catalog = load_compliance_mappings()
    compliance_result = assess_compliance_mappings(findings, mapping_catalog)

    output = build_json_report(
        profiles=profiles,
        findings=findings,
        scoring_result=result,
        compliance_result=compliance_result,
    )
    generated_at = datetime.now(UTC)
    output["generated_at"] = generated_at.isoformat().replace("+00:00", "Z")
    output["collector_mode"] = collector_mode

    summary = build_summary_report(
        profiles=profiles,
        scoring_result=result,
    )
    output["executive_summary"] = summary

    output_dir = Path(os.getenv("CRIS_SME_OUTPUT_DIR", DEFAULT_OUTPUT_DIR))
    figure_dir = Path(os.getenv("CRIS_SME_FIGURE_DIR", DEFAULT_FIGURE_DIR))
    history_reports_before = load_report_history(output_dir / "history")
    policy_pack_metadata = load_policy_pack_metadata()
    evidence_snapshot = build_evidence_snapshot(
        profiles=profiles,
        findings=findings,
        collector_mode=collector_mode,
        generated_at=output["generated_at"],
        policy_pack_version=str(policy_pack_metadata.get("policy_pack_version", "unknown")),
    )
    output["evidence_snapshot"] = evidence_snapshot.model_dump(mode="json")
    output["assessment_replay"] = build_report_replay_summary(
        current_snapshot=evidence_snapshot,
        previous_report=history_reports_before[-1] if history_reports_before else None,
    )

    benchmark_dataset = load_benchmark_dataset()
    output["benchmark_observation"] = build_benchmark_observation(output).model_dump()
    output["benchmark_comparison"] = build_benchmark_comparison(
        output,
        benchmark_dataset,
    )

    comparison_reports = [*history_reports_before, output]
    output["history_comparison"] = build_history_comparison(comparison_reports)

    output["finding_lifecycle_summary"] = enrich_report_finding_lifecycle(
        output,
        history_reports_before,
        exception_registry=load_exception_registry(),
    )

    narrator_output = maybe_generate_plain_language_narrative(
        output,
        get_narrator_settings(),
    )
    if narrator_output is not None:
        output["plain_language_narrative"] = narrator_output.model_dump()

    output["run_metadata"] = build_run_metadata(
        generated_at=output["generated_at"],
        collector_mode=collector_mode,
        schema_version=str(output.get("report_schema_version", "2.0.0")),
        narrator_enabled=narrator_output is not None,
        providers_in_scope=[profile.provider for profile in profiles],
        policy_pack=load_policy_pack_metadata(),
        collector_coverage=build_collector_coverage(profiles),
    ).model_dump()
    output["decision_ledger"] = build_decision_ledger(
        output,
        history_reports_before,
    ).model_dump(mode="json")

    output["cyber_essentials_readiness"] = build_cyber_essentials_readiness(findings)
    output["cyber_essentials_self_assessment"] = build_ce_self_assessment_pack(output)
    output["cyber_essentials_review_console"] = build_ce_review_console(
        output["cyber_essentials_self_assessment"],
        generated_at=output["generated_at"],
    )
    output["cyber_essentials_evaluation_metrics"] = build_ce_evaluation_metrics(
        output["cyber_essentials_self_assessment"],
        output["cyber_essentials_review_console"],
    )
    output["cyber_insurance_evidence"] = build_cyber_insurance_evidence_pack(output)
    output["action_plan_30_day"] = build_30_day_action_plan(
        result.prioritized_findings
    ).model_dump()
    output["remediation_simulation"] = build_remediation_simulation(
        result,
    ).model_dump()
    output["executive_pack"] = build_executive_pack(output)
    output["decision_review_queue"] = build_decision_review_queue(output).model_dump(
        mode="json"
    )

    history_snapshot_path = archive_report_snapshot(
        output,
        output_dir,
        timestamp=generated_at,
    )
    history_reports = load_report_history(output_dir / "history")
    output["history_comparison"] = build_history_comparison(history_reports)
    output["control_drift_attribution"] = build_control_drift_attribution(
        output,
        history_reports_before[-1] if history_reports_before else None,
    ).model_dump(mode="json")
    output["evaluation_mode_summary"] = build_evaluation_mode_summary(history_reports)
    output["risk_drift_analysis"] = build_risk_drift_analysis(history_reports)

    dashboard_payload = build_dashboard_payload(output, history_reports)
    dashboard_payload_path = write_dashboard_payload(dashboard_payload, output_dir)
    dashboard_html_path = write_dashboard_html(
        build_dashboard_html(dashboard_payload),
        output_dir / "cris_sme_dashboard.html",
    )

    json_report_path = output_dir / "cris_sme_report.json"
    evidence_snapshot_path = output_dir / "cris_sme_evidence_snapshot.json"
    evidence_snapshot_path.write_text(
        json.dumps(output["evidence_snapshot"], indent=2),
        encoding="utf-8",
    )
    summary_report_path = write_summary_report(summary, output_dir / "cris_sme_summary.txt")
    html_report_path = write_html_report(
        build_html_report(output),
        output_dir / "cris_sme_report.html",
    )
    figure_paths = write_report_figures(output, figure_dir)
    history_figure_paths = write_history_figures(history_reports, figure_dir)
    appendix_paths = write_appendix_tables(output, output_dir)
    insurance_paths = write_cyber_insurance_evidence_pack(
        output["cyber_insurance_evidence"], output_dir
    )
    action_plan_paths = write_action_plan_outputs(
        output["action_plan_30_day"], output_dir
    )
    benchmark_paths = write_benchmark_outputs(
        output["benchmark_observation"],
        output["benchmark_comparison"],
        output_dir,
    )
    executive_pack_paths = write_executive_pack(output["executive_pack"], output_dir)
    narrator_paths = (
        write_plain_language_reports(narrator_output, output_dir)
        if narrator_output is not None
        else {}
    )

    output["report_artifacts"] = {
        "json_report": str(json_report_path),
        "evidence_snapshot": str(evidence_snapshot_path),
        "html_report": str(html_report_path),
        "summary_report": str(summary_report_path),
        "history_snapshot": str(history_snapshot_path),
        "appendix_tables": {key: str(value) for key, value in appendix_paths.items()},
        "cyber_insurance_pack": {key: str(value) for key, value in insurance_paths.items()},
        "action_plan_30_day": {key: str(value) for key, value in action_plan_paths.items()},
        "benchmark_outputs": {key: str(value) for key, value in benchmark_paths.items()},
        "executive_pack": {key: str(value) for key, value in executive_pack_paths.items()},
        "dashboard": {
            "dashboard_payload_json": str(dashboard_payload_path),
            "dashboard_html": str(dashboard_html_path),
        },
        "cyber_essentials_self_assessment": {},
        "cyber_essentials_review_console": {},
        "cyber_essentials_evaluation_metrics": {},
        "cyber_essentials_paper_exports": {},
        "plain_language_outputs": {
            key: str(value) for key, value in narrator_paths.items()
        },
        "figures": {key: str(value) for key, value in figure_paths.items()},
        "history_figures": {key: str(value) for key, value in history_figure_paths.items()},
    }
    rbom_path = output_dir / "cris_sme_risk_bill_of_materials.json"
    rbom = build_risk_bill_of_materials(
        output,
        artifact_paths=_flatten_artifact_paths(output["report_artifacts"]),
    )
    output["risk_bill_of_materials"] = rbom.model_dump(mode="json")
    output["assessment_assurance"] = build_assessment_assurance(output).model_dump(
        mode="json"
    )
    output["report_trust_badge"] = build_report_trust_badge(output).model_dump(
        mode="json"
    )
    provenance_graph = build_decision_provenance_graph(output)
    provenance_graph_path = output_dir / "cris_sme_decision_provenance_graph.json"
    output["decision_provenance_graph"] = provenance_graph.model_dump(mode="json")
    output["report_artifacts"]["decision_provenance_graph"] = str(
        write_decision_provenance_graph(provenance_graph, provenance_graph_path)
    )
    claim_pack = build_claim_verification_pack(output)
    claim_pack_path = output_dir / "cris_sme_claim_verification_pack.json"
    output["claim_verification_pack"] = claim_pack.model_dump(mode="json")
    output["report_artifacts"]["claim_verification_pack"] = str(
        write_claim_verification_pack(claim_pack, claim_pack_path)
    )
    assurance_case = build_assurance_case(output)
    assurance_case_path = output_dir / "cris_sme_assurance_case.json"
    output["assurance_case"] = assurance_case.model_dump(mode="json")
    output["report_artifacts"]["assurance_case"] = str(
        write_assurance_case(assurance_case, assurance_case_path)
    )
    claim_bound_narrative = build_claim_bound_narrative(output)
    output["claim_bound_narrative"] = claim_bound_narrative.model_dump(mode="json")
    output["report_artifacts"]["claim_bound_narrative"] = {
        key: str(value)
        for key, value in write_claim_bound_narrative(
            claim_bound_narrative,
            output_dir,
        ).items()
    }
    assurance_portal_path = output_dir / "cris_sme_assurance_portal.html"
    output["report_artifacts"]["assurance_portal"] = str(
        write_assurance_portal_html(
            build_assurance_portal_html(output),
            assurance_portal_path,
        )
    )
    ce_self_assessment_json_path = output_dir / "cris_sme_ce_self_assessment.json"
    ce_self_assessment_html_path = output_dir / "cris_sme_ce_self_assessment.html"
    output["report_artifacts"]["cyber_essentials_self_assessment"] = {
        "json": str(
            write_ce_self_assessment_pack(
                output["cyber_essentials_self_assessment"],
                ce_self_assessment_json_path,
            )
        ),
        "html": str(
            write_ce_self_assessment_html(
                build_ce_self_assessment_html(
                    output["cyber_essentials_self_assessment"]
                ),
                ce_self_assessment_html_path,
            )
        ),
    }
    ce_review_console_json_path = output_dir / "cris_sme_ce_review_console.json"
    ce_review_console_html_path = output_dir / "cris_sme_ce_review_console.html"
    output["report_artifacts"]["cyber_essentials_review_console"] = {
        "json": str(
            write_ce_review_console(
                output["cyber_essentials_review_console"],
                ce_review_console_json_path,
            )
        ),
        "html": str(
            write_ce_review_console_html(
                build_ce_review_console_html(
                    output["cyber_essentials_review_console"]
                ),
                ce_review_console_html_path,
            )
        ),
    }
    ce_evaluation_json_path = output_dir / "cris_sme_ce_evaluation_metrics.json"
    ce_evaluation_html_path = output_dir / "cris_sme_ce_evaluation_metrics.html"
    output["report_artifacts"]["cyber_essentials_evaluation_metrics"] = {
        "json": str(
            write_ce_evaluation_metrics(
                output["cyber_essentials_evaluation_metrics"],
                ce_evaluation_json_path,
            )
        ),
        "html": str(
            write_ce_evaluation_metrics_html(
                build_ce_evaluation_metrics_html(
                    output["cyber_essentials_evaluation_metrics"]
                ),
                ce_evaluation_html_path,
            )
        ),
    }
    output["report_artifacts"]["cyber_essentials_paper_exports"] = {
        key: str(value)
        for key, value in write_ce_paper_exports(
            output["cyber_essentials_evaluation_metrics"],
            output_dir,
        ).items()
    }
    selective_disclosure = build_selective_disclosure_package(output)
    output["selective_disclosure"] = selective_disclosure.model_dump(mode="json")
    selective_disclosure_path = output_dir / "cris_sme_selective_disclosure.json"
    evidence_room_path = output_dir / "cris_sme_evidence_room.html"
    output["report_artifacts"]["selective_disclosure"] = {
        "selective_disclosure_json": str(
            write_selective_disclosure_package(
                selective_disclosure,
                selective_disclosure_path,
            )
        ),
        "evidence_room_html": str(
            write_evidence_room_html(
                build_evidence_room_html(output["selective_disclosure"]),
                evidence_room_path,
            )
        ),
    }
    rbom = build_risk_bill_of_materials(
        output,
        artifact_paths=_flatten_artifact_paths(output["report_artifacts"]),
    )
    output["risk_bill_of_materials"] = rbom.model_dump(mode="json")
    output["report_artifacts"]["risk_bill_of_materials"] = str(
        write_risk_bill_of_materials(rbom, rbom_path)
    )
    write_json_report(output, json_report_path)

    print(json.dumps(output, indent=2))


def _collect_profiles() -> list:
    """Select the configured collector implementation."""
    collector_mode = get_collector_mode()

    if collector_mode == "azure":
        return AzureCollector(
            settings=get_azure_collector_settings()
        ).collect_profiles()

    if collector_mode == "mock":
        return MockCollector().collect_profiles()

    raise ValueError(
        f"Unsupported collector mode '{collector_mode}'. Use 'mock' or 'azure'."
    )


def _flatten_artifact_paths(artifacts: dict[str, object]) -> dict[str, Path]:
    """Flatten nested artifact dictionaries into RBOM hash inputs."""
    flattened: dict[str, Path] = {}

    def walk(prefix: str, value: object) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                walk(f"{prefix}.{key}" if prefix else str(key), child)
            return
        if isinstance(value, str) and value:
            if prefix == "json_report":
                return
            flattened[prefix] = Path(value)

    walk("", artifacts)
    return flattened


if __name__ == "__main__":
    main()
