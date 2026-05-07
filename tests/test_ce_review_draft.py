# Tests for AI-assisted Cyber Essentials pilot review draft generation.
from __future__ import annotations

import json

from cris_sme.engine.ce_evaluation import build_ce_evaluation_metrics
from cris_sme.engine.ce_questionnaire import build_ce_self_assessment_pack
from cris_sme.engine.ce_review import build_ce_review_console
from cris_sme.engine.ce_review_draft import (
    build_ce_review_decision_draft,
    write_ce_review_decision_draft,
)


def test_build_ce_review_decision_draft_is_conservative() -> None:
    mapping = {
        "mapping_schema_version": "test",
        "question_set": {"name": "Danzell", "version": "test"},
        "questions": [
            {
                "question_id": "Q1",
                "section": "firewalls",
                "research_scope": "technical_control",
                "short_paraphrase": "Direct cloud firewall check",
                "evidence_class": "direct_cloud",
                "supporting_control_ids": ["NET-001"],
                "current_cris_sme_signals": ["network_inventory"],
                "planned_evidence_paths": ["NSG rules"],
                "human_review_required": True,
            },
            {
                "question_id": "Q2",
                "section": "user_access_control",
                "research_scope": "technical_control",
                "short_paraphrase": "Inferred identity risk check",
                "evidence_class": "inferred_cloud",
                "supporting_control_ids": ["IAM-001"],
                "current_cris_sme_signals": ["identity_inventory"],
                "planned_evidence_paths": ["Graph evidence"],
                "human_review_required": True,
            },
            {
                "question_id": "Q3",
                "section": "software_update_management",
                "research_scope": "technical_control",
                "short_paraphrase": "Inferred clean patch check",
                "evidence_class": "inferred_cloud",
                "supporting_control_ids": ["CMP-001"],
                "current_cris_sme_signals": ["compute_inventory"],
                "planned_evidence_paths": ["patch assessment"],
                "human_review_required": True,
            },
            {
                "question_id": "Q4",
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
                "finding_id": "iam-001-live",
                "control_id": "IAM-001",
                "title": "MFA posture is not fully observable",
                "priority": "High",
                "score": 74.0,
            }
        ]
    }
    pack = build_ce_self_assessment_pack(report, mapping=mapping)

    draft = build_ce_review_decision_draft(
        pack,
        reviewer="Pilot reviewer",
        reviewed_at="2026-05-07T00:00:00Z",
    )

    decisions = draft["review_decisions"]
    assert set(decisions) == {"Q1", "Q2", "Q3"}
    assert decisions["Q1"]["state"] == "accepted"
    assert decisions["Q1"]["final_answer"] == "Yes"
    assert decisions["Q2"]["state"] == "accepted"
    assert decisions["Q2"]["final_answer"] == "No"
    assert decisions["Q3"]["state"] == "needs_evidence"
    assert decisions["Q3"]["final_answer"] == "Cannot determine"
    assert "AI-assisted internal draft" in draft["research_boundary"]
    assert draft["summary"]["state_counts"] == {
        "accepted": 2,
        "needs_evidence": 1,
    }


def test_draft_review_decisions_feed_evaluation_metrics() -> None:
    pack = build_ce_self_assessment_pack({"prioritized_risks": []})
    draft = build_ce_review_decision_draft(pack)
    console = build_ce_review_console(
        pack,
        review_decisions=draft["review_decisions"],
    )

    metrics = build_ce_evaluation_metrics(pack, console)

    assert metrics["review_metrics"]["reviewed_count"] == 28
    assert metrics["review_metrics"]["agreement_evaluable_count"] == 5
    assert metrics["review_metrics"]["agreement_rate"] == 100.0
    assert metrics["review_metrics"]["needs_evidence_count"] == 23
    assert metrics["review_metrics"]["pending_count"] == 78


def test_ce_review_decision_draft_json_is_written(tmp_path) -> None:
    pack = build_ce_self_assessment_pack({"prioritized_risks": []})
    draft = build_ce_review_decision_draft(pack)

    path = write_ce_review_decision_draft(
        draft,
        tmp_path / "ce_review_decision_draft.json",
    )

    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["review_decision_draft_schema_version"] == "0.1.0"
    assert written["review_decisions"]
