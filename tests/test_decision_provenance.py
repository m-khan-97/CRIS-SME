# Tests for decision provenance graph generation.
from cris_sme.engine.decision_provenance import build_decision_provenance_graph


def test_decision_provenance_graph_links_core_decision_path() -> None:
    report = {
        "evidence_snapshot": {
            "snapshot_id": "evs_1234567890",
            "collector_mode": "mock",
            "policy_pack_version": "2026.04.0",
            "profile_sha256": "a" * 64,
            "finding_sha256": "b" * 64,
        },
        "run_metadata": {
            "policy_pack": {"policy_pack_version": "2026.04.0"},
        },
        "provider_evidence_contracts": {
            "contracts": [
                {
                    "contract_id": "pec_azure_net-001_1.0.0",
                    "provider": "azure",
                    "control_id": "NET-001",
                    "support_status": "active",
                    "freshness_hours": 24,
                }
            ]
        },
        "prioritized_risks": [
            {
                "finding_id": "fdg_123456",
                "control_id": "NET-001",
                "rule_version": "1.0.0",
                "title": "Administrative services exposed",
                "provider": "azure",
                "category": "Network",
                "priority": "High",
                "score": 60.0,
                "resource_scope": "Tenant root",
                "evidence_quality": {"sufficiency": "sufficient"},
            }
        ],
        "decision_review_queue": {
            "items": [
                {
                    "review_id": "drv_123456",
                    "finding_id": "fdg_123456",
                    "decision_type": "remediation_decision",
                    "priority": "high",
                    "owner_hint": "network",
                    "recommended_decision": "Approve remediation plan",
                    "rationale": "High priority risk requires review.",
                }
            ]
        },
        "assessment_replay": {
            "replay": {
                "snapshot_id": "evs_1234567890",
                "replayable": True,
                "deterministic_match": True,
                "overall_risk_delta": 0,
            }
        },
        "assessment_assurance": {
            "assurance_score": 90,
            "assurance_level": "high",
            "risk_score_impact": "No impact.",
        },
        "risk_bill_of_materials": {
            "run_id": "run_123456",
            "canonical_report_sha256": "c" * 64,
            "integrity_algorithm": "sha256",
        },
        "report_trust_badge": {
            "label": "CRIS-SME Verified Assurance",
            "level": "verified",
            "assurance_score": 90,
            "risk_score_impact": "No impact.",
        },
        "control_drift_attribution": {
            "comparable": True,
            "primary_attribution": "evidence_drift",
            "overall_risk_delta": 10,
        },
    }

    graph = build_decision_provenance_graph(report)

    assert graph.graph_model == "cris_sme_decision_provenance_graph_v1"
    assert graph.node_count >= 12
    assert graph.edge_count >= 10
    assert graph.path_count == 1
    assert graph.node_type_counts["finding"] == 1
    assert graph.node_type_counts["decision_review_item"] == 1
    assert graph.edge_type_counts["produces_finding"] == 1
    assert "finding:fdg_123456" in graph.top_decision_paths[0].node_ids


def test_decision_provenance_graph_handles_missing_review_item() -> None:
    graph = build_decision_provenance_graph(
        {
            "evidence_snapshot": {"snapshot_id": "evs_1234567890"},
            "prioritized_risks": [
                {
                    "finding_id": "fdg_123456",
                    "control_id": "IAM-001",
                    "title": "MFA missing",
                    "provider": "azure",
                    "score": 40,
                    "priority": "Planned",
                    "evidence_quality": {"sufficiency": "partial"},
                }
            ],
        }
    )

    assert graph.path_count == 1
    assert "decision_review_item" not in graph.node_type_counts
