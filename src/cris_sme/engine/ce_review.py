# Cyber Essentials human review workflow built over the answer pack.
from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REVIEW_DECISION_STATES = {
    "pending",
    "accepted",
    "overridden",
    "needs_evidence",
}


def build_ce_review_console(
    answer_pack: dict[str, Any],
    *,
    review_decisions: dict[str, dict[str, Any]] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a human-verification console model from a CE answer pack."""
    decisions = review_decisions or {}
    answers = [
        answer
        for answer in answer_pack.get("answers", [])
        if isinstance(answer, dict)
    ]
    entries = [
        _build_review_entry(answer, decisions.get(str(answer.get("question_id", "")), {}))
        for answer in answers
    ]
    evidence_counts = Counter(str(entry["evidence_class"]) for entry in entries)
    proposed_counts = Counter(str(entry["proposed_status"]) for entry in entries)
    review_counts = Counter(
        str(entry["review_decision"]["state"]) for entry in entries
    )
    override_counts = Counter(
        str(entry["review_decision"]["state"])
        for entry in entries
        if entry["review_decision"]["state"] in {"overridden", "needs_evidence"}
    )

    return {
        "console_schema_version": "0.1.0",
        "console_name": "CRIS-SME Cyber Essentials Evidence Review Console",
        "generated_at": generated_at or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source_pack_schema_version": answer_pack.get("pack_schema_version"),
        "question_set": answer_pack.get("question_set", {}),
        "question_count": len(entries),
        "review_summary": {
            "evidence_class_counts": dict(sorted(evidence_counts.items())),
            "proposed_status_counts": dict(sorted(proposed_counts.items())),
            "review_state_counts": dict(sorted(review_counts.items())),
            "override_or_evidence_request_count": sum(override_counts.values()),
            "human_review_required_count": sum(
                1 for entry in entries if entry.get("human_review_required")
            ),
            "cloud_supported_review_items": sum(
                evidence_counts.get(item, 0)
                for item in ("direct_cloud", "inferred_cloud")
            ),
        },
        "review_policy": {
            "allowed_review_states": sorted(REVIEW_DECISION_STATES),
            "default_state": "pending",
            "certification_boundary": answer_pack.get("certification_boundary"),
            "score_boundary": (
                "Reviewer decisions change the CE review ledger only. They do not "
                "change CRIS-SME deterministic findings, priorities, or scores."
            ),
        },
        "entries": entries,
        "guardrails": [
            "Every proposed answer remains pending until a responsible reviewer accepts, overrides, or requests more evidence.",
            "Overrides require a reviewer note and preserve the original CRIS-SME proposed status.",
            "Endpoint, policy, and manual evidence gaps are treated as review work, not as hidden compliance.",
            "The review ledger is a research and assurance artifact; it is not a Cyber Essentials certification submission.",
        ],
        "deterministic_score_impact": (
            "No impact. The CE review console is downstream of the deterministic "
            "answer pack and never changes CRIS-SME risk scores."
        ),
    }


def write_ce_review_console(
    console: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """Write a CE evidence review console JSON artifact."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(console, indent=2), encoding="utf-8")
    return path


def _build_review_entry(
    answer: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    proposed_status = str(answer.get("proposed_status", "manual_required"))
    decision_state = _review_state(decision)
    final_status = _final_status(proposed_status, decision_state, decision)

    return {
        "question_id": str(answer.get("question_id", "unknown")),
        "section": str(answer.get("section", "unknown")),
        "short_paraphrase": str(answer.get("short_paraphrase", "")),
        "evidence_class": str(answer.get("evidence_class", "manual_required")),
        "proposed_status": proposed_status,
        "supporting_control_ids": list(answer.get("supporting_control_ids", [])),
        "linked_findings": list(answer.get("linked_findings", [])),
        "evidence": list(answer.get("evidence", [])),
        "current_cris_sme_signals": list(answer.get("current_cris_sme_signals", [])),
        "planned_evidence_paths": list(answer.get("planned_evidence_paths", [])),
        "human_review_required": bool(answer.get("human_review_required", True)),
        "caveat": str(answer.get("caveat", "")),
        "review_decision": {
            "state": decision_state,
            "final_status": final_status,
            "reviewer": _clean_text(decision.get("reviewer")),
            "reviewed_at": _clean_text(decision.get("reviewed_at")),
            "reviewer_note": _clean_text(decision.get("reviewer_note")),
            "override_reason": _clean_text(decision.get("override_reason")),
            "additional_evidence_reference": _clean_text(
                decision.get("additional_evidence_reference")
            ),
        },
    }


def _review_state(decision: dict[str, Any]) -> str:
    state = str(decision.get("state", "pending")).strip().lower()
    if state in REVIEW_DECISION_STATES:
        return state
    return "pending"


def _final_status(
    proposed_status: str,
    decision_state: str,
    decision: dict[str, Any],
) -> str:
    if decision_state == "accepted":
        return proposed_status
    if decision_state == "needs_evidence":
        return "needs_evidence"
    if decision_state == "overridden":
        override = _clean_text(decision.get("final_status"))
        return override or "manual_override"
    return "pending_human_review"


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()
