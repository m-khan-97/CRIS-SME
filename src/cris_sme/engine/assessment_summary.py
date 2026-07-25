# Canonical compact assessment summary for API and dashboard consumers.
from __future__ import annotations

from collections import Counter
from typing import Any

from pydantic import BaseModel, Field


class AssessmentSummary(BaseModel):
    """Precomputed summary of the final assessment report."""

    summary_schema_version: str = "1.0.0"
    generated_at: str | None = None
    collector_mode: str | None = None
    overall_risk_score: float = 0.0
    risk_band: str = "unknown"
    finding_summary: dict[str, Any] = Field(default_factory=dict)
    compliance_summary: dict[str, Any] = Field(default_factory=dict)
    resource_summary: dict[str, Any] = Field(default_factory=dict)
    evidence_summary: dict[str, Any] = Field(default_factory=dict)
    lifecycle_summary: dict[str, Any] = Field(default_factory=dict)
    drift_summary: dict[str, Any] = Field(default_factory=dict)
    claim_summary: dict[str, Any] = Field(default_factory=dict)
    action_summary: dict[str, Any] = Field(default_factory=dict)
    provider_summary: dict[str, Any] = Field(default_factory=dict)
    assurance_summary: dict[str, Any] = Field(default_factory=dict)


def build_assessment_summary(report: dict[str, Any]) -> AssessmentSummary:
    """Build a stable compact summary from a near-final assessment report."""
    prioritized = _list_of_dicts(report.get("prioritized_risks"))
    overall_score = _float(report.get("overall_risk_score"), 0.0)
    return AssessmentSummary(
        generated_at=_optional_str(report.get("generated_at")),
        collector_mode=_optional_str(report.get("collector_mode")),
        overall_risk_score=overall_score,
        risk_band=_risk_band(overall_score),
        finding_summary=_finding_summary(prioritized, report),
        compliance_summary=_compliance_summary(report),
        resource_summary=_resource_summary(report),
        evidence_summary=_evidence_summary(prioritized, report),
        lifecycle_summary=_lifecycle_summary(prioritized, report),
        drift_summary=_drift_summary(report),
        claim_summary=_claim_summary(report),
        action_summary=_action_summary(report),
        provider_summary=_provider_summary(report),
        assurance_summary=_assurance_summary(report),
    )


def _finding_summary(
    prioritized: list[dict[str, Any]],
    report: dict[str, Any],
) -> dict[str, Any]:
    controls = Counter(_str(item.get("control_id"), "unknown") for item in prioritized)
    category_counts = Counter(_str(item.get("category"), "Unknown") for item in prioritized)
    severity_counts = Counter(_str(item.get("severity"), "unknown") for item in prioritized)
    priority_counts = Counter(_str(item.get("priority"), "Monitor") for item in prioritized)
    non_compliant = _dict(report.get("evaluation_context")).get(
        "non_compliant_findings",
        len(prioritized),
    )
    return {
        "finding_count": len(prioritized),
        "non_compliant_finding_count": _int(non_compliant, len(prioritized)),
        "severity_counts": dict(sorted(severity_counts.items())),
        "priority_counts": dict(sorted(priority_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "top_controls": [
            {"control_id": control_id, "finding_count": count}
            for control_id, count in controls.most_common(10)
        ],
        "top_risks": [
            {
                "finding_id": item.get("finding_id"),
                "control_id": item.get("control_id"),
                "title": item.get("title"),
                "priority": item.get("priority"),
                "score": item.get("score"),
                "category": item.get("category"),
            }
            for item in sorted(
                prioritized,
                key=lambda risk: _float(risk.get("score"), 0.0),
                reverse=True,
            )[:10]
        ],
    }


def _compliance_summary(report: dict[str, Any]) -> dict[str, Any]:
    compliance = _dict(report.get("compliance"))
    frameworks = _list(compliance.get("frameworks_covered"))
    uk_profile = _dict(compliance.get("uk_sme_profile"))
    findings_by_framework = _dict(compliance.get("findings_by_framework"))
    ce_readiness = _dict(report.get("cyber_essentials_readiness"))
    return {
        "framework_count": len(frameworks),
        "frameworks_covered": frameworks,
        "findings_by_framework": findings_by_framework,
        "uk_sme_mapped_control_count": _int(uk_profile.get("mapped_control_count"), 0),
        "uk_sme_profile": uk_profile,
        "cyber_essentials_overall_readiness_score": ce_readiness.get(
            "overall_readiness_score"
        ),
        "cyber_essentials_pillar_count": _int(ce_readiness.get("pillar_count"), 0),
    }


def _resource_summary(report: dict[str, Any]) -> dict[str, Any]:
    resource_context = _dict(report.get("resource_context"))
    assets = _list_of_dicts(resource_context.get("assets"))
    links = _list_of_dicts(resource_context.get("finding_asset_links"))
    asset_type_counts = Counter(_str(asset.get("asset_type"), "unknown") for asset in assets)
    provider_counts = Counter(_str(asset.get("provider"), "unknown") for asset in assets)
    exposure_counts = Counter(
        _str(asset.get("exposure"), "unknown")
        for asset in assets
        if asset.get("exposure") is not None
    )
    return {
        "context_model": resource_context.get("context_model"),
        "asset_count": len(assets),
        "evidence_record_count": len(_list_of_dicts(resource_context.get("evidence_records"))),
        "finding_asset_link_count": len(links),
        "asset_type_counts": dict(sorted(asset_type_counts.items())),
        "provider_counts": dict(sorted(provider_counts.items())),
        "exposure_counts": dict(sorted(exposure_counts.items())),
        "linked_finding_count": len(
            {
                _str(link.get("finding_id"), "")
                for link in links
                if _str(link.get("finding_id"), "")
            }
        ),
    }


def _evidence_summary(
    prioritized: list[dict[str, Any]],
    report: dict[str, Any],
) -> dict[str, Any]:
    sufficiency_counts: Counter[str] = Counter()
    observation_counts: Counter[str] = Counter()
    direct_count = 0
    inferred_count = 0
    unavailable_count = 0
    for risk in prioritized:
        quality = _dict(risk.get("evidence_quality"))
        sufficiency_counts[_str(quality.get("sufficiency"), "unknown")] += 1
        observation_counts[_str(quality.get("observation_class"), "unknown")] += 1
        direct_count += _int(quality.get("direct_evidence_count"), 0)
        inferred_count += _int(quality.get("inferred_evidence_count"), 0)
        unavailable_count += _int(quality.get("unavailable_evidence_count"), 0)

    backlog = _dict(report.get("evidence_gap_backlog"))
    replay = _dict(report.get("assessment_replay"))
    replay_status = _dict(replay.get("replay"))
    evidence_diff = _dict(replay.get("evidence_diff"))
    return {
        "sufficiency_counts": dict(sorted(sufficiency_counts.items())),
        "observation_class_counts": dict(sorted(observation_counts.items())),
        "direct_evidence_count": direct_count,
        "inferred_evidence_count": inferred_count,
        "unavailable_evidence_count": unavailable_count,
        "evidence_gap_backlog_count": _int(backlog.get("item_count"), 0),
        "high_priority_gap_count": _int(backlog.get("high_priority_count"), 0),
        "replayable": bool(replay_status.get("replayable", False)),
        "deterministic_replay_match": bool(
            replay_status.get("deterministic_match", False)
        ),
        "evidence_changed_since_previous": bool(evidence_diff.get("evidence_changed", False)),
    }


def _lifecycle_summary(
    prioritized: list[dict[str, Any]],
    report: dict[str, Any],
) -> dict[str, Any]:
    status_counts = Counter(
        _str(_dict(item.get("lifecycle")).get("status"), "open")
        for item in prioritized
    )
    lifecycle = _dict(report.get("finding_lifecycle_summary"))
    return {
        "status_counts": dict(sorted(status_counts.items())),
        "summary_status_counts": _dict(lifecycle.get("status_counts")),
        "new_finding_count": sum(
            1
            for item in prioritized
            if bool(_dict(item.get("lifecycle")).get("is_new", False))
        ),
        "recurring_finding_count": sum(
            1
            for item in prioritized
            if _int(_dict(item.get("lifecycle")).get("recurrence_count"), 0) > 0
        ),
        "exception_applied_count": _int(lifecycle.get("exception_applied_count"), 0),
    }


def _drift_summary(report: dict[str, Any]) -> dict[str, Any]:
    risk_drift = _dict(report.get("risk_drift_analysis"))
    control_drift = _dict(report.get("control_drift_attribution"))
    return {
        "risk_drift_status": risk_drift.get("status"),
        "risk_drift_direction": risk_drift.get("direction"),
        "risk_drift_overall_delta": risk_drift.get("overall_risk_delta"),
        "control_drift_comparable": bool(control_drift.get("comparable", False)),
        "control_drift_primary_attribution": control_drift.get(
            "primary_attribution",
            "unknown",
        ),
        "control_drift_overall_delta": control_drift.get("overall_risk_delta"),
        "control_drift_attribution_counts": _dict(
            control_drift.get("attribution_counts")
        ),
        "evidence_changed": bool(control_drift.get("evidence_changed", False)),
        "policy_pack_changed": bool(control_drift.get("policy_pack_changed", False)),
        "collector_mode_changed": bool(
            control_drift.get("collector_mode_changed", False)
        ),
    }


def _claim_summary(report: dict[str, Any]) -> dict[str, Any]:
    pack = _dict(report.get("claim_verification_pack"))
    return {
        "pack_schema_version": pack.get("pack_schema_version"),
        "claim_count": _int(pack.get("claim_count"), 0),
        "verified_claim_count": _int(pack.get("verified_claim_count"), 0),
        "caveated_claim_count": _int(pack.get("caveated_claim_count"), 0),
        "claim_type_counts": _dict(pack.get("claim_type_counts")),
    }


def _action_summary(report: dict[str, Any]) -> dict[str, Any]:
    action_plan = _dict(report.get("action_plan_30_day"))
    phases = _list_of_dicts(action_plan.get("phases"))
    phase_counts: dict[str, int] = {}
    owner_counts: Counter[str] = Counter()
    total_actions = 0
    for phase in phases:
        actions = _list_of_dicts(phase.get("actions"))
        phase_name = _str(
            phase.get("phase_name") or phase.get("label") or phase.get("name"),
            "unknown",
        )
        phase_counts[phase_name] = len(actions)
        total_actions += len(actions)
        for action in actions:
            owner_counts[_str(action.get("owner"), "Unassigned")] += 1
    return {
        "phase_count": len(phases),
        "action_count": total_actions,
        "phase_action_counts": phase_counts,
        "owner_counts": dict(sorted(owner_counts.items())),
    }


def _provider_summary(report: dict[str, Any]) -> dict[str, Any]:
    contracts = _dict(report.get("provider_evidence_contracts"))
    conformance = _dict(report.get("provider_contract_conformance"))
    return {
        "contract_schema_version": contracts.get("contract_schema_version"),
        "provider_count": _int(contracts.get("provider_count"), 0),
        "control_count": _int(contracts.get("control_count"), 0),
        "contract_count": _int(contracts.get("contract_count"), 0),
        "support_status_counts": _dict(contracts.get("support_status_counts")),
        "conformance_passed": bool(conformance.get("passed", False)),
        "active_contract_count": _int(conformance.get("active_contract_count"), 0),
        "planned_contract_count": _int(conformance.get("planned_contract_count"), 0),
        "failed_contract_count": _int(conformance.get("failed_contract_count"), 0),
    }


def _assurance_summary(report: dict[str, Any]) -> dict[str, Any]:
    assurance = _dict(report.get("assessment_assurance"))
    trust_badge = _dict(report.get("report_trust_badge"))
    assurance_case = _dict(report.get("assurance_case"))
    return {
        "assessment_assurance_score": assurance.get("assurance_score"),
        "assessment_assurance_level": assurance.get("assurance_level"),
        "trust_badge_level": trust_badge.get("level"),
        "trust_badge_assurance_score": trust_badge.get("assurance_score"),
        "assurance_case_conclusion": assurance_case.get("overall_conclusion"),
        "assurance_case_score": assurance_case.get("assurance_score"),
    }


def _risk_band(score: float) -> str:
    if score >= 70:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 30:
        return "moderate"
    if score > 0:
        return "low"
    return "clear"


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _list_of_dicts(value: object) -> list[dict[str, Any]]:
    return [item for item in _list(value) if isinstance(item, dict)]


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _str(value: object, default: str) -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
