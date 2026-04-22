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
    build_collector_coverage,
    build_run_metadata,
    enrich_report_finding_lifecycle,
    load_compliance_mappings,
    load_exception_registry,
)
from cris_sme.engine.benchmark import (
    build_benchmark_comparison,
    build_benchmark_observation,
    load_benchmark_dataset,
)
from cris_sme.engine.uk_readiness import build_cyber_essentials_readiness
from cris_sme.engine.scoring import score_findings
from cris_sme.policies import load_policy_pack_metadata
from cris_sme.reporting import (
    archive_report_snapshot,
    build_dashboard_html,
    build_dashboard_payload,
    build_history_comparison,
    build_cyber_insurance_evidence_pack,
    build_executive_pack,
    build_html_report,
    build_json_report,
    build_summary_report,
    load_report_history,
    maybe_generate_plain_language_narrative,
    write_appendix_tables,
    write_action_plan_outputs,
    write_benchmark_outputs,
    write_cyber_insurance_evidence_pack,
    write_dashboard_html,
    write_dashboard_payload,
    write_executive_pack,
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

    # Refresh benchmark outputs now that run metadata fields are finalized.
    benchmark_dataset = load_benchmark_dataset()
    output["benchmark_observation"] = build_benchmark_observation(output).model_dump()
    output["benchmark_comparison"] = build_benchmark_comparison(
        output,
        benchmark_dataset,
    )

    # Build history comparison using existing snapshots plus the current in-memory run.
    comparison_reports = [*history_reports_before, output]
    output["history_comparison"] = build_history_comparison(comparison_reports)

    # Attach finding lifecycle state from historical snapshots and approved exceptions.
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

    output["cyber_essentials_readiness"] = build_cyber_essentials_readiness(findings)
    output["cyber_insurance_evidence"] = build_cyber_insurance_evidence_pack(output)
    output["action_plan_30_day"] = build_30_day_action_plan(
        result.prioritized_findings
    ).model_dump()
    output["executive_pack"] = build_executive_pack(output)

    # Build dashboard bundle after lifecycle, trend, and remediation layers are fully populated.
    dashboard_payload = build_dashboard_payload(output, comparison_reports)
    dashboard_payload_path = write_dashboard_payload(dashboard_payload, output_dir)
    dashboard_html_path = write_dashboard_html(
        build_dashboard_html(dashboard_payload),
        output_dir / "cris_sme_dashboard.html",
    )

    json_report_path = write_json_report(output, output_dir / "cris_sme_report.json")
    summary_report_path = write_summary_report(
        summary, output_dir / "cris_sme_summary.txt"
    )
    html_report = build_html_report(output)
    html_report_path = write_html_report(html_report, output_dir / "cris_sme_report.html")
    figure_paths = write_report_figures(output, figure_dir)
    history_snapshot_path = archive_report_snapshot(
        output,
        output_dir,
        timestamp=generated_at,
    )
    history_reports = load_report_history(output_dir / "history")
    output["history_comparison"] = build_history_comparison(history_reports)
    history_figure_paths = write_history_figures(history_reports, figure_dir)
    appendix_paths = write_appendix_tables(output, output_dir)
    insurance_paths = write_cyber_insurance_evidence_pack(
        output["cyber_insurance_evidence"], output_dir
    )
    action_plan_paths = write_action_plan_outputs(output["action_plan_30_day"], output_dir)
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
        "plain_language_outputs": {
            key: str(value) for key, value in narrator_paths.items()
        },
        "figures": {key: str(value) for key, value in figure_paths.items()},
        "history_figures": {key: str(value) for key, value in history_figure_paths.items()},
    }
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


if __name__ == "__main__":
    main()
