# Tests for control drift attribution.
from cris_sme.engine.control_drift import build_control_drift_attribution


def test_control_drift_attribution_classifies_evidence_drift() -> None:
    previous = {
        "generated_at": "2026-05-03T00:00:00Z",
        "collector_mode": "mock",
        "overall_risk_score": 20.0,
        "evidence_snapshot": {
            "profile_sha256": "a" * 64,
            "finding_sha256": "b" * 64,
            "policy_pack_version": "2026.04.0",
        },
        "prioritized_risks": [
            {
                "control_id": "NET-001",
                "title": "Administrative services exposed",
                "category": "Network",
                "score": 40.0,
                "priority": "Planned",
            }
        ],
        "finding_lifecycle_summary": {
            "status_counts": {"open": 1},
            "exception_applied_count": 0,
        },
    }
    current = {
        "generated_at": "2026-05-04T00:00:00Z",
        "collector_mode": "mock",
        "overall_risk_score": 30.0,
        "evidence_snapshot": {
            "profile_sha256": "c" * 64,
            "finding_sha256": "d" * 64,
            "policy_pack_version": "2026.04.0",
        },
        "prioritized_risks": [
            {
                "control_id": "NET-001",
                "title": "Administrative services exposed",
                "category": "Network",
                "score": 60.0,
                "priority": "High",
            }
        ],
        "finding_lifecycle_summary": {
            "status_counts": {"open": 1},
            "exception_applied_count": 0,
        },
    }

    attribution = build_control_drift_attribution(current, previous)

    assert attribution.comparable is True
    assert attribution.evidence_changed is True
    assert attribution.policy_pack_changed is False
    assert attribution.primary_attribution == "evidence_drift"
    assert attribution.items[0].delta == 20.0
    assert attribution.items[0].direction == "worse"


def test_control_drift_attribution_classifies_policy_drift() -> None:
    previous = {
        "generated_at": "2026-05-03T00:00:00Z",
        "collector_mode": "mock",
        "overall_risk_score": 20.0,
        "evidence_snapshot": {
            "profile_sha256": "a" * 64,
            "finding_sha256": "b" * 64,
            "policy_pack_version": "2026.04.0",
        },
        "prioritized_risks": [{"control_id": "IAM-001", "score": 20.0}],
    }
    current = {
        "generated_at": "2026-05-04T00:00:00Z",
        "collector_mode": "mock",
        "overall_risk_score": 25.0,
        "evidence_snapshot": {
            "profile_sha256": "a" * 64,
            "finding_sha256": "b" * 64,
            "policy_pack_version": "2026.05.0",
        },
        "prioritized_risks": [{"control_id": "IAM-001", "score": 30.0}],
    }

    attribution = build_control_drift_attribution(current, previous)

    assert attribution.policy_pack_changed is True
    assert attribution.evidence_changed is False
    assert attribution.primary_attribution == "policy_drift"
    assert attribution.items[0].attribution == "policy_drift"


def test_control_drift_attribution_handles_baseline() -> None:
    attribution = build_control_drift_attribution(
        {"generated_at": "2026-05-04T00:00:00Z"},
        None,
    )

    assert attribution.comparable is False
    assert attribution.primary_attribution == "baseline"
    assert attribution.items == []
