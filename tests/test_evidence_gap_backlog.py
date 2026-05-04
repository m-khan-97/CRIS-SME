# Tests for evidence gap backlog generation.
from cris_sme.engine.evidence_gap_backlog import build_evidence_gap_backlog


def test_evidence_gap_backlog_extracts_finding_and_provider_gaps() -> None:
    report = {
        "prioritized_risks": [
            {
                "finding_id": "fdg_123456",
                "control_id": "IAM-001",
                "title": "Privileged accounts lack MFA",
                "provider": "azure",
                "category": "IAM",
                "score": 72.0,
                "evidence_quality": {
                    "sufficiency": "partial",
                    "missing_requirements": ["privileged assignment inventory"],
                    "provider_support": "active",
                },
            }
        ],
        "provider_evidence_contracts": {
            "contracts": [
                {
                    "provider": "aws",
                    "control_id": "IAM-001",
                    "domain": "IAM",
                    "support_status": "planned",
                    "evidence_requirements": ["iam role inventory"],
                    "activation_gate": (
                        "aws support can be activated only after collector evidence, "
                        "adapter routing, tests, and documented limitations are present."
                    ),
                }
            ]
        },
    }

    backlog = build_evidence_gap_backlog(report)

    assert backlog.item_count == 2
    assert backlog.high_priority_count == 1
    assert backlog.provider_counts == {"azure": 1, "aws": 1}
    assert backlog.domain_counts == {"IAM": 2}
    assert backlog.items[0].gap_type == "finding_evidence_gap"
    assert backlog.items[0].priority == "high"
    assert backlog.items[1].gap_type == "provider_activation_gap"


def test_evidence_gap_backlog_ignores_sufficient_current_findings() -> None:
    report = {
        "prioritized_risks": [
            {
                "finding_id": "fdg_123456",
                "control_id": "NET-001",
                "title": "Administrative port exposed",
                "provider": "azure",
                "category": "Network",
                "score": 80.0,
                "evidence_quality": {
                    "sufficiency": "sufficient",
                    "missing_requirements": [],
                    "provider_support": "active",
                },
            }
        ],
        "provider_evidence_contracts": {"contracts": []},
    }

    backlog = build_evidence_gap_backlog(report)

    assert backlog.item_count == 0
    assert backlog.high_priority_count == 0
