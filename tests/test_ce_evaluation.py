# Tests for Cyber Essentials evaluation metrics generation.
from __future__ import annotations

import json

from cris_sme.engine.ce_evaluation import (
    build_ce_evaluation_metrics,
    write_ce_evaluation_metrics,
)
from cris_sme.engine.ce_questionnaire import build_ce_self_assessment_pack
from cris_sme.engine.ce_review import build_ce_review_console
from cris_sme.reporting.ce_evaluation_report import (
    build_ce_evaluation_metrics_html,
    write_ce_evaluation_metrics_html,
)


def test_build_ce_evaluation_metrics_counts_observability_and_review() -> None:
    pack = build_ce_self_assessment_pack({"prioritized_risks": []})
    console = build_ce_review_console(pack)

    metrics = build_ce_evaluation_metrics(pack, console)

    assert metrics["metrics_name"] == "CRIS-SME Cyber Essentials Evaluation Metrics Pack"
    assert metrics["question_count"] == 106
    assert metrics["technical_question_count"] == 62
    assert metrics["observability_metrics"]["cloud_supported_count"] == 28
    assert metrics["observability_metrics"]["cloud_supported_rate"] == 26.42
    assert metrics["observability_metrics"]["technical_cloud_supported_count"] == 22
    assert metrics["observability_metrics"]["technical_cloud_supported_rate"] == 35.48
    assert metrics["review_metrics"]["pending_count"] == 106
    assert metrics["review_metrics"]["agreement_rate"] == 0.0
    assert metrics["status_counts"]["proposed_answer_counts"] == {
        "Cannot determine": 78,
        "Yes": 28,
    }
    assert metrics["evidence_gap_taxonomy"]["endpoint_required"]["count"] == 24
    assert "never change CRIS-SME deterministic" in metrics["deterministic_score_impact"]


def test_build_ce_evaluation_metrics_calculates_reviewer_agreement() -> None:
    mapping = {
        "mapping_schema_version": "test",
        "question_set": {"name": "Danzell", "version": "test"},
        "questions": [
            {
                "question_id": "Q1",
                "section": "firewalls",
                "research_scope": "technical_control",
                "short_paraphrase": "Cloud firewall check",
                "evidence_class": "direct_cloud",
                "supporting_control_ids": ["NET-001"],
                "current_cris_sme_signals": ["network_inventory"],
                "planned_evidence_paths": ["network rules"],
                "human_review_required": True,
            },
            {
                "question_id": "Q2",
                "section": "user_access_control",
                "research_scope": "technical_control",
                "short_paraphrase": "Privileged user check",
                "evidence_class": "inferred_cloud",
                "supporting_control_ids": ["IAM-001"],
                "current_cris_sme_signals": ["identity_inventory"],
                "planned_evidence_paths": ["Graph permissions"],
                "human_review_required": True,
            },
            {
                "question_id": "Q3",
                "section": "malware_protection",
                "research_scope": "technical_control",
                "short_paraphrase": "Endpoint malware check",
                "evidence_class": "endpoint_required",
                "supporting_control_ids": ["CMP-002"],
                "current_cris_sme_signals": [],
                "planned_evidence_paths": ["MDM inventory"],
                "human_review_required": True,
            },
        ],
    }
    report = {
        "prioritized_risks": [
            {
                "finding_id": "fdg_net_001",
                "control_id": "NET-001",
                "title": "Administrative exposure",
                "priority": "High",
                "score": 70.0,
                "evidence": ["SSH is exposed"],
                "evidence_quality": {"sufficiency": "direct"},
            }
        ]
    }
    pack = build_ce_self_assessment_pack(report, mapping=mapping)
    console = build_ce_review_console(
        pack,
        review_decisions={
            "Q1": {"state": "accepted"},
            "Q2": {
                "state": "overridden",
                "final_status": "manual_override",
                "final_answer": "No",
            },
            "Q3": {"state": "needs_evidence"},
        },
    )

    metrics = build_ce_evaluation_metrics(pack, console)

    assert metrics["review_metrics"]["reviewed_count"] == 3
    assert metrics["review_metrics"]["agreement_evaluable_count"] == 2
    assert metrics["review_metrics"]["agreement_count"] == 1
    assert metrics["review_metrics"]["agreement_rate"] == 50.0
    assert "proposed_answer" in metrics["review_metrics"]["agreement_basis"]
    assert metrics["review_metrics"]["needs_evidence_count"] == 1
    assert metrics["top_controls_causing_ce_answer_failures"][0]["control_id"] == "NET-001"
    assert metrics["top_controls_causing_ce_answer_failures"][0]["affected_question_count"] == 1


def test_ce_evaluation_metrics_json_and_html_are_written(tmp_path) -> None:
    pack = build_ce_self_assessment_pack({"prioritized_risks": []})
    console = build_ce_review_console(pack)
    metrics = build_ce_evaluation_metrics(pack, console)

    json_path = write_ce_evaluation_metrics(
        metrics,
        tmp_path / "ce_evaluation_metrics.json",
    )
    html = build_ce_evaluation_metrics_html(metrics)
    html_path = write_ce_evaluation_metrics_html(
        html,
        tmp_path / "ce_evaluation_metrics.html",
    )

    written_metrics = json.loads(json_path.read_text(encoding="utf-8"))
    assert written_metrics["metrics_schema_version"] == "0.1.0"
    assert "Cyber Essentials Evaluation Metrics" in html
    assert "Paper Tables" in html
    assert html_path.read_text(encoding="utf-8") == html
