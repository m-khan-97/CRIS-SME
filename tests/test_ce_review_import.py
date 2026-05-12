# Tests for completed Cyber Essentials review-ledger import.
from __future__ import annotations

import json

import pytest

from cris_sme.engine.ce_evaluation import build_ce_evaluation_metrics
from cris_sme.engine.ce_questionnaire import build_ce_self_assessment_pack
from cris_sme.engine.ce_review import build_ce_review_console
from cris_sme.engine.ce_review_import import load_ce_review_decisions
from cris_sme.engine.ce_review_signature import (
    build_signed_ce_review_ledger,
    canonical_sha256,
    verify_ce_review_ledger,
)


def test_load_ce_review_decisions_from_csv_feeds_human_agreement(tmp_path) -> None:
    pack = build_ce_self_assessment_pack(_report(), mapping=_mapping())
    ledger = tmp_path / "review-ledger.csv"
    ledger.write_text(
        "\n".join(
            [
                "question_id,review_state,final_answer,reviewer,reviewed_at,reviewer_note,evidence_reference,override_reason",
                "Q1,accepted,,Human Reviewer,2026-05-12T10:00:00Z,Evidence reviewed,NSG export,",
                "Q2,overridden,No,Human Reviewer,2026-05-12T10:05:00Z,External policy evidence reviewed,Policy doc,Reviewer disagreed with proposed answer",
                "Q3,needs_evidence,,Human Reviewer,2026-05-12T10:10:00Z,Endpoint data required,MDM export needed,",
            ]
        ),
        encoding="utf-8",
    )

    decisions = load_ce_review_decisions(ledger, answer_pack=pack)
    console = build_ce_review_console(pack, review_decisions=decisions)
    metrics = build_ce_evaluation_metrics(pack, console)

    assert decisions["Q1"]["state"] == "accepted"
    assert decisions["Q2"]["state"] == "overridden"
    assert decisions["Q2"]["additional_evidence_reference"] == "Policy doc"
    assert decisions["Q3"]["state"] == "needs_evidence"
    assert metrics["review_metrics"]["reviewed_count"] == 3
    assert metrics["review_metrics"]["agreement_evaluable_count"] == 2
    assert metrics["review_metrics"]["agreement_count"] == 1
    assert metrics["review_metrics"]["agreement_rate"] == 50.0
    assert metrics["review_metrics"]["draft_acceptance_evaluable_count"] == 0


def test_load_ce_review_decisions_from_console_json(tmp_path) -> None:
    pack = build_ce_self_assessment_pack(_report(), mapping=_mapping())
    console = build_ce_review_console(
        pack,
        review_decisions={
            "Q1": {
                "state": "accepted",
                "reviewer": "Human Reviewer",
                "reviewed_at": "2026-05-12T10:00:00Z",
            }
        },
    )
    path = tmp_path / "console.json"
    path.write_text(json.dumps(console), encoding="utf-8")

    decisions = load_ce_review_decisions(path, answer_pack=pack)

    assert decisions == {
        "Q1": {
            "state": "accepted",
            "final_status": "supported_risk_found",
            "final_answer": "No",
            "reviewer": "Human Reviewer",
            "reviewed_at": "2026-05-12T10:00:00Z",
            "reviewer_note": "",
            "override_reason": "",
            "additional_evidence_reference": "",
        }
    }


def test_load_ce_review_decisions_rejects_invalid_rows(tmp_path) -> None:
    pack = build_ce_self_assessment_pack(_report(), mapping=_mapping())
    ledger = tmp_path / "bad-ledger.csv"
    ledger.write_text(
        "\n".join(
            [
                "question_id,review_state,final_answer,reviewer,override_reason",
                "Q404,accepted,,Human Reviewer,",
                "Q1,overridden,Maybe,Human Reviewer,",
                "Q2,accepted,,,",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as excinfo:
        load_ce_review_decisions(ledger, answer_pack=pack)

    message = str(excinfo.value)
    assert "unknown question_id 'Q404'" in message
    assert "overridden row for Q1 requires final_answer" in message
    assert "accepted row for Q2 requires reviewer" in message


def test_signed_ce_review_ledger_hashes_are_stable_and_verifiable() -> None:
    pack = build_ce_self_assessment_pack(_report(), mapping=_mapping())
    decisions = {
        "Q1": {
            "state": "accepted",
            "final_answer": "No",
            "final_status": "supported_risk_found",
            "reviewer": "Human Reviewer",
            "reviewed_at": "2026-05-12T10:00:00Z",
        },
        "Q2": {
            "state": "needs_evidence",
            "final_answer": "Cannot determine",
            "final_status": "needs_evidence",
            "reviewer": "Human Reviewer",
            "reviewed_at": "2026-05-12T10:05:00Z",
            "reviewer_note": "Graph evidence required.",
        },
    }

    first = build_signed_ce_review_ledger(
        answer_pack=pack,
        review_decisions=decisions,
        reviewer={"name": "Human Reviewer", "role": "CE reviewer"},
        generated_at="2026-05-12T11:00:00Z",
        signing_key="secret",
        key_id="test-key",
    )
    second = build_signed_ce_review_ledger(
        answer_pack=pack,
        review_decisions=dict(reversed(list(decisions.items()))),
        reviewer={"role": "CE reviewer", "name": "Human Reviewer"},
        generated_at="2026-05-12T11:00:00Z",
        signing_key="secret",
        key_id="test-key",
    )

    assert first["integrity"]["canonical_ledger_sha256"] == second["integrity"]["canonical_ledger_sha256"]
    assert first["integrity"]["canonical_decisions_sha256"] == second["integrity"]["canonical_decisions_sha256"]
    assert first["integrity"]["source_answer_pack_sha256"] == canonical_sha256(pack)
    assert first["signature"]["algorithm"] == "hmac-sha256"

    result = verify_ce_review_ledger(first, answer_pack=pack, signing_key="secret")

    assert result["verified"] is True
    assert result["ledger_hash_verified"] is True
    assert result["decisions_hash_verified"] is True
    assert result["answer_pack_hash_verified"] is True
    assert result["signature_verified"] is True


def test_signed_ce_review_ledger_detects_tampering() -> None:
    pack = build_ce_self_assessment_pack(_report(), mapping=_mapping())
    ledger = build_signed_ce_review_ledger(
        answer_pack=pack,
        review_decisions={
            "Q1": {
                "state": "accepted",
                "final_answer": "No",
                "final_status": "supported_risk_found",
                "reviewer": "Human Reviewer",
            }
        },
        generated_at="2026-05-12T11:00:00Z",
        signing_key="secret",
        key_id="test-key",
    )
    ledger["review_decisions"][0]["final_answer"] = "Yes"

    result = verify_ce_review_ledger(ledger, answer_pack=pack, signing_key="secret")

    assert result["verified"] is False
    assert result["ledger_hash_verified"] is False
    assert result["decisions_hash_verified"] is False
    assert result["signature_verified"] is False
    assert any("hash mismatch" in error.lower() for error in result["errors"])


def _mapping() -> dict:
    return {
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
                "planned_evidence_paths": ["NSG rules"],
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
                "planned_evidence_paths": ["Graph evidence"],
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


def _report() -> dict:
    return {
        "prioritized_risks": [
            {
                "finding_id": "fdg_net_001",
                "control_id": "NET-001",
                "title": "Administrative exposure",
                "priority": "High",
                "score": 70.0,
            }
        ]
    }
