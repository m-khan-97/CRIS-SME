# Tests for Cyber Essentials paper-ready exports.
from __future__ import annotations

import csv
import json

from cris_sme.engine.ce_evaluation import build_ce_evaluation_metrics
from cris_sme.engine.ce_questionnaire import build_ce_self_assessment_pack
from cris_sme.engine.ce_review import build_ce_review_console
from cris_sme.reporting.ce_paper_export import (
    build_ce_chart_data,
    build_ce_paper_tables_markdown,
    write_ce_paper_exports,
)


def test_build_ce_paper_tables_markdown_contains_all_manuscript_tables() -> None:
    metrics = _metrics()

    markdown = build_ce_paper_tables_markdown(metrics)

    assert "# CRIS-SME Cyber Essentials Paper Tables" in markdown
    assert "## Table 1. CE Question Observability By Evidence Class" in markdown
    assert "## Table 2. Technical-Question Observability" in markdown
    assert "## Table 3. Evidence Gap Taxonomy" in markdown
    assert "## Table 4. Review Outcomes" in markdown
    assert "## Table 5. Proposed CE Answers" in markdown
    assert "## Table 6. Top Controls Contributing To CE Answer Failures" in markdown
    assert "## Table 7. Section-Level Coverage" in markdown
    assert "Cloud-supported entries: `28` (`26.42%`)" in markdown


def test_build_ce_chart_data_exposes_headline_and_series() -> None:
    chart_data = build_ce_chart_data(_metrics())

    assert chart_data["chart_schema_version"] == "0.1.0"
    assert chart_data["headline"]["question_count"] == 106
    assert chart_data["headline"]["cloud_supported_rate"] == 26.42
    assert "gap_taxonomy" in chart_data["series"]
    assert "proposed_answers" in chart_data["series"]
    assert chart_data["series"]["technical_observability_by_evidence_class"]


def test_write_ce_paper_exports_persists_markdown_csv_and_chart_json(tmp_path) -> None:
    paths = write_ce_paper_exports(_metrics(), tmp_path)

    expected_keys = {
        "ce_paper_tables_markdown",
        "ce_paper_tables_csv",
        "ce_observability_summary_csv",
        "ce_gap_taxonomy_csv",
        "ce_section_coverage_csv",
        "ce_chart_data_json",
    }
    assert set(paths) == expected_keys
    for path in paths.values():
        assert path.exists()

    markdown = paths["ce_paper_tables_markdown"].read_text(encoding="utf-8")
    assert "Human reviewer agreement" in markdown
    assert "AI-assisted draft acceptance" in markdown

    with paths["ce_observability_summary_csv"].open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["label"] == "direct_cloud"
    assert rows[0]["count"] == "5"

    with paths["ce_paper_tables_csv"].open(encoding="utf-8", newline="") as handle:
        all_rows = list(csv.DictReader(handle))
    assert {row["table"] for row in all_rows} >= {
        "observability_by_evidence_class",
        "evidence_gap_taxonomy",
        "section_coverage",
    }

    chart_data = json.loads(paths["ce_chart_data_json"].read_text(encoding="utf-8"))
    assert chart_data["headline"]["technical_cloud_supported_rate"] == 35.48


def _metrics() -> dict:
    pack = build_ce_self_assessment_pack({"prioritized_risks": []})
    console = build_ce_review_console(pack)
    return build_ce_evaluation_metrics(pack, console)
