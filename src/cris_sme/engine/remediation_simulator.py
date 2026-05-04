# Deterministic remediation simulation for CRIS-SME risk-reduction planning.
from __future__ import annotations

from statistics import mean

from pydantic import BaseModel, Field

from cris_sme.engine.lineage import build_stable_finding_id
from cris_sme.engine.remediation import BUDGET_PROFILES, COST_TIER_WEIGHTS
from cris_sme.engine.scoring import CATEGORY_WEIGHTS, ScoredFinding, ScoringResult
from cris_sme.models.finding import FindingCategory, RemediationCostTier


class SimulatedRemediationAction(BaseModel):
    """One finding assumed remediated inside a deterministic simulation scenario."""

    finding_id: str = Field(..., min_length=6)
    control_id: str = Field(..., min_length=3)
    title: str = Field(..., min_length=5)
    category: str = Field(..., min_length=2)
    organization: str = Field(..., min_length=2)
    current_score: float = Field(..., ge=0.0, le=100.0)
    remediation_cost_tier: str = Field(..., min_length=2)
    remediation_value_score: float = Field(..., ge=0.0)


class RemediationSimulationScenario(BaseModel):
    """Before/after score impact for one deterministic remediation scenario."""

    scenario_id: str = Field(..., min_length=3)
    label: str = Field(..., min_length=3)
    basis: str = Field(..., min_length=8)
    selected_action_count: int = Field(..., ge=0)
    current_overall_risk_score: float = Field(..., ge=0.0, le=100.0)
    simulated_overall_risk_score: float = Field(..., ge=0.0, le=100.0)
    expected_risk_reduction: float = Field(..., ge=0.0)
    expected_risk_reduction_percent: float = Field(..., ge=0.0)
    current_non_compliant_findings: int = Field(..., ge=0)
    simulated_non_compliant_findings: int = Field(..., ge=0)
    category_score_deltas: dict[str, float] = Field(default_factory=dict)
    selected_actions: list[SimulatedRemediationAction] = Field(default_factory=list)


class RemediationSimulationResult(BaseModel):
    """Deterministic remediation simulation output for an assessment."""

    simulation_model: str = Field(default="cris_sme_deterministic_remediation_simulator_v1")
    method_summary: str = Field(..., min_length=10)
    scenarios: list[RemediationSimulationScenario] = Field(default_factory=list)


class RemediationSimulationRequest(BaseModel):
    """Custom remediation simulation selector for future API/UI workflows."""

    scenario_id: str = Field(..., min_length=3)
    label: str = Field(..., min_length=3)
    finding_ids: list[str] = Field(default_factory=list)
    control_ids: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)


def build_remediation_simulation(
    scoring_result: ScoringResult,
) -> RemediationSimulationResult:
    """Build default deterministic remediation what-if scenarios."""
    scenarios = [
        _simulate_scenario(
            scoring_result,
            scenario_id="fix_free_this_week",
            label="Fix free actions this week",
            basis="Top free remediation actions ranked by remediation value score.",
            selected=_select_by_budget_profile(scoring_result.prioritized_findings, "free_this_week"),
        ),
        _simulate_scenario(
            scoring_result,
            scenario_id="fix_under_200_month",
            label="Fix actions under GBP200/month",
            basis="Top free and low-cost actions ranked by remediation value score.",
            selected=_select_by_budget_profile(scoring_result.prioritized_findings, "under_200_month"),
        ),
        _simulate_scenario(
            scoring_result,
            scenario_id="fix_under_750_month",
            label="Fix actions under GBP750/month",
            basis="Top free, low, and medium-cost actions ranked by remediation value score.",
            selected=_select_by_budget_profile(scoring_result.prioritized_findings, "under_750_month"),
        ),
        _simulate_scenario(
            scoring_result,
            scenario_id="fix_top_5_risks",
            label="Fix top 5 risks",
            basis="Five highest-scoring active findings regardless of cost tier.",
            selected=scoring_result.prioritized_findings[:5],
        ),
    ]

    return RemediationSimulationResult(
        method_summary=(
            "Scenarios assume selected findings are remediated and removed from the "
            "active non-compliant set, then domain and overall scores are recomputed "
            "using the existing deterministic category weighting model. This is a "
            "planning simulator, not an incident-probability forecast."
        ),
        scenarios=scenarios,
    )


def build_custom_remediation_simulation(
    scoring_result: ScoringResult,
    request: RemediationSimulationRequest,
) -> RemediationSimulationScenario:
    """Build one custom scenario from explicit finding/control/category selectors."""
    selected = _select_custom_findings(scoring_result.prioritized_findings, request)
    return _simulate_scenario(
        scoring_result,
        scenario_id=request.scenario_id,
        label=request.label,
        basis=_custom_basis(request),
        selected=selected,
    )


def build_custom_report_remediation_simulation(
    report: dict[str, object],
    request: RemediationSimulationRequest,
) -> dict[str, object]:
    """Build a custom remediation scenario from an existing JSON report artifact."""
    risks = report.get("prioritized_risks", [])
    if not isinstance(risks, list):
        risks = []
    selected = [
        risk for risk in risks if isinstance(risk, dict) and _risk_matches_request(risk, request)
    ]
    remaining = [
        risk for risk in risks if isinstance(risk, dict) and not _risk_matches_request(risk, request)
    ]
    category_scores = report.get("category_scores", {})
    if not isinstance(category_scores, dict):
        category_scores = {}

    simulated_category_scores = _aggregate_report_category_scores(remaining)
    current_overall = float(report.get("overall_risk_score", 0.0))
    simulated_overall = _calculate_overall_score(simulated_category_scores)
    expected_reduction = max(0.0, round(current_overall - simulated_overall, 2))
    return {
        "scenario_id": request.scenario_id,
        "label": request.label,
        "basis": _custom_basis(request),
        "selected_action_count": len(selected),
        "current_overall_risk_score": round(current_overall, 2),
        "simulated_overall_risk_score": round(simulated_overall, 2),
        "expected_risk_reduction": expected_reduction,
        "expected_risk_reduction_percent": (
            round((expected_reduction / current_overall) * 100.0, 2)
            if current_overall > 0
            else 0.0
        ),
        "current_non_compliant_findings": len(risks),
        "simulated_non_compliant_findings": len(remaining),
        "category_score_deltas": {
            str(category): _clean_delta(
                float(score) - simulated_category_scores.get(str(category), 0.0)
            )
            for category, score in category_scores.items()
        },
        "selected_actions": [_report_risk_to_action(risk) for risk in selected],
    }


def _simulate_scenario(
    scoring_result: ScoringResult,
    *,
    scenario_id: str,
    label: str,
    basis: str,
    selected: list[ScoredFinding],
) -> RemediationSimulationScenario:
    selected_ids = {build_stable_finding_id(item.finding) for item in selected}
    remaining = [
        item
        for item in scoring_result.prioritized_findings
        if build_stable_finding_id(item.finding) not in selected_ids
    ]
    simulated_category_scores = _aggregate_category_scores(remaining)
    simulated_overall = _calculate_overall_score(simulated_category_scores)
    current_overall = scoring_result.overall_risk_score
    expected_reduction = max(0.0, round(current_overall - simulated_overall, 2))
    reduction_percent = (
        round((expected_reduction / current_overall) * 100.0, 2)
        if current_overall > 0
        else 0.0
    )

    return RemediationSimulationScenario(
        scenario_id=scenario_id,
        label=label,
        basis=basis,
        selected_action_count=len(selected),
        current_overall_risk_score=current_overall,
        simulated_overall_risk_score=round(simulated_overall, 2),
        expected_risk_reduction=expected_reduction,
        expected_risk_reduction_percent=reduction_percent,
        current_non_compliant_findings=scoring_result.non_compliant_findings,
        simulated_non_compliant_findings=len(remaining),
        category_score_deltas={
            category: _clean_delta(
                scoring_result.category_scores.get(category, 0.0)
                - simulated_category_scores.get(category, 0.0)
            )
            for category in scoring_result.category_scores
        },
        selected_actions=[_to_action(item) for item in selected],
    )


def _select_custom_findings(
    prioritized_findings: list[ScoredFinding],
    request: RemediationSimulationRequest,
) -> list[ScoredFinding]:
    return [
        item
        for item in prioritized_findings
        if _finding_matches_request(item, request)
    ]


def _finding_matches_request(
    item: ScoredFinding,
    request: RemediationSimulationRequest,
) -> bool:
    finding_id = build_stable_finding_id(item.finding)
    categories = {category.lower() for category in request.categories}
    return (
        finding_id in set(request.finding_ids)
        or item.finding.control_id in set(request.control_ids)
        or item.finding.category.value.lower() in categories
    )


def _risk_matches_request(
    risk: dict[str, object],
    request: RemediationSimulationRequest,
) -> bool:
    categories = {category.lower() for category in request.categories}
    return (
        str(risk.get("finding_id", "")) in set(request.finding_ids)
        or str(risk.get("control_id", "")) in set(request.control_ids)
        or str(risk.get("category", "")).lower() in categories
    )


def _custom_basis(request: RemediationSimulationRequest) -> str:
    parts: list[str] = []
    if request.finding_ids:
        parts.append(f"finding_ids={','.join(sorted(request.finding_ids))}")
    if request.control_ids:
        parts.append(f"control_ids={','.join(sorted(request.control_ids))}")
    if request.categories:
        parts.append(f"categories={','.join(sorted(request.categories))}")
    return "Custom remediation scenario selected by " + "; ".join(parts or ["no selectors"])


def _select_by_budget_profile(
    prioritized_findings: list[ScoredFinding],
    profile_id: str,
) -> list[ScoredFinding]:
    profile = next(
        item for item in BUDGET_PROFILES if str(item["profile_id"]) == profile_id
    )
    allowed_tiers = set(profile["allowed_tiers"])
    top_n = int(profile["top_n"])
    eligible = [
        item
        for item in prioritized_findings
        if item.finding.remediation_cost_tier in allowed_tiers
    ]
    return sorted(
        eligible,
        key=lambda item: (_remediation_value_score(item), item.score),
        reverse=True,
    )[:top_n]


def _aggregate_category_scores(scored_findings: list[ScoredFinding]) -> dict[str, float]:
    grouped_scores: dict[str, list[float]] = {
        category.value: [] for category in FindingCategory
    }
    for item in scored_findings:
        grouped_scores[item.finding.category.value].append(item.score)
    return {
        category: mean(scores) if scores else 0.0
        for category, scores in grouped_scores.items()
    }


def _calculate_overall_score(category_scores: dict[str, float]) -> float:
    weighted_total = 0.0
    for category, weight in CATEGORY_WEIGHTS.items():
        weighted_total += category_scores.get(category.value, 0.0) * weight
    return round(weighted_total, 2)


def _aggregate_report_category_scores(risks: list[object]) -> dict[str, float]:
    grouped_scores: dict[str, list[float]] = {
        category.value: [] for category in FindingCategory
    }
    for risk in risks:
        if not isinstance(risk, dict):
            continue
        category = str(risk.get("category", ""))
        if category not in grouped_scores:
            grouped_scores[category] = []
        grouped_scores[category].append(float(risk.get("score", 0.0)))
    return {
        category: mean(scores) if scores else 0.0
        for category, scores in grouped_scores.items()
    }


def _to_action(item: ScoredFinding) -> SimulatedRemediationAction:
    tier = item.finding.remediation_cost_tier
    tier_value = tier.value if tier is not None else "unknown"
    return SimulatedRemediationAction(
        finding_id=build_stable_finding_id(item.finding),
        control_id=item.finding.control_id,
        title=item.finding.title,
        category=item.finding.category.value,
        organization=str(item.finding.metadata.get("organization_name", "unknown organization")),
        current_score=item.score,
        remediation_cost_tier=tier_value,
        remediation_value_score=_remediation_value_score(item),
    )


def _report_risk_to_action(risk: dict[str, object]) -> dict[str, object]:
    return {
        "finding_id": risk.get("finding_id"),
        "control_id": risk.get("control_id"),
        "title": risk.get("title"),
        "category": risk.get("category"),
        "organization": risk.get("organization"),
        "current_score": risk.get("score"),
        "remediation_cost_tier": risk.get("remediation_cost_tier"),
        "remediation_value_score": risk.get("remediation_value_score"),
    }


def _remediation_value_score(item: ScoredFinding) -> float:
    tier: RemediationCostTier | None = item.finding.remediation_cost_tier
    if tier is None:
        return round(item.score / 3.25, 2)
    return round(item.score / COST_TIER_WEIGHTS[tier], 2)


def _clean_delta(value: float) -> float:
    rounded = round(value, 2)
    return 0.0 if rounded == 0 else rounded
