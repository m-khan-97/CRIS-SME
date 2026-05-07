# Tests for Cyber Essentials self-assessment answer-pack generation.
from __future__ import annotations

import json

from cris_sme.engine.ce_questionnaire import (
    build_ce_self_assessment_pack,
    load_ce_question_mapping,
    write_ce_self_assessment_pack,
)
from cris_sme.reporting.ce_questionnaire_report import (
    build_ce_self_assessment_html,
    write_ce_self_assessment_html,
)


def test_build_ce_self_assessment_pack_links_cloud_questions_to_risks() -> None:
    report = {
        "prioritized_risks": [
            {
                "finding_id": "fdg_net_001",
                "control_id": "NET-001",
                "title": "Administrative services are exposed",
                "priority": "High",
                "score": 72.12,
                "evidence": ["1 asset exposes SSH to the public internet"],
                "evidence_quality": {"sufficiency": "direct"},
            },
            {
                "finding_id": "fdg_iam_001",
                "control_id": "IAM-001",
                "title": "Conditional Access is not enforced",
                "priority": "High",
                "score": 68.2,
                "evidence": [
                    "Conditional access for privileged administrators was not observable"
                ],
                "evidence_quality": {"sufficiency": "partial"},
            },
        ]
    }

    pack = build_ce_self_assessment_pack(report)

    assert pack["question_count"] == 106
    assert pack["technical_question_count"] == 62
    assert pack["coverage_summary"]["technical_cloud_supported_count"] == 22
    firewall_admin = next(
        answer for answer in pack["answers"] if answer["question_id"] == "A4.9"
    )
    assert firewall_admin["proposed_status"] == "supported_risk_found"
    assert firewall_admin["proposed_answer"] == "No"
    assert "candidate CE answer is No" in firewall_admin["answer_basis"]
    assert firewall_admin["linked_findings"][0]["finding_id"] == "fdg_net_001"
    assert "SSH" in firewall_admin["evidence"][0]

    endpoint_answer = next(
        answer for answer in pack["answers"] if answer["question_id"] == "A8.1"
    )
    assert endpoint_answer["proposed_status"] == "endpoint_required"
    assert endpoint_answer["proposed_answer"] == "Cannot determine"
    assert endpoint_answer["human_review_required"] is True


def test_build_ce_self_assessment_pack_marks_cloud_no_issue_when_no_linked_risk() -> None:
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
            }
        ],
    }

    pack = build_ce_self_assessment_pack({"prioritized_risks": []}, mapping=mapping)

    assert pack["answers"][0]["proposed_status"] == "supported_no_issue"
    assert pack["answers"][0]["proposed_answer"] == "Yes"
    assert pack["answers"][0]["linked_findings"] == []


def test_ce_self_assessment_pack_and_html_are_written(tmp_path) -> None:
    pack = build_ce_self_assessment_pack({"prioritized_risks": []})

    json_path = write_ce_self_assessment_pack(
        pack,
        tmp_path / "ce_self_assessment.json",
    )
    html = build_ce_self_assessment_html(pack)
    html_path = write_ce_self_assessment_html(
        html,
        tmp_path / "ce_self_assessment.html",
    )

    written_pack = json.loads(json_path.read_text(encoding="utf-8"))
    assert written_pack["pack_name"] == pack["pack_name"]
    assert "Cyber Essentials Pre-Assessment Pack" in html
    assert "Danzell" in html
    assert html_path.read_text(encoding="utf-8") == html


def test_load_ce_question_mapping_reads_default_dataset() -> None:
    mapping = load_ce_question_mapping()

    assert mapping["question_set"]["name"] == "Danzell"
    assert len(mapping["questions"]) == 106
