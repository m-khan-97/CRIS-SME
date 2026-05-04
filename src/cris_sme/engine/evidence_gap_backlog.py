# Evidence gap backlog generation for CRIS-SME product and collector improvement.
from __future__ import annotations

import hashlib
from typing import Any

from cris_sme.models.platform import EvidenceGapBacklog, EvidenceGapBacklogItem


def build_evidence_gap_backlog(report: dict[str, Any]) -> EvidenceGapBacklog:
    """Build actionable backlog items from evidence quality and provider contracts."""
    items = [
        *_finding_evidence_gap_items(report),
        *_provider_activation_gap_items(report),
    ]
    items = sorted(
        items,
        key=lambda item: (_priority_rank(item.priority), item.provider, item.control_id),
    )
    return EvidenceGapBacklog(
        item_count=len(items),
        high_priority_count=sum(1 for item in items if item.priority == "high"),
        provider_counts=_count_by(items, "provider"),
        domain_counts=_count_by(items, "domain"),
        items=items,
    )


def _finding_evidence_gap_items(report: dict[str, Any]) -> list[EvidenceGapBacklogItem]:
    prioritized = report.get("prioritized_risks", [])
    if not isinstance(prioritized, list):
        return []

    items: list[EvidenceGapBacklogItem] = []
    for risk in prioritized:
        if not isinstance(risk, dict):
            continue
        quality = risk.get("evidence_quality", {})
        if not isinstance(quality, dict):
            continue
        sufficiency = str(quality.get("sufficiency", "")).lower()
        missing = [
            str(item)
            for item in quality.get("missing_requirements", [])
            if str(item).strip()
        ]
        if sufficiency not in {"partial", "unavailable", "inferred", "stale"} and not missing:
            continue
        control_id = str(risk.get("control_id", "unknown"))
        provider = str(risk.get("provider", "unknown"))
        domain = str(risk.get("category", "unknown"))
        gap_text = ", ".join(missing) if missing else f"{sufficiency} evidence"
        items.append(
            EvidenceGapBacklogItem(
                gap_id=_gap_id("finding", provider, control_id, str(risk.get("finding_id"))),
                gap_type="finding_evidence_gap",
                provider=provider,
                domain=domain,
                control_id=control_id,
                title=str(risk.get("title", control_id)),
                priority=_finding_gap_priority(risk, sufficiency),
                evidence_gap=gap_text,
                recommended_action=(
                    "Add or enrich collector evidence for the missing requirement and "
                    "keep the limitation visible until direct evidence is available."
                ),
                linked_finding_id=str(risk.get("finding_id")),
                support_status=str(quality.get("provider_support", "unknown")),
                assurance_impact=_assurance_impact(sufficiency),
            )
        )
    return items


def _provider_activation_gap_items(report: dict[str, Any]) -> list[EvidenceGapBacklogItem]:
    contracts = _contracts(report)
    items: list[EvidenceGapBacklogItem] = []
    for contract in contracts:
        support_status = str(contract.get("support_status", "")).lower()
        if support_status != "planned":
            continue
        provider = str(contract.get("provider", "unknown"))
        control_id = str(contract.get("control_id", "unknown"))
        domain = str(contract.get("domain", "unknown"))
        requirements = [
            str(item)
            for item in contract.get("evidence_requirements", [])
            if str(item).strip()
        ]
        items.append(
            EvidenceGapBacklogItem(
                gap_id=_gap_id("provider", provider, control_id, support_status),
                gap_type="provider_activation_gap",
                provider=provider,
                domain=domain,
                control_id=control_id,
                title=f"Activate {provider.upper()} evidence path for {control_id}",
                priority="medium",
                evidence_gap=", ".join(requirements) if requirements else "collector evidence",
                recommended_action=str(contract.get("activation_gate", "")).strip()
                or "Implement collector evidence, adapter routing, tests, and limitations.",
                linked_finding_id=None,
                support_status=support_status,
                assurance_impact="future_provider_assurance",
            )
        )
    return items


def _contracts(report: dict[str, Any]) -> list[dict[str, Any]]:
    catalog = report.get("provider_evidence_contracts", {})
    if not isinstance(catalog, dict):
        return []
    contracts = catalog.get("contracts", [])
    return [item for item in contracts if isinstance(item, dict)] if isinstance(contracts, list) else []


def _finding_gap_priority(risk: dict[str, Any], sufficiency: str) -> str:
    score = _safe_float(risk.get("score"))
    if sufficiency in {"unavailable", "stale"} and score >= 50:
        return "high"
    if score >= 65:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def _assurance_impact(sufficiency: str) -> str:
    if sufficiency in {"unavailable", "stale"}:
        return "high"
    if sufficiency in {"partial", "inferred"}:
        return "medium"
    return "low"


def _count_by(items: list[EvidenceGapBacklogItem], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(getattr(item, field))
        counts[value] = counts.get(value, 0) + 1
    return counts


def _priority_rank(priority: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(priority, 3)


def _gap_id(*parts: str) -> str:
    raw = "|".join(parts)
    return f"egap_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:14]}"


def _safe_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
