# Tests for Cyber Essentials evidence review console generation.
from __future__ import annotations

import json

from cris_sme.engine.ce_questionnaire import build_ce_self_assessment_pack
from cris_sme.engine.ce_review import (
    build_ce_review_console,
    write_ce_review_console,
)
from cris_sme.reporting.ce_review_console import (
    build_ce_review_console_html,
    write_ce_review_console_html,
)


def test_build_ce_review_console_defaults_entries_to_pending() -> None:
    pack = build_ce_self_assessment_pack({"prioritized_risks": []})

    console = build_ce_review_console(pack, generated_at="2026-05-07T00:00:00Z")

    assert console["console_name"] == "CRIS-SME Cyber Essentials Evidence Review Console"
    assert console["generated_at"] == "2026-05-07T00:00:00Z"
    assert console["question_count"] == 106
    assert console["review_summary"]["review_state_counts"] == {"pending": 106}
    first_entry = console["entries"][0]
    assert first_entry["review_decision"]["state"] == "pending"
    assert first_entry["review_decision"]["final_status"] == "pending_human_review"
    assert first_entry["review_decision"]["final_answer"] == "pending_human_review"
    assert "never changes CRIS-SME risk scores" in console["deterministic_score_impact"]


def test_build_ce_review_console_applies_accept_and_override_decisions() -> None:
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
        ],
    }
    pack = build_ce_self_assessment_pack({"prioritized_risks": []}, mapping=mapping)

    console = build_ce_review_console(
        pack,
        review_decisions={
            "Q1": {"state": "accepted", "reviewer": "Lead assessor"},
            "Q2": {
                "state": "overridden",
                "final_status": "requires_policy_exception",
                "final_answer": "No",
                "reviewer_note": "Tenant has compensating control evidence.",
                "override_reason": "External evidence reviewed.",
            },
        },
    )

    decisions = {
        entry["question_id"]: entry["review_decision"]
        for entry in console["entries"]
    }
    assert decisions["Q1"]["state"] == "accepted"
    assert decisions["Q1"]["final_status"] == "supported_no_issue"
    assert decisions["Q1"]["final_answer"] == "Yes"
    assert decisions["Q2"]["state"] == "overridden"
    assert decisions["Q2"]["final_status"] == "requires_policy_exception"
    assert decisions["Q2"]["final_answer"] == "No"
    assert console["review_summary"]["review_state_counts"] == {
        "accepted": 1,
        "overridden": 1,
    }
    assert console["review_summary"]["override_or_evidence_request_count"] == 1


def test_ce_review_console_json_and_html_are_written(tmp_path) -> None:
    pack = build_ce_self_assessment_pack({"prioritized_risks": []})
    console = build_ce_review_console(pack)

    json_path = write_ce_review_console(
        console,
        tmp_path / "ce_review_console.json",
    )
    html = build_ce_review_console_html(console)
    html_path = write_ce_review_console_html(
        html,
        tmp_path / "ce_review_console.html",
    )

    written_console = json.loads(json_path.read_text(encoding="utf-8"))
    assert written_console["console_schema_version"] == "0.1.0"
    assert "Cyber Essentials Evidence Review Console" in html
    assert "Export Review Ledger" in html
    assert "Final answer" in html
    assert html_path.read_text(encoding="utf-8") == html
