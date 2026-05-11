# Cyber Essentials evaluation metrics derived from answer and review artifacts.
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


CLOUD_EVIDENCE_CLASSES = {"direct_cloud", "inferred_cloud"}
NON_CLOUD_EVIDENCE_CLASSES = {
    "endpoint_required",
    "policy_required",
    "manual_required",
    "not_observable",
}
REVIEWED_STATES = {"accepted", "overridden", "needs_evidence"}
AGREEMENT_EVALUABLE_STATES = {"accepted", "overridden"}
AI_DRAFT_REVIEWER_MARKERS = ("ai-assisted", "pilot reviewer draft")


def build_ce_evaluation_metrics(
    answer_pack: dict[str, Any],
    review_console: dict[str, Any],
) -> dict[str, Any]:
    """Build paper-ready metrics for CE pre-population evaluation."""
    answers = [
        answer
        for answer in answer_pack.get("answers", [])
        if isinstance(answer, dict)
    ]
    entries = [
        entry
        for entry in review_console.get("entries", [])
        if isinstance(entry, dict)
    ]
    answer_by_id = {str(answer.get("question_id")): answer for answer in answers}
    entry_by_id = {str(entry.get("question_id")): entry for entry in entries}
    merged = [
        _merge_answer_and_review(answer, entry_by_id.get(str(answer.get("question_id"))))
        for answer in answers
    ]
    if not merged and entries:
        merged = [_merge_answer_and_review(answer_by_id.get(str(entry.get("question_id"))), entry) for entry in entries]

    evidence_counts = Counter(str(item["evidence_class"]) for item in merged)
    proposed_counts = Counter(str(item["proposed_status"]) for item in merged)
    answer_counts = Counter(str(item["proposed_answer"]) for item in merged)
    final_answer_counts = Counter(str(item["final_answer"]) for item in merged)
    review_counts = Counter(str(item["review_state"]) for item in merged)
    section_counts = Counter(str(item["section"]) for item in merged)
    technical_items = [
        item for item in merged if item.get("research_scope") == "technical_control"
    ]
    technical_evidence_counts = Counter(
        str(item["evidence_class"]) for item in technical_items
    )
    reviewed_items = [
        item for item in merged if item.get("review_state") in REVIEWED_STATES
    ]
    draft_items = [
        item
        for item in merged
        if item.get("review_state") in AGREEMENT_EVALUABLE_STATES
        and item.get("is_ai_assisted_review")
    ]
    human_agreement_items = [
        item
        for item in merged
        if item.get("review_state") in AGREEMENT_EVALUABLE_STATES
        and not item.get("is_ai_assisted_review")
    ]
    draft_accepted_count = sum(
        1
        for item in draft_items
        if item.get("final_answer") == item.get("proposed_answer")
    )
    human_agreement_count = sum(
        1
        for item in human_agreement_items
        if item.get("final_answer") == item.get("proposed_answer")
    )
    cloud_supported_count = _count_evidence(merged, CLOUD_EVIDENCE_CLASSES)
    technical_cloud_supported_count = _count_evidence(
        technical_items,
        CLOUD_EVIDENCE_CLASSES,
    )

    return {
        "metrics_schema_version": "0.1.0",
        "metrics_name": "CRIS-SME Cyber Essentials Evaluation Metrics Pack",
        "source_pack_schema_version": answer_pack.get("pack_schema_version"),
        "source_console_schema_version": review_console.get("console_schema_version"),
        "question_set": answer_pack.get("question_set", review_console.get("question_set", {})),
        "question_count": len(merged),
        "technical_question_count": len(technical_items),
        "observability_metrics": {
            "cloud_supported_count": cloud_supported_count,
            "cloud_supported_rate": _rate(cloud_supported_count, len(merged)),
            "direct_cloud_count": evidence_counts.get("direct_cloud", 0),
            "inferred_cloud_count": evidence_counts.get("inferred_cloud", 0),
            "technical_cloud_supported_count": technical_cloud_supported_count,
            "technical_cloud_supported_rate": _rate(
                technical_cloud_supported_count,
                len(technical_items),
            ),
            "requires_non_cloud_evidence_count": _count_evidence(
                merged,
                NON_CLOUD_EVIDENCE_CLASSES,
            ),
        },
        "review_metrics": {
            "review_state_counts": dict(sorted(review_counts.items())),
            "reviewed_count": len(reviewed_items),
            "reviewed_rate": _rate(len(reviewed_items), len(merged)),
            "accepted_count": review_counts.get("accepted", 0),
            "override_count": review_counts.get("overridden", 0),
            "needs_evidence_count": review_counts.get("needs_evidence", 0),
            "pending_count": review_counts.get("pending", 0),
            "agreement_evaluable_count": len(human_agreement_items),
            "agreement_count": human_agreement_count,
            "agreement_rate": _rate(human_agreement_count, len(human_agreement_items)),
            "agreement_basis": (
                "Human agreement compares non-AI reviewer final_answer with CRIS-SME "
                "proposed_answer over accepted and overridden entries. AI-assisted "
                "pilot decisions are reported separately as draft acceptance."
            ),
            "draft_acceptance_evaluable_count": len(draft_items),
            "draft_accepted_count": draft_accepted_count,
            "draft_accepted_rate": _rate(draft_accepted_count, len(draft_items)),
            "draft_acceptance_basis": (
                "Draft acceptance is calculated only for AI-assisted pilot reviewer "
                "entries. It validates workflow plumbing and conservative review "
                "policy, but it is not independent human agreement."
            ),
        },
        "evidence_gap_taxonomy": _gap_taxonomy(merged),
        "status_counts": {
            "evidence_class_counts": dict(sorted(evidence_counts.items())),
            "proposed_status_counts": dict(sorted(proposed_counts.items())),
            "proposed_answer_counts": dict(sorted(answer_counts.items())),
            "final_answer_counts": dict(sorted(final_answer_counts.items())),
            "section_counts": dict(sorted(section_counts.items())),
            "technical_evidence_class_counts": dict(
                sorted(technical_evidence_counts.items())
            ),
        },
        "top_controls_causing_ce_answer_failures": _top_controls(merged),
        "paper_tables": {
            "observability_by_evidence_class": _table_from_counts(evidence_counts),
            "technical_observability_by_evidence_class": _table_from_counts(
                technical_evidence_counts
            ),
            "review_outcomes": _table_from_counts(review_counts),
            "proposed_answers": _table_from_counts(answer_counts),
            "final_answers": _table_from_counts(final_answer_counts),
            "section_coverage": _section_coverage(merged),
            "control_failure_contribution": _top_controls(merged, limit=12),
        },
        "evaluation_notes": [
            "Human agreement rate compares proposed_answer to non-AI reviewer final_answer and excludes pending entries, needs-evidence requests, and AI-assisted pilot decisions.",
            "AI-assisted pilot decisions are reported as draft acceptance, not reviewer agreement.",
            "Cloud observability counts direct_cloud and inferred_cloud evidence classes only.",
            "A proposed Yes means no mapped CRIS-SME cloud-control-plane risk was observed; it is not proof that every implementation path for the CE requirement is satisfied.",
            "Endpoint, policy, manual, and not-observable items are evidence gaps, not compliance failures by themselves.",
            "Metrics are derived from CRIS-SME artifacts and reviewer ledger states; they do not certify Cyber Essentials compliance.",
        ],
        "deterministic_score_impact": (
            "No impact. CE evaluation metrics are downstream measurements and never "
            "change CRIS-SME deterministic findings, priorities, or scores."
        ),
    }


def write_ce_evaluation_metrics(
    metrics: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """Write a CE evaluation metrics JSON artifact."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return path


def _merge_answer_and_review(
    answer: dict[str, Any] | None,
    entry: dict[str, Any] | None,
) -> dict[str, Any]:
    source = answer or entry or {}
    decision = entry.get("review_decision", {}) if isinstance(entry, dict) else {}
    if not isinstance(decision, dict):
        decision = {}
    return {
        "question_id": str(source.get("question_id", "unknown")),
        "section": str(source.get("section", "unknown")),
        "research_scope": str(source.get("research_scope", "unknown")),
        "evidence_class": str(source.get("evidence_class", "manual_required")),
        "proposed_status": str(source.get("proposed_status", "manual_required")),
        "proposed_answer": str(source.get("proposed_answer", "Cannot determine")),
        "final_status": str(decision.get("final_status", "pending_human_review")),
        "final_answer": str(decision.get("final_answer", "pending_human_review")),
        "review_state": str(decision.get("state", "pending")),
        "reviewer": str(decision.get("reviewer", "")),
        "is_ai_assisted_review": _is_ai_assisted_reviewer(
            str(decision.get("reviewer", ""))
        ),
        "supporting_control_ids": list(source.get("supporting_control_ids", [])),
        "linked_findings": list(source.get("linked_findings", [])),
        "planned_evidence_paths": list(source.get("planned_evidence_paths", [])),
    }


def _is_ai_assisted_reviewer(reviewer: str) -> bool:
    normalized = reviewer.strip().lower()
    if not normalized:
        return False
    return any(marker in normalized for marker in AI_DRAFT_REVIEWER_MARKERS)


def _count_evidence(items: list[dict[str, Any]], classes: set[str]) -> int:
    return sum(1 for item in items if str(item.get("evidence_class")) in classes)


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


def _gap_taxonomy(items: list[dict[str, Any]]) -> dict[str, Any]:
    gap_classes = {
        "endpoint_required": "Endpoint, MDM, EDR, patch, or local device evidence required.",
        "policy_required": "Policy, process, approval, or business-need evidence required.",
        "manual_required": "Applicant scoping, company context, or final attestation required.",
        "not_observable": "Required signal is outside current CRIS-SME observable evidence paths.",
    }
    taxonomy = {}
    for evidence_class, description in gap_classes.items():
        matching = [
            item for item in items if item.get("evidence_class") == evidence_class
        ]
        taxonomy[evidence_class] = {
            "count": len(matching),
            "rate": _rate(len(matching), len(items)),
            "description": description,
            "sample_question_ids": [
                str(item.get("question_id")) for item in matching[:8]
            ],
        }
    return taxonomy


def _top_controls(
    items: list[dict[str, Any]],
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    control_counts: Counter[str] = Counter()
    control_scores: dict[str, float] = {}
    control_titles: dict[str, set[str]] = {}
    for item in items:
        if item.get("proposed_status") != "supported_risk_found":
            continue
        linked_findings = item.get("linked_findings", [])
        if not isinstance(linked_findings, list):
            linked_findings = []
        for finding in linked_findings:
            if not isinstance(finding, dict):
                continue
            control_id = str(finding.get("control_id", "")).strip()
            if not control_id:
                continue
            control_counts[control_id] += 1
            score = finding.get("score")
            if isinstance(score, (int, float)):
                control_scores[control_id] = max(
                    control_scores.get(control_id, 0.0),
                    float(score),
                )
            title = str(finding.get("title", "")).strip()
            if title:
                control_titles.setdefault(control_id, set()).add(title)
    rows = []
    for control_id, count in control_counts.most_common(limit):
        rows.append(
            {
                "control_id": control_id,
                "affected_question_count": count,
                "max_linked_score": round(control_scores.get(control_id, 0.0), 2),
                "sample_finding_titles": sorted(control_titles.get(control_id, set()))[:3],
            }
        )
    return rows


def _table_from_counts(counts: Counter[str]) -> list[dict[str, Any]]:
    total = sum(counts.values())
    return [
        {
            "label": str(label),
            "count": count,
            "rate": _rate(count, total),
        }
        for label, count in sorted(counts.items())
    ]


def _section_coverage(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_section: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        by_section.setdefault(str(item.get("section", "unknown")), []).append(item)
    rows = []
    for section, section_items in sorted(by_section.items()):
        cloud_count = _count_evidence(section_items, CLOUD_EVIDENCE_CLASSES)
        rows.append(
            {
                "section": section,
                "question_count": len(section_items),
                "cloud_supported_count": cloud_count,
                "cloud_supported_rate": _rate(cloud_count, len(section_items)),
                "reviewed_count": sum(
                    1
                    for item in section_items
                    if item.get("review_state") in REVIEWED_STATES
                ),
            }
        )
    return rows
