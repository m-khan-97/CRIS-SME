# Paper-ready Cyber Essentials table exports.
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def write_ce_paper_exports(
    metrics: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write CE paper tables, CSV datasets, and chart-ready JSON."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = target_dir / "cris_sme_ce_paper_tables.md"
    all_tables_csv_path = target_dir / "cris_sme_ce_paper_tables.csv"
    observability_csv_path = target_dir / "cris_sme_ce_observability_summary.csv"
    gap_taxonomy_csv_path = target_dir / "cris_sme_ce_gap_taxonomy.csv"
    section_coverage_csv_path = target_dir / "cris_sme_ce_section_coverage.csv"
    chart_json_path = target_dir / "cris_sme_ce_chart_data.json"

    markdown_path.write_text(build_ce_paper_tables_markdown(metrics), encoding="utf-8")
    write_ce_all_paper_tables_csv(metrics, all_tables_csv_path)
    write_rows_csv(
        _paper_table(metrics, "observability_by_evidence_class"),
        observability_csv_path,
    )
    write_rows_csv(_gap_taxonomy_rows(metrics), gap_taxonomy_csv_path)
    write_rows_csv(
        _paper_table(metrics, "section_coverage"),
        section_coverage_csv_path,
    )
    chart_json_path.write_text(
        json.dumps(build_ce_chart_data(metrics), indent=2),
        encoding="utf-8",
    )

    return {
        "ce_paper_tables_markdown": markdown_path,
        "ce_paper_tables_csv": all_tables_csv_path,
        "ce_observability_summary_csv": observability_csv_path,
        "ce_gap_taxonomy_csv": gap_taxonomy_csv_path,
        "ce_section_coverage_csv": section_coverage_csv_path,
        "ce_chart_data_json": chart_json_path,
    }


def build_ce_paper_tables_markdown(metrics: dict[str, Any]) -> str:
    """Build a manuscript-ready Markdown appendix for CE metrics."""
    question_set = metrics.get("question_set", {})
    if not isinstance(question_set, dict):
        question_set = {}
    observability = _dict(metrics.get("observability_metrics"))
    review = _dict(metrics.get("review_metrics"))

    lines = [
        "# CRIS-SME Cyber Essentials Paper Tables",
        "",
        f"- Question set: `{question_set.get('name', 'unknown')}` version `{question_set.get('version', 'unknown')}`",
        f"- Requirements version: `{question_set.get('requirements_version', 'unknown')}`",
        f"- Total mapped entries: `{metrics.get('question_count', 0)}`",
        f"- Technical-control entries: `{metrics.get('technical_question_count', 0)}`",
        f"- Cloud-supported entries: `{observability.get('cloud_supported_count', 0)}` (`{observability.get('cloud_supported_rate', 0)}%`)",
        f"- Technical cloud-supported entries: `{observability.get('technical_cloud_supported_count', 0)}` (`{observability.get('technical_cloud_supported_rate', 0)}%`)",
        f"- Reviewer agreement: `{review.get('agreement_count', 0)}` of `{review.get('agreement_evaluable_count', 0)}` (`{review.get('agreement_rate', 0)}%`)",
        "",
        "## Table 1. CE Question Observability By Evidence Class",
        "",
        *_markdown_table(_paper_table(metrics, "observability_by_evidence_class")),
        "",
        "## Table 2. Technical-Question Observability",
        "",
        *_markdown_table(_paper_table(metrics, "technical_observability_by_evidence_class")),
        "",
        "## Table 3. Evidence Gap Taxonomy",
        "",
        *_markdown_table(_gap_taxonomy_rows(metrics)),
        "",
        "## Table 4. Review Outcomes",
        "",
        *_markdown_table(_paper_table(metrics, "review_outcomes")),
        "",
        "## Table 5. Proposed CE Answers",
        "",
        *_markdown_table(_paper_table(metrics, "proposed_answers")),
        "",
        "## Table 6. Top Controls Contributing To CE Answer Failures",
        "",
        *_markdown_table(_paper_table(metrics, "control_failure_contribution")),
        "",
        "## Table 7. Section-Level Coverage",
        "",
        *_markdown_table(_paper_table(metrics, "section_coverage")),
        "",
        "## Reproducibility Notes",
        "",
        *[f"- {note}" for note in metrics.get("evaluation_notes", []) if str(note).strip()],
        f"- {metrics.get('deterministic_score_impact', '')}",
        "",
    ]
    return "\n".join(lines)


def write_ce_all_paper_tables_csv(
    metrics: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """Write all CE paper tables to one long-form CSV."""
    rows: list[dict[str, Any]] = []
    table_map = {
        "observability_by_evidence_class": _paper_table(
            metrics,
            "observability_by_evidence_class",
        ),
        "technical_observability_by_evidence_class": _paper_table(
            metrics,
            "technical_observability_by_evidence_class",
        ),
        "evidence_gap_taxonomy": _gap_taxonomy_rows(metrics),
        "review_outcomes": _paper_table(metrics, "review_outcomes"),
        "proposed_answers": _paper_table(metrics, "proposed_answers"),
        "final_answers": _paper_table(metrics, "final_answers"),
        "control_failure_contribution": _paper_table(
            metrics,
            "control_failure_contribution",
        ),
        "section_coverage": _paper_table(metrics, "section_coverage"),
    }
    for table_name, table_rows in table_map.items():
        for row in table_rows:
            normalized = {"table": table_name}
            normalized.update(row)
            rows.append(normalized)
    return write_rows_csv(rows, output_path)


def write_rows_csv(rows: list[dict[str, Any]], output_path: str | Path) -> Path:
    """Write a list of dictionaries to CSV with stable columns."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_cell(row.get(key, "")) for key in headers})
    return path


def build_ce_chart_data(metrics: dict[str, Any]) -> dict[str, Any]:
    """Build compact chart-ready data for paper figures."""
    observability = _dict(metrics.get("observability_metrics"))
    review = _dict(metrics.get("review_metrics"))
    return {
        "chart_schema_version": "0.1.0",
        "question_set": metrics.get("question_set", {}),
        "headline": {
            "question_count": metrics.get("question_count", 0),
            "technical_question_count": metrics.get("technical_question_count", 0),
            "cloud_supported_rate": observability.get("cloud_supported_rate", 0),
            "technical_cloud_supported_rate": observability.get(
                "technical_cloud_supported_rate",
                0,
            ),
            "agreement_rate": review.get("agreement_rate", 0),
        },
        "series": {
            "observability_by_evidence_class": _paper_table(
                metrics,
                "observability_by_evidence_class",
            ),
            "technical_observability_by_evidence_class": _paper_table(
                metrics,
                "technical_observability_by_evidence_class",
            ),
            "gap_taxonomy": _gap_taxonomy_rows(metrics),
            "proposed_answers": _paper_table(metrics, "proposed_answers"),
            "final_answers": _paper_table(metrics, "final_answers"),
            "section_coverage": _paper_table(metrics, "section_coverage"),
            "control_failure_contribution": _paper_table(
                metrics,
                "control_failure_contribution",
            ),
        },
        "deterministic_score_impact": metrics.get("deterministic_score_impact", ""),
    }


def _paper_table(metrics: dict[str, Any], table_name: str) -> list[dict[str, Any]]:
    paper_tables = metrics.get("paper_tables", {})
    if not isinstance(paper_tables, dict):
        return []
    rows = paper_tables.get(table_name, [])
    if not isinstance(rows, list):
        return []
    return [_normalize_row(row) for row in rows if isinstance(row, dict)]


def _gap_taxonomy_rows(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    taxonomy = metrics.get("evidence_gap_taxonomy", {})
    if not isinstance(taxonomy, dict):
        return []
    rows = []
    for evidence_class, detail in sorted(taxonomy.items()):
        if not isinstance(detail, dict):
            continue
        rows.append(
            {
                "evidence_class": evidence_class,
                "count": detail.get("count", 0),
                "rate": detail.get("rate", 0),
                "description": detail.get("description", ""),
                "sample_question_ids": detail.get("sample_question_ids", []),
            }
        )
    return [_normalize_row(row) for row in rows]


def _markdown_table(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["No rows available."]
    headers = sorted({key for row in rows for key in row})
    lines = [
        "| " + " | ".join(_title(key) for key in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(_markdown_cell(row.get(header, "")) for header in headers)
            + " |"
        )
    return lines


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {str(key): value for key, value in row.items()}


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _title(value: str) -> str:
    return value.replace("_", " ").title()


def _csv_cell(value: object) -> object:
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return value


def _markdown_cell(value: object) -> str:
    text = str(_csv_cell(value))
    return text.replace("|", "\\|").replace("\n", " ")
