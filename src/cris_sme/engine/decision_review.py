# Decision review queue generation for governance-ready CRIS-SME outputs.
from __future__ import annotations

import hashlib
from typing import Any

from cris_sme.models.platform import DecisionReviewQueue, DecisionReviewQueueItem


def build_decision_review_queue(report: dict[str, Any]) -> DecisionReviewQueue:
    """Build explicit stakeholder decision items from findings and evidence gaps."""
    items = [
        *_risk_review_items(report),
        *_evidence_review_items(report),
    ]
    deduped = _dedupe(items)
    deduped.sort(key=lambda item: (_priority_rank(item.priority), item.control_id, item.review_id))
    return DecisionReviewQueue(
        item_count=len(deduped),
        decision_type_counts=_count_by(deduped, "decision_type"),
        priority_counts=_count_by(deduped, "priority"),
        items=deduped[:75],
    )


def _risk_review_items(report: dict[str, Any]) -> list[DecisionReviewQueueItem]:
    risks = report.get("prioritized_risks", [])
    if not isinstance(risks, list):
        return []
    items: list[DecisionReviewQueueItem] = []
    for risk in risks:
        if not isinstance(risk, dict):
            continue
        score = _safe_float(risk.get("score"))
        priority = str(risk.get("priority", "Monitor"))
        lifecycle = risk.get("lifecycle", {})
        if not isinstance(lifecycle, dict):
            lifecycle = {}
        status = str(lifecycle.get("status", "open"))
        evidence_quality = risk.get("evidence_quality", {})
        if not isinstance(evidence_quality, dict):
            evidence_quality = {}
        sufficiency = str(evidence_quality.get("sufficiency", "unknown"))
        decision_type, recommended_decision, rationale = _risk_decision(
            score=score,
            priority=priority,
            lifecycle_status=status,
            sufficiency=sufficiency,
        )
        if decision_type == "monitor" and score < 25:
            continue
        items.append(
            DecisionReviewQueueItem(
                review_id=_review_id("risk", str(risk.get("finding_id")), decision_type),
                decision_type=decision_type,
                control_id=str(risk.get("control_id", "unknown")),
                finding_id=str(risk.get("finding_id")) if risk.get("finding_id") else None,
                title=str(risk.get("title", "Untitled finding")),
                provider=str(risk.get("provider", "azure")),
                priority=_queue_priority(priority, score),
                recommended_decision=recommended_decision,
                rationale=rationale,
                evidence_sufficiency=sufficiency,
                lifecycle_status=status,
                owner_hint=_owner_hint(str(risk.get("category", ""))),
            )
        )
    return items


def _evidence_review_items(report: dict[str, Any]) -> list[DecisionReviewQueueItem]:
    backlog = report.get("evidence_gap_backlog", {})
    if not isinstance(backlog, dict):
        return []
    gaps = backlog.get("items", [])
    if not isinstance(gaps, list):
        return []
    items: list[DecisionReviewQueueItem] = []
    for gap in gaps:
        if not isinstance(gap, dict):
            continue
        priority = str(gap.get("priority", "medium"))
        if priority == "low":
            continue
        items.append(
            DecisionReviewQueueItem(
                review_id=_review_id("evidence", str(gap.get("gap_id")), priority),
                decision_type="evidence_investigation",
                control_id=str(gap.get("control_id", "unknown")),
                finding_id=str(gap.get("linked_finding_id")) if gap.get("linked_finding_id") else None,
                title=str(gap.get("title", "Evidence gap")),
                provider=str(gap.get("provider", "unknown")),
                priority=priority,
                recommended_decision="Investigate or enrich evidence path",
                rationale=str(gap.get("recommended_action", "Evidence gap requires review.")),
                evidence_sufficiency=str(gap.get("assurance_impact", "unknown")),
                lifecycle_status=None,
                owner_hint="platform",
            )
        )
    return items


def _risk_decision(
    *,
    score: float,
    priority: str,
    lifecycle_status: str,
    sufficiency: str,
) -> tuple[str, str, str]:
    if lifecycle_status in {"accepted_risk", "suppressed", "expired_exception"}:
        return (
            "exception_review",
            "Review exception state",
            "Finding has an exception-related lifecycle status and needs governance review.",
        )
    if sufficiency in {"partial", "inferred", "unavailable", "stale"} and score >= 50:
        return (
            "evidence_review",
            "Confirm evidence before final risk decision",
            "Risk is material but evidence sufficiency has limitations.",
        )
    if priority in {"Immediate", "High"} or score >= 50:
        return (
            "remediation_decision",
            "Approve remediation plan",
            "Risk priority is high enough to require an explicit remediation decision.",
        )
    return (
        "monitor",
        "Monitor in next assessment",
        "Risk is present but below immediate governance-decision threshold.",
    )


def _queue_priority(priority: str, score: float) -> str:
    if priority == "Immediate" or score >= 75:
        return "high"
    if priority == "High" or score >= 50:
        return "high"
    if priority == "Planned" or score >= 25:
        return "medium"
    return "low"


def _owner_hint(category: str) -> str:
    normalized = category.lower()
    if "iam" in normalized:
        return "identity"
    if "network" in normalized:
        return "network"
    if "data" in normalized:
        return "data"
    if "monitor" in normalized:
        return "security-operations"
    if "compute" in normalized:
        return "platform"
    return "governance"


def _dedupe(items: list[DecisionReviewQueueItem]) -> list[DecisionReviewQueueItem]:
    seen: set[str] = set()
    deduped: list[DecisionReviewQueueItem] = []
    for item in items:
        key = f"{item.decision_type}|{item.control_id}|{item.finding_id or item.title}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _count_by(items: list[DecisionReviewQueueItem], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(getattr(item, field))
        counts[value] = counts.get(value, 0) + 1
    return counts


def _priority_rank(priority: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(priority, 3)


def _review_id(*parts: str) -> str:
    raw = "|".join(parts)
    return f"drv_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:14]}"


def _safe_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
