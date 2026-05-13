# Tests for the longitudinal risk drift analysis engine.
from __future__ import annotations

from cris_sme.reporting.history import build_risk_drift_analysis


def _make_report(
    *,
    overall_risk_score: float,
    generated_at: str,
    collector_mode: str = "mock",
    iam_score: float = 30.0,
    network_score: float = 40.0,
) -> dict:
    return {
        "overall_risk_score": overall_risk_score,
        "generated_at": generated_at,
        "collector_mode": collector_mode,
        "category_scores": {
            "IAM": iam_score,
            "Network": network_score,
        },
        "evaluation_context": {"non_compliant_findings": 10},
        "prioritized_risks": [
            {"control_id": "IAM-001", "score": 70.0, "priority": "High"},
            {"control_id": "NET-001", "score": 60.0, "priority": "High"},
        ],
    }


def test_drift_analysis_returns_insufficient_for_fewer_than_three_runs() -> None:
    result = build_risk_drift_analysis([])
    assert result["status"] == "insufficient_history"
    assert result["available_runs"] == 0

    result = build_risk_drift_analysis([_make_report(overall_risk_score=40.0, generated_at="2026-01-01T00:00:00Z")])
    assert result["status"] == "insufficient_history"
    assert result["available_runs"] == 1

    result = build_risk_drift_analysis([
        _make_report(overall_risk_score=40.0, generated_at="2026-01-01T00:00:00Z"),
        _make_report(overall_risk_score=42.0, generated_at="2026-01-08T00:00:00Z"),
    ])
    assert result["status"] == "insufficient_history"
    assert result["available_runs"] == 2


def test_drift_analysis_detects_worsening_trend() -> None:
    reports = [
        _make_report(overall_risk_score=30.0, generated_at="2026-01-01T00:00:00Z"),
        _make_report(overall_risk_score=40.0, generated_at="2026-01-08T00:00:00Z"),
        _make_report(overall_risk_score=50.0, generated_at="2026-01-15T00:00:00Z"),
        _make_report(overall_risk_score=60.0, generated_at="2026-01-22T00:00:00Z"),
    ]
    result = build_risk_drift_analysis(reports)

    assert result["status"] == "available"
    assert result["run_count"] == 4
    assert result["overall_risk"]["slope_per_run"] > 0
    assert result["overall_risk"]["velocity_per_week"] > 0
    assert result["overall_risk"]["direction"] in {"worsening", "rapidly_worsening"}
    assert result["overall_risk"]["change_total"] == pytest.approx(30.0, abs=0.1)


def test_drift_analysis_detects_improving_trend() -> None:
    reports = [
        _make_report(overall_risk_score=60.0, generated_at="2026-01-01T00:00:00Z"),
        _make_report(overall_risk_score=50.0, generated_at="2026-01-08T00:00:00Z"),
        _make_report(overall_risk_score=40.0, generated_at="2026-01-15T00:00:00Z"),
    ]
    result = build_risk_drift_analysis(reports)

    assert result["status"] == "available"
    assert result["overall_risk"]["slope_per_run"] < 0
    assert result["overall_risk"]["direction"] in {"improving", "rapidly_improving"}
    assert result["overall_risk"]["change_total"] < 0


def test_drift_analysis_computes_category_slopes() -> None:
    reports = [
        _make_report(overall_risk_score=40.0, generated_at="2026-01-01T00:00:00Z", iam_score=20.0, network_score=60.0),
        _make_report(overall_risk_score=45.0, generated_at="2026-01-08T00:00:00Z", iam_score=30.0, network_score=50.0),
        _make_report(overall_risk_score=50.0, generated_at="2026-01-15T00:00:00Z", iam_score=40.0, network_score=40.0),
    ]
    result = build_risk_drift_analysis(reports)

    assert result["status"] == "available"
    assert "IAM" in result["category_drift"]
    assert "Network" in result["category_drift"]
    assert result["category_drift"]["IAM"]["slope_per_run"] > 0
    assert result["category_drift"]["Network"]["slope_per_run"] < 0
    assert result["fastest_deteriorating_category"] == "IAM"


def test_drift_analysis_builds_control_stability_index() -> None:
    always_failing_report = {
        "overall_risk_score": 40.0,
        "generated_at": "2026-01-01T00:00:00Z",
        "collector_mode": "mock",
        "category_scores": {"IAM": 40.0},
        "evaluation_context": {},
        "prioritized_risks": [
            {"control_id": "IAM-001", "score": 70.0, "priority": "High"},
            {"control_id": "NET-001", "score": 50.0, "priority": "High"},
        ],
    }
    sometimes_failing_report = {
        "overall_risk_score": 35.0,
        "generated_at": "2026-01-08T00:00:00Z",
        "collector_mode": "mock",
        "category_scores": {"IAM": 35.0},
        "evaluation_context": {},
        "prioritized_risks": [
            {"control_id": "IAM-001", "score": 65.0, "priority": "High"},
        ],
    }
    clean_report = {
        "overall_risk_score": 30.0,
        "generated_at": "2026-01-15T00:00:00Z",
        "collector_mode": "mock",
        "category_scores": {"IAM": 30.0},
        "evaluation_context": {},
        "prioritized_risks": [
            {"control_id": "IAM-001", "score": 60.0, "priority": "High"},
        ],
    }
    result = build_risk_drift_analysis([always_failing_report, sometimes_failing_report, clean_report])

    stability = {item["control_id"]: item for item in result["control_stability"]}
    assert "IAM-001" in stability
    assert stability["IAM-001"]["stability_index"] == 1.0
    assert stability["IAM-001"]["persistence_label"] == "persistent"
    assert "NET-001" in stability
    assert stability["NET-001"]["stability_index"] == pytest.approx(1 / 3, abs=0.01)
    assert stability["NET-001"]["persistence_label"] == "occasional"
    assert result["persistent_control_count"] == 1
    assert "IAM-001" in result["persistent_controls"]


def test_drift_analysis_stable_scores_produce_stable_direction() -> None:
    reports = [
        _make_report(overall_risk_score=40.0, generated_at=f"2026-01-0{i+1}T00:00:00Z")
        for i in range(4)
    ]
    result = build_risk_drift_analysis(reports)
    assert result["status"] == "available"
    assert result["overall_risk"]["direction"] == "stable"
    assert abs(result["overall_risk"]["velocity_per_week"]) < 0.3


import pytest
