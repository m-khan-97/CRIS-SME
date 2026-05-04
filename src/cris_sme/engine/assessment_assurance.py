# Assessment artifact assurance scoring that never changes deterministic risk scores.
from __future__ import annotations

from typing import Any

from cris_sme.models.platform import (
    AssessmentAssuranceResult,
    AssessmentAssuranceSignal,
)


def build_assessment_assurance(report: dict[str, Any]) -> AssessmentAssuranceResult:
    """Score the trustworthiness of an assessment artifact separately from risk."""
    signals = [
        _replay_signal(report),
        _rbom_signal(report),
        _provider_conformance_signal(report),
        _evidence_sufficiency_signal(report),
        _decision_ledger_signal(report),
        _collector_coverage_signal(report),
    ]
    assurance_score = round(
        sum(signal.score * signal.weight for signal in signals)
        / sum(signal.weight for signal in signals),
        2,
    )
    strengths = [
        signal.label
        for signal in signals
        if signal.passed
    ]
    gaps = [
        signal.explanation
        for signal in signals
        if not signal.passed
    ]
    return AssessmentAssuranceResult(
        assurance_score=assurance_score,
        assurance_level=_assurance_level(assurance_score),
        risk_score_impact=(
            "No impact. Assessment assurance grades artifact trustworthiness and "
            "never changes deterministic CRIS-SME risk scores."
        ),
        signals=signals,
        strengths=strengths,
        gaps=gaps,
    )


def _replay_signal(report: dict[str, Any]) -> AssessmentAssuranceSignal:
    replay = _nested_dict(report, "assessment_replay", "replay")
    passed = bool(replay.get("replayable")) and bool(replay.get("deterministic_match"))
    return AssessmentAssuranceSignal(
        signal_id="replay",
        label="Deterministic replay",
        score=100.0 if passed else 25.0 if replay else 0.0,
        weight=0.25,
        passed=passed,
        explanation=(
            "Evidence snapshot replay matched deterministic findings and scores."
            if passed
            else "Evidence snapshot replay is missing or did not match deterministically."
        ),
    )


def _rbom_signal(report: dict[str, Any]) -> AssessmentAssuranceSignal:
    rbom = report.get("risk_bill_of_materials")
    artifacts = rbom.get("artifacts", []) if isinstance(rbom, dict) else []
    passed = isinstance(rbom, dict) and bool(rbom.get("canonical_report_sha256")) and bool(artifacts)
    return AssessmentAssuranceSignal(
        signal_id="rbom",
        label="Risk Bill of Materials",
        score=100.0 if passed else 0.0,
        weight=0.20,
        passed=passed,
        explanation=(
            "RBOM hashes report and downstream artifacts."
            if passed
            else "RBOM is missing or incomplete."
        ),
    )


def _provider_conformance_signal(report: dict[str, Any]) -> AssessmentAssuranceSignal:
    conformance = report.get("provider_contract_conformance")
    failed = int(conformance.get("failed_contract_count", 0)) if isinstance(conformance, dict) else 1
    passed = isinstance(conformance, dict) and bool(conformance.get("passed")) and failed == 0
    return AssessmentAssuranceSignal(
        signal_id="provider_conformance",
        label="Provider contract conformance",
        score=100.0 if passed else max(0.0, 100.0 - (failed * 10.0)),
        weight=0.15,
        passed=passed,
        explanation=(
            "Provider support claims match implementation signals."
            if passed
            else "Provider support claims have conformance gaps."
        ),
    )


def _evidence_sufficiency_signal(report: dict[str, Any]) -> AssessmentAssuranceSignal:
    counts = _nested_dict(report, "evidence_sufficiency", "counts")
    if not counts:
        counts = _nested_dict(report, "risk_bill_of_materials", "evidence_sufficiency_counts")
    total = sum(int(value) for value in counts.values()) if counts else 0
    sufficient = int(counts.get("sufficient", 0)) if counts else 0
    partial = int(counts.get("partial", 0)) if counts else 0
    weighted_ratio = ((sufficient * 1.0) + (partial * 0.55)) / total if total else 0.0
    score = round(weighted_ratio * 100, 2)
    passed = score >= 60.0
    return AssessmentAssuranceSignal(
        signal_id="evidence_sufficiency",
        label="Evidence sufficiency",
        score=score,
        weight=0.20,
        passed=passed,
        explanation=(
            "Evidence sufficiency is strong enough for assessment assurance."
            if passed
            else "Evidence sufficiency is low; findings may be explainable but less assured."
        ),
    )


def _decision_ledger_signal(report: dict[str, Any]) -> AssessmentAssuranceSignal:
    ledger = report.get("decision_ledger")
    event_count = int(ledger.get("event_count", 0)) if isinstance(ledger, dict) else 0
    passed = event_count > 0
    return AssessmentAssuranceSignal(
        signal_id="decision_ledger",
        label="Decision Ledger",
        score=100.0 if passed else 0.0,
        weight=0.10,
        passed=passed,
        explanation=(
            "Decision Ledger records assessment and finding events."
            if passed
            else "Decision Ledger events are missing."
        ),
    )


def _collector_coverage_signal(report: dict[str, Any]) -> AssessmentAssuranceSignal:
    coverage = report.get("collector_coverage", [])
    passed = isinstance(coverage, list) and bool(coverage)
    score = 100.0 if passed else 0.0
    return AssessmentAssuranceSignal(
        signal_id="collector_coverage",
        label="Collector coverage",
        score=score,
        weight=0.10,
        passed=passed,
        explanation=(
            "Collector coverage and observability boundaries are present."
            if passed
            else "Collector coverage metadata is missing."
        ),
    )


def _assurance_level(score: float) -> str:
    if score >= 85.0:
        return "high"
    if score >= 65.0:
        return "medium"
    if score >= 40.0:
        return "limited"
    return "low"


def _nested_dict(payload: dict[str, Any], *keys: str) -> dict[str, Any]:
    current: object = payload
    for key in keys:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return current if isinstance(current, dict) else {}
