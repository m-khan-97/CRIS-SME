# Deterministic 30-day SME action planning derived from CRIS-SME prioritized risks.
from __future__ import annotations

from pydantic import BaseModel, Field

from cris_sme.engine.scoring import ScoredFinding
from cris_sme.models.finding import RemediationCostTier


class ActionPlanTask(BaseModel):
    """A single remediation task in the 30-day SME action plan."""

    control_id: str = Field(..., min_length=3)
    title: str = Field(..., min_length=5)
    organization: str = Field(..., min_length=2)
    category: str = Field(..., min_length=2)
    priority: str = Field(..., min_length=2)
    score: float = Field(..., ge=0.0, le=100.0)
    remediation_cost_tier: str = Field(..., min_length=2)
    remediation_summary: str = Field(..., min_length=3)
    action_rationale: str = Field(..., min_length=8)


class ActionPlanPhase(BaseModel):
    """A time-boxed phase inside the 30-day SME action plan."""

    phase_id: str = Field(..., min_length=3)
    label: str = Field(..., min_length=3)
    time_window: str = Field(..., min_length=3)
    goal: str = Field(..., min_length=8)
    total_actions: int = Field(..., ge=0)
    cumulative_risk_score: float = Field(..., ge=0.0)
    actions: list[ActionPlanTask] = Field(default_factory=list)


class ActionPlan30DayResult(BaseModel):
    """A pragmatic 30-day action plan for a budget-conscious SME."""

    plan_name: str = Field(..., min_length=3)
    planning_basis: str = Field(..., min_length=8)
    phases: list[ActionPlanPhase] = Field(default_factory=list)


def build_30_day_action_plan(
    prioritized_findings: list[ScoredFinding],
) -> ActionPlan30DayResult:
    """Build a phased 30-day remediation plan from prioritized CRIS-SME findings."""
    week_one_candidates = [
        item
        for item in prioritized_findings
        if item.finding.remediation_cost_tier == RemediationCostTier.FREE
    ]
    week_one = _select_phase_actions(week_one_candidates, limit=5)
    week_one_ids = {item.finding.control_id for item in week_one}

    days_8_30_candidates = [
        item
        for item in prioritized_findings
        if item.finding.remediation_cost_tier in {RemediationCostTier.FREE, RemediationCostTier.LOW}
        and item.finding.control_id not in week_one_ids
    ]
    days_8_30 = _select_phase_actions(days_8_30_candidates, limit=7)
    scheduled_ids = week_one_ids | {item.finding.control_id for item in days_8_30}

    carry_forward_candidates = [
        item for item in prioritized_findings if item.finding.control_id not in scheduled_ids
    ]
    carry_forward = _select_phase_actions(carry_forward_candidates, limit=5)

    return ActionPlan30DayResult(
        plan_name="CRIS-SME 30-Day SME Action Plan",
        planning_basis=(
            "Actions are phased by deterministic risk score, remediation cost tier, and "
            "SME-operational practicality so free and low-friction improvements land first."
        ),
        phases=[
            _build_phase(
                phase_id="days_1_7",
                label="Fix this week",
                time_window="Days 1-7",
                goal="Prioritize zero-cost or low-friction fixes that reduce immediate exposure.",
                findings=week_one,
            ),
            _build_phase(
                phase_id="days_8_30",
                label="Complete this month",
                time_window="Days 8-30",
                goal="Deliver the best remaining low-cost improvements within a lean SME operating window.",
                findings=days_8_30,
            ),
            _build_phase(
                phase_id="carry_forward",
                label="Plan next",
                time_window="After day 30",
                goal="Schedule higher-effort items that likely need architecture, tooling, or procurement support.",
                findings=carry_forward,
            ),
        ],
    )


def _select_phase_actions(
    findings: list[ScoredFinding],
    *,
    limit: int,
) -> list[ScoredFinding]:
    """Choose the strongest actions for a phase based on value and urgency."""
    ranked = sorted(
        findings,
        key=lambda item: (
            _cost_tier_rank(item.finding.remediation_cost_tier),
            -item.score,
        ),
    )
    return ranked[:limit]


def _build_phase(
    *,
    phase_id: str,
    label: str,
    time_window: str,
    goal: str,
    findings: list[ScoredFinding],
) -> ActionPlanPhase:
    """Convert selected findings into a single action-plan phase."""
    actions = [_to_task(item, phase_label=label) for item in findings]
    return ActionPlanPhase(
        phase_id=phase_id,
        label=label,
        time_window=time_window,
        goal=goal,
        total_actions=len(actions),
        cumulative_risk_score=round(sum(item.score for item in findings), 2),
        actions=actions,
    )


def _to_task(item: ScoredFinding, *, phase_label: str) -> ActionPlanTask:
    """Convert a scored finding into an action-plan task."""
    tier = item.finding.remediation_cost_tier
    tier_value = tier.value if tier is not None else "unknown"
    return ActionPlanTask(
        control_id=item.finding.control_id,
        title=item.finding.title,
        organization=str(item.finding.metadata.get("organization_name", "unknown organization")),
        category=item.finding.category.value,
        priority=item.priority,
        score=item.score,
        remediation_cost_tier=tier_value,
        remediation_summary=item.finding.remediation_summary or "No remediation guidance recorded",
        action_rationale=_action_rationale(item, phase_label=phase_label),
    )


def _action_rationale(item: ScoredFinding, *, phase_label: str) -> str:
    """Explain why this action was placed in the current phase."""
    tier = item.finding.remediation_cost_tier
    tier_label = tier.value if tier is not None else "unknown"
    return (
        f"Placed in '{phase_label}' because it carries {item.priority.lower()} urgency, "
        f"a {item.score:.2f} risk score, and a {tier_label} remediation cost profile."
    )


def _cost_tier_rank(cost_tier: RemediationCostTier | None) -> int:
    """Order lower-cost remediations ahead of more complex ones within a phase."""
    order = {
        RemediationCostTier.FREE: 0,
        RemediationCostTier.LOW: 1,
        RemediationCostTier.MEDIUM: 2,
        RemediationCostTier.HIGH: 3,
        None: 4,
    }
    return order[cost_tier]
