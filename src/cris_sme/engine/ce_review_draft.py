# AI-assisted pilot reviewer decisions for Cyber Essentials answer packs.
from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


CLOUD_EVIDENCE_CLASSES = {"direct_cloud", "inferred_cloud"}
DEFAULT_DRAFT_REVIEWER = "AI-assisted internal reviewer draft"


def build_ce_review_decision_draft(
    answer_pack: dict[str, Any],
    *,
    reviewer: str = DEFAULT_DRAFT_REVIEWER,
    reviewed_at: str | None = None,
) -> dict[str, Any]:
    """Build conservative draft review decisions for cloud-supported CE entries.

    This is a pilot-research aid, not an independent human expert review. It marks
    directly observed cloud answers and linked-risk inferred "No" answers as
    accepted, while treating inferred "Yes" answers as requiring more evidence.
    """
    timestamp = reviewed_at or datetime.now(UTC).isoformat().replace("+00:00", "Z")
    answers = [
        answer
        for answer in answer_pack.get("answers", [])
        if isinstance(answer, dict)
    ]
    decisions: dict[str, dict[str, Any]] = {}
    for answer in answers:
        question_id = str(answer.get("question_id", "")).strip()
        if not question_id:
            continue
        decision = _draft_decision_for_answer(
            answer,
            reviewer=reviewer,
            reviewed_at=timestamp,
        )
        if decision:
            decisions[question_id] = decision

    state_counts = Counter(str(item.get("state", "pending")) for item in decisions.values())
    answer_counts = Counter(
        str(item.get("final_answer", "Cannot determine"))
        for item in decisions.values()
    )
    evidence_counts = Counter(
        str(answer.get("evidence_class", "manual_required"))
        for answer in answers
        if str(answer.get("question_id", "")) in decisions
    )

    return {
        "review_decision_draft_schema_version": "0.1.0",
        "draft_name": "CRIS-SME Cyber Essentials AI-Assisted Pilot Review Ledger",
        "generated_at": timestamp,
        "reviewer": reviewer,
        "source_pack_schema_version": answer_pack.get("pack_schema_version"),
        "question_set": answer_pack.get("question_set", {}),
        "review_scope": {
            "included_evidence_classes": sorted(CLOUD_EVIDENCE_CLASSES),
            "excluded_entries": (
                "Endpoint, policy, manual, and not-observable entries remain pending "
                "because this draft only reviews cloud-supported pre-population."
            ),
        },
        "research_boundary": (
            "This artifact is an AI-assisted internal draft for pilot analysis. It is "
            "not an independent human expert review, not assessor advice, and not a "
            "Cyber Essentials certification decision."
        ),
        "decision_policy": {
            "direct_cloud": (
                "Accept direct cloud-control-plane proposed answers as a reviewer "
                "draft, subject to later human verification."
            ),
            "inferred_cloud_no": (
                "Accept inferred cloud 'No' answers when mapped CRIS-SME findings are "
                "present, because the draft is conservative about answer-impact risks."
            ),
            "inferred_cloud_yes": (
                "Request more evidence for inferred cloud 'Yes' answers because the "
                "absence of a finding is not enough to independently validate the CE answer."
            ),
        },
        "summary": {
            "draft_decision_count": len(decisions),
            "state_counts": dict(sorted(state_counts.items())),
            "final_answer_counts": dict(sorted(answer_counts.items())),
            "evidence_class_counts": dict(sorted(evidence_counts.items())),
        },
        "review_decisions": decisions,
    }


def write_ce_review_decision_draft(
    draft: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """Write AI-assisted CE review draft decisions as JSON."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(draft, indent=2), encoding="utf-8")
    return path


def _draft_decision_for_answer(
    answer: dict[str, Any],
    *,
    reviewer: str,
    reviewed_at: str,
) -> dict[str, Any] | None:
    evidence_class = str(answer.get("evidence_class", "manual_required"))
    if evidence_class not in CLOUD_EVIDENCE_CLASSES:
        return None

    proposed_answer = str(answer.get("proposed_answer", "Cannot determine"))
    proposed_status = str(answer.get("proposed_status", "manual_required"))
    linked_findings = _linked_findings(answer)
    control_ids = _control_ids(answer)
    evidence_reference = _evidence_reference(control_ids, linked_findings)

    if evidence_class == "direct_cloud" and proposed_answer in {"Yes", "No"}:
        return {
            "state": "accepted",
            "final_status": proposed_status,
            "final_answer": proposed_answer,
            "reviewer": reviewer,
            "reviewed_at": reviewed_at,
            "reviewer_note": (
                "Accepted as an AI-assisted pilot decision because CRIS-SME mapped "
                "this entry to direct cloud-control-plane evidence. A human assessor "
                "must still verify tenant scope and final CE wording."
            ),
            "override_reason": "",
            "additional_evidence_reference": evidence_reference,
        }

    if evidence_class == "inferred_cloud" and proposed_answer == "No" and linked_findings:
        return {
            "state": "accepted",
            "final_status": proposed_status,
            "final_answer": "No",
            "reviewer": reviewer,
            "reviewed_at": reviewed_at,
            "reviewer_note": (
                "Accepted as a conservative AI-assisted pilot decision because mapped "
                "CRIS-SME finding evidence indicates an answer-impact risk. This is "
                "not a certification failure verdict and should be verified by a human reviewer."
            ),
            "override_reason": "",
            "additional_evidence_reference": evidence_reference,
        }

    return {
        "state": "needs_evidence",
        "final_status": "needs_evidence",
        "final_answer": "Cannot determine",
        "reviewer": reviewer,
        "reviewed_at": reviewed_at,
        "reviewer_note": (
            "Not accepted in the AI-assisted pilot ledger because this is an inferred "
            "cloud 'Yes' or otherwise insufficiently supported answer. Human review "
            "should confirm scope, external evidence, and whether absence of a CRIS-SME "
            "finding is enough for this CE entry."
        ),
        "override_reason": "Inferred evidence requires human corroboration before accepting a Yes answer.",
        "additional_evidence_reference": evidence_reference,
    }


def _linked_findings(answer: dict[str, Any]) -> list[dict[str, Any]]:
    findings = answer.get("linked_findings", [])
    if not isinstance(findings, list):
        return []
    return [finding for finding in findings if isinstance(finding, dict)]


def _control_ids(answer: dict[str, Any]) -> list[str]:
    values = answer.get("supporting_control_ids", [])
    if not isinstance(values, list):
        return []
    return [str(value) for value in values if str(value).strip()]


def _evidence_reference(
    control_ids: list[str],
    linked_findings: list[dict[str, Any]],
) -> str:
    parts = []
    if control_ids:
        parts.append("controls: " + ", ".join(control_ids))
    finding_ids = [
        str(finding.get("finding_id") or finding.get("id") or finding.get("control_id"))
        for finding in linked_findings
        if str(finding.get("finding_id") or finding.get("id") or finding.get("control_id") or "").strip()
    ]
    if finding_ids:
        parts.append("linked_findings: " + ", ".join(finding_ids))
    if not parts:
        return "No CRIS-SME linked finding reference; human corroboration required."
    return "; ".join(parts)
