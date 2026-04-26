# Appendix export helpers for paper-ready CRIS-SME summary tables.
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def write_appendix_tables(
    report: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write compact appendix tables in Markdown and CSV formats."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = target_dir / "results_appendix.md"
    csv_path = target_dir / "prioritized_risks.csv"

    markdown_path.write_text(build_results_appendix_markdown(report), encoding="utf-8")
    write_prioritized_risks_csv(report, csv_path)

    return {
        "results_appendix_markdown": markdown_path,
        "prioritized_risks_csv": csv_path,
    }


def build_results_appendix_markdown(report: dict[str, Any]) -> str:
    """Build a compact markdown appendix from the current report."""
    category_scores = report.get("category_scores", {})
    evaluation_mode_summary = report.get("evaluation_mode_summary", {})
    history_comparison = report.get("history_comparison", {})
    prioritized_risks = report.get("prioritized_risks", [])
    remediation = report.get("budget_aware_remediation", {})
    control_deltas = []
    if isinstance(history_comparison, dict):
        control_deltas = history_comparison.get("control_score_deltas_vs_distinct_mode", [])

    category_lines = ["| Category | Score |", "| --- | ---: |"]
    if isinstance(category_scores, dict):
        for category, score in category_scores.items():
            category_lines.append(f"| {category} | {float(score):.2f} |")

    evaluation_mode_lines = [
        "| Mode | Evidence Class | Overall Risk | Generated Findings | Non-Compliant Findings | Collector |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    modes = (
        evaluation_mode_summary.get("modes", [])
        if isinstance(evaluation_mode_summary, dict)
        else []
    )
    if isinstance(modes, list):
        for mode in modes:
            if not isinstance(mode, dict):
                continue
            evaluation_mode_lines.append(
                "| "
                f"{mode.get('label', '')} | "
                f"{mode.get('evidence_class', '')} | "
                f"{float(mode.get('overall_risk_score', 0.0)):.2f} | "
                f"{int(mode.get('generated_findings', 0))} | "
                f"{int(mode.get('non_compliant_findings', 0))} | "
                f"{mode.get('collector_mode', '')} |"
            )

    comparison_lines = ["| Metric | Value |", "| --- | --- |"]
    if isinstance(history_comparison, dict):
        for key in (
            "history_count",
            "current_collector_mode",
            "previous_collector_mode",
            "previous_distinct_mode",
            "overall_risk_delta",
            "overall_risk_delta_vs_distinct_mode",
            "non_compliant_findings_delta",
            "latest_generated_at",
            "previous_generated_at",
            "previous_distinct_generated_at",
        ):
            value = history_comparison.get(key)
            if value is not None:
                comparison_lines.append(
                    f"| {key.replace('_', ' ').title()} | {value} |"
                )

    top_risk_lines = [
        "| Control | Category | Priority | Score | Cost Tier | Value Score |",
        "| --- | --- | --- | ---: | --- | ---: |",
    ]
    if isinstance(prioritized_risks, list):
        for risk in prioritized_risks[:10]:
            if not isinstance(risk, dict):
                continue
            top_risk_lines.append(
                "| "
                f"{risk.get('control_id', '')} | "
                f"{risk.get('category', '')} | "
                f"{risk.get('priority', '')} | "
                f"{float(risk.get('score', 0.0)):.2f} | "
                f"{risk.get('remediation_cost_tier', '')} | "
                f"{float(risk.get('remediation_value_score', 0.0)):.2f} |"
            )

    remediation_lines = [
        "| Budget Profile | Budget Cap | Actions | Cumulative Risk | Avg Value Score |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    budget_profiles = remediation.get("budget_profiles", []) if isinstance(remediation, dict) else []
    if isinstance(budget_profiles, list):
        for profile in budget_profiles:
            if not isinstance(profile, dict):
                continue
            remediation_lines.append(
                "| "
                f"{profile.get('label', '')} | "
                f"{profile.get('max_monthly_cost_gbp', 0)} | "
                f"{profile.get('total_recommended', 0)} | "
                f"{float(profile.get('cumulative_risk_score', 0.0)):.2f} | "
                f"{float(profile.get('average_value_score', 0.0)):.2f} |"
            )

    delta_lines = [
        "| Control | Category | Current | Previous Distinct | Delta |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    if isinstance(control_deltas, list):
        for item in control_deltas[:10]:
            if not isinstance(item, dict):
                continue
            delta_lines.append(
                "| "
                f"{item.get('control_id', '')} | "
                f"{item.get('category', '')} | "
                f"{float(item.get('current_score', 0.0)):.2f} | "
                f"{float(item.get('previous_score', 0.0)):.2f} | "
                f"{float(item.get('delta', 0.0)):.2f} |"
            )

    overall = float(report.get("overall_risk_score", 0.0))
    summary = str(report.get("summary", "CRIS-SME results summary"))
    generated_at = str(report.get("generated_at", "unknown"))

    return "\n".join(
        [
            "# CRIS-SME Results Appendix",
            "",
            f"- Generated at: `{generated_at}`",
            f"- Overall risk score: `{overall:.2f}`",
            f"- Summary: {summary}",
            "",
            "## Category Scores",
            "",
            *category_lines,
            "",
            "## Three-Mode Evaluation Summary",
            "",
            *evaluation_mode_lines,
            "",
            "## Archived Run Comparison",
            "",
            *comparison_lines,
            "",
            "## Top Prioritized Risks",
            "",
            *top_risk_lines,
            "",
            "## Budget-Aware Remediation Packs",
            "",
            *remediation_lines,
            "",
            "## Top Control Deltas Versus Previous Distinct Mode",
            "",
            *delta_lines,
            "",
        ]
    )


def write_prioritized_risks_csv(report: dict[str, Any], output_path: str | Path) -> Path:
    """Write prioritized risks to a CSV file for appendix and spreadsheet workflows."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    prioritized_risks = report.get("prioritized_risks", [])

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "control_id",
                "title",
                "category",
                "priority",
                "severity",
                "score",
                "organization",
                "remediation_cost_tier",
                "remediation_value_score",
                "budget_fit_profiles",
                "remediation_summary",
            ]
        )
        if isinstance(prioritized_risks, list):
            for risk in prioritized_risks:
                if not isinstance(risk, dict):
                    continue
                writer.writerow(
                    [
                        risk.get("control_id", ""),
                        risk.get("title", ""),
                        risk.get("category", ""),
                        risk.get("priority", ""),
                        risk.get("severity", ""),
                        risk.get("score", ""),
                        risk.get("organization", ""),
                        risk.get("remediation_cost_tier", ""),
                        risk.get("remediation_value_score", ""),
                        ",".join(risk.get("budget_fit_profiles", [])),
                        risk.get("remediation_summary", ""),
                    ]
                )
    return path
