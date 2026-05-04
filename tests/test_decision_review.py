# Tests for governance decision review queue generation.
from cris_sme.engine.decision_review import build_decision_review_queue


def test_decision_review_queue_creates_remediation_and_evidence_items() -> None:
    report = {
        "prioritized_risks": [
            {
                "finding_id": "fdg_1",
                "control_id": "NET-001",
                "title": "Admin port exposed",
                "provider": "azure",
                "category": "Network",
                "score": 80.0,
                "priority": "Immediate",
                "evidence_quality": {"sufficiency": "sufficient"},
                "lifecycle": {"status": "open"},
            },
            {
                "finding_id": "fdg_2",
                "control_id": "IAM-001",
                "title": "Privileged account evidence partial",
                "provider": "azure",
                "category": "IAM",
                "score": 60.0,
                "priority": "High",
                "evidence_quality": {"sufficiency": "partial"},
                "lifecycle": {"status": "open"},
            },
        ],
        "evidence_gap_backlog": {
            "items": [
                {
                    "gap_id": "egap_1",
                    "priority": "medium",
                    "control_id": "IAM-001",
                    "linked_finding_id": "fdg_2",
                    "title": "Privileged account evidence partial",
                    "provider": "azure",
                    "recommended_action": "Enrich IAM collector evidence.",
                    "assurance_impact": "medium",
                }
            ]
        },
    }

    queue = build_decision_review_queue(report)

    assert queue.item_count == 3
    assert queue.decision_type_counts["remediation_decision"] == 1
    assert queue.decision_type_counts["evidence_review"] == 1
    assert queue.decision_type_counts["evidence_investigation"] == 1
    assert queue.priority_counts["high"] == 2


def test_decision_review_queue_creates_exception_review() -> None:
    queue = build_decision_review_queue(
        {
            "prioritized_risks": [
                {
                    "finding_id": "fdg_1",
                    "control_id": "DATA-001",
                    "title": "Public storage accepted risk",
                    "provider": "azure",
                    "category": "Data",
                    "score": 30.0,
                    "priority": "Planned",
                    "evidence_quality": {"sufficiency": "sufficient"},
                    "lifecycle": {"status": "accepted_risk"},
                }
            ]
        }
    )

    assert queue.item_count == 1
    assert queue.items[0].decision_type == "exception_review"
    assert queue.items[0].owner_hint == "data"
