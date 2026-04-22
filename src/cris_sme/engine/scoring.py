# Deterministic scoring logic for converting findings into explainable risk outputs.
from __future__ import annotations

from statistics import mean

from pydantic import BaseModel, Field

from cris_sme.engine.confidence import calibrate_finding_confidence
from cris_sme.models.finding import Finding, FindingCategory, FindingSeverity

SEVERITY_WEIGHTS: dict[FindingSeverity, float] = {
    FindingSeverity.CRITICAL: 10.0,
    FindingSeverity.HIGH: 7.0,
    FindingSeverity.MEDIUM: 4.0,
    FindingSeverity.LOW: 1.0,
}

CATEGORY_WEIGHTS: dict[FindingCategory, float] = {
    FindingCategory.IAM: 0.25,
    FindingCategory.NETWORK: 0.20,
    FindingCategory.DATA: 0.20,
    FindingCategory.MONITORING: 0.15,
    FindingCategory.COMPUTE: 0.10,
    FindingCategory.GOVERNANCE: 0.10,
}

MAX_FINDING_SCORE = SEVERITY_WEIGHTS[FindingSeverity.CRITICAL] * 1.6 * 1.6 * 1.0


class ScoreBreakdown(BaseModel):
    """Explainable breakdown of a single finding's deterministic score."""

    observed_confidence: float = Field(
        ...,
        description="Raw control confidence prior to calibration.",
    )
    calibrated_confidence: float = Field(
        ...,
        description="Confidence after blending observed control confidence with calibration metadata.",
    )
    calibration_status: str = Field(
        ...,
        description="Calibration maturity label for the underlying control.",
    )
    base_severity: float = Field(..., description="Numeric weight derived from severity.")
    likelihood_factor: float = Field(..., description="Modifier driven by exposure.")
    data_factor: float = Field(..., description="Modifier driven by data sensitivity.")
    confidence_factor: float = Field(..., description="Modifier driven by confidence.")
    remediation_factor: float = Field(
        ...,
        description="Small uplift reflecting operational effort to remediate.",
    )
    raw_score: float = Field(..., description="Unbounded score before normalization.")
    normalized_score: float = Field(..., ge=0.0, le=100.0, description="0-100 score.")


class ScoredFinding(BaseModel):
    """Finding enriched with score, priority, and explainability details."""

    finding: Finding
    score: float = Field(..., ge=0.0, le=100.0)
    priority: str = Field(..., description="Priority label derived from the score.")
    breakdown: ScoreBreakdown


class ScoringResult(BaseModel):
    """Aggregated output of the scoring engine for a set of findings."""

    overall_risk_score: float = Field(..., ge=0.0, le=100.0)
    category_scores: dict[str, float]
    prioritized_findings: list[ScoredFinding]
    total_findings: int = Field(..., ge=0)
    non_compliant_findings: int = Field(..., ge=0)

    @property
    def summary(self) -> str:
        """Short human-readable summary suitable for CLI and reporting."""
        return (
            f"Overall risk score: {self.overall_risk_score:.2f}/100 across "
            f"{self.non_compliant_findings} non-compliant findings."
        )


def score_findings(findings: list[Finding]) -> ScoringResult:
    """Score findings and return category and overall risk views."""
    scored_findings = [_score_finding(finding) for finding in findings if finding.is_risk]

    category_scores = _aggregate_category_scores(scored_findings)
    overall_risk_score = _calculate_overall_score(category_scores)

    prioritized_findings = sorted(
        scored_findings,
        key=lambda item: item.score,
        reverse=True,
    )

    return ScoringResult(
        overall_risk_score=round(overall_risk_score, 2),
        category_scores={key: round(value, 2) for key, value in category_scores.items()},
        prioritized_findings=prioritized_findings,
        total_findings=len(findings),
        non_compliant_findings=len(scored_findings),
    )


def _score_finding(finding: Finding) -> ScoredFinding:
    """Apply the deterministic CRIS-SME scoring formula to one finding."""
    calibration = calibrate_finding_confidence(finding)
    base_severity = SEVERITY_WEIGHTS[finding.severity]
    likelihood_factor = 0.8 + (0.8 * finding.exposure)
    data_factor = 0.8 + (0.8 * finding.data_sensitivity)
    confidence_factor = 0.7 + (0.3 * calibration.calibrated_confidence)

    # Remediation effort slightly increases urgency for issues that are likely to persist.
    remediation_factor = 1.0 + (0.15 * finding.remediation_effort)

    raw_score = (
        base_severity
        * likelihood_factor
        * data_factor
        * confidence_factor
        * remediation_factor
    )
    # Keep a small headroom band above the modeled maximum so very severe findings
    # do not collapse into a saturated 100 too easily; this preserves ranking space
    # for future calibration while keeping the current deterministic model bounded.
    normalized_score = min((raw_score / (MAX_FINDING_SCORE * 1.15)) * 100, 100.0)

    breakdown = ScoreBreakdown(
        observed_confidence=round(calibration.observed_confidence, 4),
        calibrated_confidence=round(calibration.calibrated_confidence, 4),
        calibration_status=calibration.calibration_status,
        base_severity=base_severity,
        likelihood_factor=round(likelihood_factor, 4),
        data_factor=round(data_factor, 4),
        confidence_factor=round(confidence_factor, 4),
        remediation_factor=round(remediation_factor, 4),
        raw_score=round(raw_score, 4),
        normalized_score=round(normalized_score, 2),
    )

    return ScoredFinding(
        finding=finding,
        score=round(normalized_score, 2),
        priority=_priority_from_score(normalized_score),
        breakdown=breakdown,
    )


def _aggregate_category_scores(scored_findings: list[ScoredFinding]) -> dict[str, float]:
    """Average risk scores by category across non-compliant findings."""
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
    """Apply fixed category weights to produce the overall risk score."""
    weighted_total = 0.0

    for category, weight in CATEGORY_WEIGHTS.items():
        weighted_total += category_scores.get(category.value, 0.0) * weight

    return weighted_total


def _priority_from_score(score: float) -> str:
    """Convert a numeric score into a practical response priority."""
    if score >= 75:
        return "Immediate"
    if score >= 50:
        return "High"
    if score >= 25:
        return "Planned"
    return "Monitor"
