# Deterministic budget-aware remediation planning for SME-oriented action packs.
from __future__ import annotations

from pydantic import BaseModel, Field

from cris_sme.engine.scoring import ScoredFinding
from cris_sme.models.finding import RemediationCostTier


COST_TIER_WEIGHTS: dict[RemediationCostTier, float] = {
    RemediationCostTier.FREE: 1.0,
    RemediationCostTier.LOW: 1.35,
    RemediationCostTier.MEDIUM: 1.85,
    RemediationCostTier.HIGH: 2.75,
}

BUDGET_PROFILES = [
    {
        "profile_id": "free_this_week",
        "label": "Free fixes this week",
        "description": (
            "Prioritize zero-cost configuration changes and governance fixes that can be "
            "started immediately."
        ),
        "max_monthly_cost_gbp": 0,
        "allowed_tiers": [RemediationCostTier.FREE],
        "top_n": 5,
    },
    {
        "profile_id": "under_200_month",
        "label": "Under GBP200 per month",
        "description": (
            "Focus on the highest-value combination of free and low-cost remediations "
            "that fit a lean SME cloud budget."
        ),
        "max_monthly_cost_gbp": 200,
        "allowed_tiers": [RemediationCostTier.FREE, RemediationCostTier.LOW],
        "top_n": 7,
    },
    {
        "profile_id": "under_750_month",
        "label": "Under GBP750 per month",
        "description": (
            "Broaden coverage to include medium-cost protections where they materially "
            "reduce SME cloud risk."
        ),
        "max_monthly_cost_gbp": 750,
        "allowed_tiers": [
            RemediationCostTier.FREE,
            RemediationCostTier.LOW,
            RemediationCostTier.MEDIUM,
        ],
        "top_n": 10,
    },
]


class RemediationRecommendation(BaseModel):
    """Budget-aware recommendation for a single scored finding."""

    control_id: str = Field(..., min_length=3)
    title: str = Field(..., min_length=5)
    category: str = Field(..., min_length=2)
    organization: str = Field(..., min_length=2)
    priority: str = Field(..., min_length=2)
    score: float = Field(..., ge=0.0, le=100.0)
    remediation_cost_tier: str = Field(..., min_length=2)
    remediation_summary: str = Field(..., min_length=3)
    remediation_value_score: float = Field(..., ge=0.0)


class BudgetPlan(BaseModel):
    """Action pack for a specific SME budget band."""

    profile_id: str = Field(..., min_length=3)
    label: str = Field(..., min_length=3)
    description: str = Field(..., min_length=8)
    max_monthly_cost_gbp: int = Field(..., ge=0)
    allowed_cost_tiers: list[str] = Field(default_factory=list)
    total_recommended: int = Field(..., ge=0)
    cumulative_risk_score: float = Field(..., ge=0.0)
    average_value_score: float = Field(..., ge=0.0)
    recommended_actions: list[RemediationRecommendation] = Field(default_factory=list)


class RemediationPlanResult(BaseModel):
    """Structured output of budget-aware remediation planning."""

    value_score_method: str = Field(..., min_length=10)
    budget_profiles: list[BudgetPlan] = Field(default_factory=list)


def build_budget_aware_remediation_plan(
    prioritized_findings: list[ScoredFinding],
) -> RemediationPlanResult:
    """Build practical action packs for common SME remediation budget levels."""
    scored_actions = [
        _to_recommendation(finding)
        for finding in prioritized_findings
        if finding.finding.remediation_cost_tier is not None
    ]

    budget_profiles = [
        _build_budget_profile(
            profile_id=str(profile["profile_id"]),
            label=str(profile["label"]),
            description=str(profile["description"]),
            max_monthly_cost_gbp=int(profile["max_monthly_cost_gbp"]),
            allowed_tiers=list(profile["allowed_tiers"]),
            top_n=int(profile["top_n"]),
            recommendations=scored_actions,
        )
        for profile in BUDGET_PROFILES
    ]

    return RemediationPlanResult(
        value_score_method=(
            "remediation_value_score = finding_score / remediation_cost_weight, "
            "where cheaper fixes are favored when risk scores are similar"
        ),
        budget_profiles=budget_profiles,
    )


def budget_fit_profile_ids(cost_tier: RemediationCostTier | None) -> list[str]:
    """Return the budget profiles that can accommodate the given remediation tier."""
    if cost_tier is None:
        return []

    return [
        str(profile["profile_id"])
        for profile in BUDGET_PROFILES
        if cost_tier in profile["allowed_tiers"]
    ]


def _to_recommendation(scored_finding: ScoredFinding) -> RemediationRecommendation:
    """Convert a scored finding into a budget-aware remediation recommendation."""
    finding = scored_finding.finding
    remediation_cost_tier = finding.remediation_cost_tier
    assert remediation_cost_tier is not None

    return RemediationRecommendation(
        control_id=finding.control_id,
        title=finding.title,
        category=finding.category.value,
        organization=str(
            finding.metadata.get("organization_name", "unknown organization")
        ),
        priority=scored_finding.priority,
        score=scored_finding.score,
        remediation_cost_tier=remediation_cost_tier.value,
        remediation_summary=finding.remediation_summary or "No remediation guidance recorded",
        remediation_value_score=round(
            scored_finding.score / COST_TIER_WEIGHTS[remediation_cost_tier],
            2,
        ),
    )


def _build_budget_profile(
    *,
    profile_id: str,
    label: str,
    description: str,
    max_monthly_cost_gbp: int,
    allowed_tiers: list[RemediationCostTier],
    top_n: int,
    recommendations: list[RemediationRecommendation],
) -> BudgetPlan:
    """Build a single SME budget profile from the recommendation pool."""
    eligible = [
        recommendation
        for recommendation in recommendations
        if recommendation.remediation_cost_tier
        in {tier.value for tier in allowed_tiers}
    ]
    ranked = sorted(
        eligible,
        key=lambda item: (item.remediation_value_score, item.score),
        reverse=True,
    )[:top_n]

    total_recommended = len(ranked)
    cumulative_risk_score = round(sum(item.score for item in ranked), 2)
    average_value_score = round(
        sum(item.remediation_value_score for item in ranked) / total_recommended,
        2,
    ) if total_recommended else 0.0

    return BudgetPlan(
        profile_id=profile_id,
        label=label,
        description=description,
        max_monthly_cost_gbp=max_monthly_cost_gbp,
        allowed_cost_tiers=[tier.value for tier in allowed_tiers],
        total_recommended=total_recommended,
        cumulative_risk_score=cumulative_risk_score,
        average_value_score=average_value_score,
        recommended_actions=ranked,
    )
