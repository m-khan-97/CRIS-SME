# Import completed Cyber Essentials human review ledgers.
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .ce_review import REVIEW_DECISION_STATES


REVIEW_IMPORT_REQUIRED_COLUMNS = {
    "question_id",
    "review_state",
}


def load_ce_review_decisions(
    ledger_path: str | Path,
    *,
    answer_pack: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Load and validate CE review decisions from CSV or JSON."""
    path = Path(ledger_path)
    if not path.exists():
        raise FileNotFoundError(f"Review ledger not found: {path}")

    allowed_question_ids = _question_ids(answer_pack) if answer_pack else None
    if path.suffix.lower() == ".csv":
        rows = _load_csv_rows(path)
    elif path.suffix.lower() == ".json":
        rows = _load_json_rows(path)
    else:
        raise ValueError(
            f"Unsupported review ledger format '{path.suffix}'. Use .csv or .json."
        )

    decisions: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    for row_number, row in enumerate(rows, start=2):
        try:
            question_id, decision = _normalize_review_row(
                row,
                allowed_question_ids=allowed_question_ids,
            )
        except ValueError as exc:
            errors.append(f"row {row_number}: {exc}")
            continue
        if decision["state"] == "pending":
            continue
        decisions[question_id] = decision

    if errors:
        raise ValueError("Invalid CE review ledger:\n" + "\n".join(errors))
    return decisions


def _load_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = set(reader.fieldnames or [])
        missing = REVIEW_IMPORT_REQUIRED_COLUMNS - headers
        if missing:
            raise ValueError(
                "Review ledger is missing required column(s): "
                + ", ".join(sorted(missing))
            )
        return [dict(row) for row in reader]


def _load_json_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    if not isinstance(payload, dict):
        raise ValueError("JSON review ledger must be an object or a list of rows.")

    decisions = payload.get("review_decisions")
    if isinstance(decisions, list):
        return [row for row in decisions if isinstance(row, dict)]
    if isinstance(decisions, dict):
        rows = []
        for question_id, decision in decisions.items():
            if isinstance(decision, dict):
                row = {"question_id": question_id}
                row.update(decision)
                rows.append(row)
        return rows

    entries = payload.get("entries")
    if isinstance(entries, list):
        rows = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            decision = entry.get("review_decision", {})
            if not isinstance(decision, dict):
                decision = {}
            row = {"question_id": entry.get("question_id")}
            row.update(decision)
            rows.append(row)
        return rows

    raise ValueError(
        "JSON review ledger must contain review_decisions, entries, or a list of rows."
    )


def _normalize_review_row(
    row: dict[str, Any],
    *,
    allowed_question_ids: set[str] | None,
) -> tuple[str, dict[str, Any]]:
    question_id = _clean(row.get("question_id"))
    if not question_id:
        raise ValueError("missing question_id")
    if allowed_question_ids is not None and question_id not in allowed_question_ids:
        raise ValueError(f"unknown question_id '{question_id}'")

    state = _clean(row.get("review_state") or row.get("state")).lower()
    if state not in REVIEW_DECISION_STATES:
        raise ValueError(
            f"invalid review_state '{state or '<blank>'}' for {question_id}"
        )

    final_answer = _clean(row.get("final_answer"))
    final_status = _clean(row.get("final_status"))
    reviewer = _clean(row.get("reviewer"))
    reviewer_note = _clean(row.get("reviewer_note"))
    override_reason = _clean(row.get("override_reason"))
    evidence_reference = _clean(
        row.get("additional_evidence_reference")
        or row.get("evidence_reference")
    )

    if state == "overridden":
        if final_answer not in {"Yes", "No", "Cannot determine"}:
            raise ValueError(
                f"overridden row for {question_id} requires final_answer "
                "Yes, No, or Cannot determine"
            )
        if not override_reason:
            raise ValueError(
                f"overridden row for {question_id} requires override_reason"
            )

    if state in {"accepted", "overridden", "needs_evidence"} and not reviewer:
        raise ValueError(f"{state} row for {question_id} requires reviewer")

    decision = {
        "state": state,
        "final_status": final_status,
        "final_answer": final_answer,
        "reviewer": reviewer,
        "reviewed_at": _clean(row.get("reviewed_at")),
        "reviewer_note": reviewer_note,
        "override_reason": override_reason,
        "additional_evidence_reference": evidence_reference,
    }
    return question_id, decision


def _question_ids(answer_pack: dict[str, Any] | None) -> set[str]:
    if not isinstance(answer_pack, dict):
        return set()
    answers = answer_pack.get("answers", [])
    if not isinstance(answers, list):
        return set()
    return {
        str(answer.get("question_id"))
        for answer in answers
        if isinstance(answer, dict) and str(answer.get("question_id", "")).strip()
    }


def _clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()
