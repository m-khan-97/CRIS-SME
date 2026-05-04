# Control drift attribution for separating evidence, policy, collector, and lifecycle movement.
from __future__ import annotations

from typing import Any

from cris_sme.models.platform import (
    ControlDriftAttributionItem,
    ControlDriftAttributionReport,
)


def build_control_drift_attribution(
    current_report: dict[str, Any],
    previous_report: dict[str, Any] | None,
) -> ControlDriftAttributionReport:
    """Attribute control score movement between two assessment reports."""
    if previous_report is None:
        return ControlDriftAttributionReport(
            comparable=False,
            current_generated_at=_string_or_none(current_report.get("generated_at")),
            previous_generated_at=None,
            overall_risk_delta=None,
            primary_attribution="baseline",
            explanation="No previous report is available, so control drift attribution is a baseline view.",
        )

    evidence_changed = _evidence_hash(current_report) != _evidence_hash(previous_report)
    policy_pack_changed = _policy_pack_version(current_report) != _policy_pack_version(previous_report)
    collector_mode_changed = current_report.get("collector_mode") != previous_report.get("collector_mode")
    lifecycle_changed = _status_counts(current_report) != _status_counts(previous_report)
    exception_state_changed = _exception_count(current_report) != _exception_count(previous_report)
    current_risks = _index_risks(current_report.get("prioritized_risks", []))
    previous_risks = _index_risks(previous_report.get("prioritized_risks", []))
    control_ids = sorted(set(current_risks) | set(previous_risks))

    items = [
        _build_item(
            control_id=control_id,
            current=current_risks.get(control_id),
            previous=previous_risks.get(control_id),
            evidence_changed=evidence_changed,
            policy_pack_changed=policy_pack_changed,
            collector_mode_changed=collector_mode_changed,
            lifecycle_changed=lifecycle_changed,
            exception_state_changed=exception_state_changed,
        )
        for control_id in control_ids
    ]
    items = [item for item in items if item.delta != 0.0 or item.contributing_factors]
    items.sort(key=lambda item: abs(item.delta), reverse=True)
    attribution_counts = _attribution_counts(items)
    primary_attribution = _primary_attribution(attribution_counts)

    return ControlDriftAttributionReport(
        comparable=True,
        current_generated_at=_string_or_none(current_report.get("generated_at")),
        previous_generated_at=_string_or_none(previous_report.get("generated_at")),
        overall_risk_delta=round(
            _safe_float(current_report.get("overall_risk_score"))
            - _safe_float(previous_report.get("overall_risk_score")),
            2,
        ),
        primary_attribution=primary_attribution,
        attribution_counts=attribution_counts,
        evidence_changed=evidence_changed,
        policy_pack_changed=policy_pack_changed,
        collector_mode_changed=collector_mode_changed,
        lifecycle_changed=lifecycle_changed,
        exception_state_changed=exception_state_changed,
        items=items[:50],
        explanation=_explanation(primary_attribution),
    )


def _build_item(
    *,
    control_id: str,
    current: dict[str, Any] | None,
    previous: dict[str, Any] | None,
    evidence_changed: bool,
    policy_pack_changed: bool,
    collector_mode_changed: bool,
    lifecycle_changed: bool,
    exception_state_changed: bool,
) -> ControlDriftAttributionItem:
    current_score = _safe_float(current.get("score")) if current else 0.0
    previous_score = _safe_float(previous.get("score")) if previous else 0.0
    delta = round(current_score - previous_score, 2)
    factors: list[str] = []
    if current is None:
        factors.append("finding_resolved_or_absent")
    if previous is None:
        factors.append("finding_new_or_newly_observed")
    if evidence_changed:
        factors.append("evidence_drift")
    if policy_pack_changed:
        factors.append("policy_pack_drift")
    if collector_mode_changed:
        factors.append("collector_mode_drift")
    if lifecycle_changed:
        factors.append("lifecycle_state_drift")
    if exception_state_changed:
        factors.append("exception_state_drift")

    representative = current or previous or {}
    return ControlDriftAttributionItem(
        control_id=control_id,
        title=_string_or_none(representative.get("title")),
        category=_string_or_none(representative.get("category")),
        current_score=round(current_score, 2),
        previous_score=round(previous_score, 2),
        delta=delta,
        direction=_direction(delta, current, previous),
        attribution=_attribute(factors),
        contributing_factors=factors or ["score_unchanged"],
        current_priority=_string_or_none(current.get("priority")) if current else None,
        previous_priority=_string_or_none(previous.get("priority")) if previous else None,
    )


def _attribute(factors: list[str]) -> str:
    if "policy_pack_drift" in factors and "evidence_drift" in factors:
        return "mixed_evidence_policy_drift"
    if "policy_pack_drift" in factors:
        return "policy_drift"
    if "evidence_drift" in factors:
        return "evidence_drift"
    if "collector_mode_drift" in factors:
        return "collector_coverage_drift"
    if "exception_state_drift" in factors or "lifecycle_state_drift" in factors:
        return "lifecycle_exception_drift"
    if "finding_new_or_newly_observed" in factors:
        return "new_finding"
    if "finding_resolved_or_absent" in factors:
        return "resolved_finding"
    return "unchanged"


def _direction(
    delta: float,
    current: dict[str, Any] | None,
    previous: dict[str, Any] | None,
) -> str:
    if previous is None and current is not None:
        return "new"
    if current is None and previous is not None:
        return "resolved"
    if delta > 0:
        return "worse"
    if delta < 0:
        return "improved"
    return "unchanged"


def _index_risks(risks: object) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    if not isinstance(risks, list):
        return indexed
    for risk in risks:
        if not isinstance(risk, dict):
            continue
        control_id = str(risk.get("control_id", "")).strip()
        if control_id:
            indexed[control_id] = risk
    return indexed


def _evidence_hash(report: dict[str, Any]) -> str:
    snapshot = report.get("evidence_snapshot")
    if not isinstance(snapshot, dict):
        return ""
    return "|".join(
        [
            str(snapshot.get("profile_sha256", "")),
            str(snapshot.get("finding_sha256", "")),
        ]
    )


def _policy_pack_version(report: dict[str, Any]) -> str:
    snapshot = report.get("evidence_snapshot")
    if isinstance(snapshot, dict) and snapshot.get("policy_pack_version"):
        return str(snapshot.get("policy_pack_version"))
    metadata = report.get("run_metadata")
    if isinstance(metadata, dict):
        policy_pack = metadata.get("policy_pack")
        if isinstance(policy_pack, dict):
            return str(policy_pack.get("policy_pack_version", ""))
    return ""


def _status_counts(report: dict[str, Any]) -> dict[str, int]:
    summary = report.get("finding_lifecycle_summary")
    if not isinstance(summary, dict):
        return {}
    counts = summary.get("status_counts", {})
    return {str(key): int(value) for key, value in counts.items()} if isinstance(counts, dict) else {}


def _exception_count(report: dict[str, Any]) -> int:
    summary = report.get("finding_lifecycle_summary")
    if not isinstance(summary, dict):
        return 0
    return int(summary.get("exception_applied_count", 0))


def _attribution_counts(items: list[ControlDriftAttributionItem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        counts[item.attribution] = counts.get(item.attribution, 0) + 1
    return counts


def _primary_attribution(counts: dict[str, int]) -> str:
    if not counts:
        return "unchanged"
    return sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[0][0]


def _explanation(primary_attribution: str) -> str:
    explanations = {
        "mixed_evidence_policy_drift": "Score movement is attributable to both evidence and policy-pack changes.",
        "evidence_drift": "Score movement is primarily evidence-driven.",
        "policy_drift": "Score movement is primarily policy-pack driven.",
        "collector_coverage_drift": "Score movement is primarily collector or coverage driven.",
        "lifecycle_exception_drift": "Score movement is primarily lifecycle or exception-state driven.",
        "new_finding": "Score movement is primarily due to newly observed findings.",
        "resolved_finding": "Score movement is primarily due to resolved or absent findings.",
        "unchanged": "No material control drift is visible between the compared reports.",
    }
    return explanations.get(primary_attribution, "Control drift attribution completed.")


def _safe_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
