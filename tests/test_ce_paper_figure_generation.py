import json
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.generate_ce_paper_figures import main


def test_generate_ce_paper_figures_from_metrics(tmp_path: Path) -> None:
    metrics = {
        "observability_metrics": {"cloud_supported_count": 28},
        "review_metrics": {"agreement_count": 23, "agreement_evaluable_count": 23},
        "paper_tables": {
            "observability_by_evidence_class": [
                {"label": "direct_cloud", "count": 5},
                {"label": "inferred_cloud", "count": 23},
                {"label": "endpoint_required", "count": 24},
                {"label": "policy_required", "count": 19},
                {"label": "manual_required", "count": 35},
            ],
            "proposed_answers": [
                {"label": "No", "count": 23},
                {"label": "Yes", "count": 5},
                {"label": "Cannot determine", "count": 78},
            ],
        },
    }
    report = {
        "overall_risk_score": 40.16,
        "category_scores": {
            "IAM": 32.51,
            "Network": 58.42,
            "Data": 41.74,
        },
    }
    metrics_path = tmp_path / "metrics.json"
    report_path = tmp_path / "report.json"
    out_dir = tmp_path / "figures"
    metrics_path.write_text(json.dumps(metrics), encoding="utf-8")
    report_path.write_text(json.dumps(report), encoding="utf-8")

    result = main(
        [
            "--metrics",
            str(metrics_path),
            "--report",
            str(report_path),
            "--out-dir",
            str(out_dir),
        ]
    )

    assert result == 0
    figures = sorted(out_dir.glob("*.svg"))
    assert len(figures) == 4
    for figure in figures:
        root = ET.parse(figure).getroot()
        assert root.tag.endswith("svg")

    evidence_svg = (out_dir / "ce-evidence-class-distribution.svg").read_text(
        encoding="utf-8"
    )
    assert "direct cloud" in evidence_svg
    assert "35" in evidence_svg
