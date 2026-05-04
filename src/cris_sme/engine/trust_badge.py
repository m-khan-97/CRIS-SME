# Stakeholder-facing report trust badge generation.
from __future__ import annotations

from typing import Any

from cris_sme.models.platform import ReportTrustBadge


def build_report_trust_badge(report: dict[str, Any]) -> ReportTrustBadge:
    """Build a compact trust badge from assurance, replay, RBOM, and conformance signals."""
    assurance = report.get("assessment_assurance", {})
    if not isinstance(assurance, dict):
        assurance = {}
    replay = report.get("assessment_replay", {})
    replay_result = replay.get("replay", {}) if isinstance(replay, dict) else {}
    if not isinstance(replay_result, dict):
        replay_result = {}
    conformance = report.get("provider_contract_conformance", {})
    if not isinstance(conformance, dict):
        conformance = {}
    backlog = report.get("evidence_gap_backlog", {})
    if not isinstance(backlog, dict):
        backlog = {}

    assurance_score = _safe_float(assurance.get("assurance_score"))
    replay_verified = bool(replay_result.get("deterministic_match"))
    rbom_present = isinstance(report.get("risk_bill_of_materials"), dict)
    provider_conformance_passed = bool(conformance.get("passed"))
    high_priority_evidence_gaps = int(backlog.get("high_priority_count", 0))
    level = _level(
        assurance_score=assurance_score,
        replay_verified=replay_verified,
        rbom_present=rbom_present,
        provider_conformance_passed=provider_conformance_passed,
        high_priority_evidence_gaps=high_priority_evidence_gaps,
    )
    caveats = _caveats(
        replay_verified=replay_verified,
        rbom_present=rbom_present,
        provider_conformance_passed=provider_conformance_passed,
        high_priority_evidence_gaps=high_priority_evidence_gaps,
    )
    return ReportTrustBadge(
        label=f"CRIS-SME {level.title()} Assurance",
        level=level,
        assurance_score=round(assurance_score, 2),
        replay_verified=replay_verified,
        rbom_present=rbom_present,
        provider_conformance_passed=provider_conformance_passed,
        high_priority_evidence_gaps=high_priority_evidence_gaps,
        statement=_statement(level),
        caveats=caveats,
        risk_score_impact=(
            "No impact. The trust badge summarizes report assurance signals and "
            "never changes deterministic CRIS-SME risk scores."
        ),
    )


def _level(
    *,
    assurance_score: float,
    replay_verified: bool,
    rbom_present: bool,
    provider_conformance_passed: bool,
    high_priority_evidence_gaps: int,
) -> str:
    if (
        assurance_score >= 85
        and replay_verified
        and rbom_present
        and provider_conformance_passed
        and high_priority_evidence_gaps == 0
    ):
        return "verified"
    if assurance_score >= 65 and replay_verified and rbom_present:
        return "assured"
    if assurance_score >= 40:
        return "limited"
    return "unverified"


def _statement(level: str) -> str:
    statements = {
        "verified": "Report integrity, deterministic replay, and provider support claims are verified for this assessment artifact.",
        "assured": "Core report assurance signals are present, with caveats recorded for review.",
        "limited": "Report is explainable but has assurance gaps that should be reviewed before external reliance.",
        "unverified": "Report assurance signals are incomplete or unavailable.",
    }
    return statements[level]


def _caveats(
    *,
    replay_verified: bool,
    rbom_present: bool,
    provider_conformance_passed: bool,
    high_priority_evidence_gaps: int,
) -> list[str]:
    caveats: list[str] = []
    if not replay_verified:
        caveats.append("Deterministic replay is not verified.")
    if not rbom_present:
        caveats.append("Risk Bill of Materials is not present.")
    if not provider_conformance_passed:
        caveats.append("Provider contract conformance is not passing.")
    if high_priority_evidence_gaps:
        caveats.append(f"{high_priority_evidence_gaps} high-priority evidence gaps remain.")
    return caveats


def _safe_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
