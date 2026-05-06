# Tests for the paraphrased Cyber Essentials question mapping dataset.
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


MAPPING_PATH = Path("data/ce_question_mapping.json")
VALID_EVIDENCE_CLASSES = {
    "direct_cloud",
    "inferred_cloud",
    "endpoint_required",
    "policy_required",
    "manual_required",
    "not_observable",
}


def test_ce_question_mapping_loads_and_uses_current_danzell_metadata() -> None:
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))

    question_set = mapping["question_set"]
    assert question_set["name"] == "Danzell"
    assert question_set["version"] == "16.2"
    assert question_set["requirements_version"] == "3.3"
    assert "Verbatim question text is intentionally not reproduced" in question_set["source_note"]


def test_ce_question_mapping_entries_have_valid_evidence_classes() -> None:
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    questions = mapping["questions"]

    assert len(questions) == 106
    question_ids = [question["question_id"] for question in questions]
    assert len(question_ids) == len(set(question_ids))

    for question in questions:
        assert question["evidence_class"] in VALID_EVIDENCE_CLASSES
        assert question["short_paraphrase"]
        assert question["human_review_required"] is True
        assert isinstance(question["supporting_control_ids"], list)
        assert isinstance(question["current_cris_sme_signals"], list)
        assert isinstance(question["planned_evidence_paths"], list)


def test_ce_question_mapping_counts_first_pass_coverage() -> None:
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    questions = mapping["questions"]
    all_counts = Counter(question["evidence_class"] for question in questions)
    technical_counts = Counter(
        question["evidence_class"]
        for question in questions
        if question["research_scope"] == "technical_control"
    )

    assert all_counts == {
        "direct_cloud": 5,
        "endpoint_required": 24,
        "inferred_cloud": 23,
        "manual_required": 35,
        "policy_required": 19,
    }
    assert technical_counts == {
        "direct_cloud": 5,
        "endpoint_required": 21,
        "inferred_cloud": 17,
        "manual_required": 1,
        "policy_required": 18,
    }

