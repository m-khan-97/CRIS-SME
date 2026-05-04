# Tests for Claim Verification Pack generation.
from cris_sme.engine.claim_verification import build_claim_verification_pack


def test_claim_verification_pack_links_core_claims_to_evidence() -> None:
    report = {
        "generated_at": "2026-05-04T00:00:00Z",
        "overall_risk_score": 42.0,
        "report_trust_badge": {
            "level": "verified",
            "statement": "Report integrity is verified.",
            "assurance_score": 90,
            "risk_score_impact": "No impact.",
            "caveats": [],
        },
        "assessment_replay": {
            "replay": {
                "snapshot_id": "evs_123456",
                "deterministic_match": True,
            }
        },
        "evidence_snapshot": {"snapshot_id": "evs_123456"},
        "risk_bill_of_materials": {"canonical_report_sha256": "a" * 64},
        "prioritized_risks": [
            {
                "finding_id": "fdg_123456",
                "control_id": "NET-001",
                "priority": "High",
                "score": 60.0,
                "evidence_quality": {"sufficiency": "sufficient"},
                "finding_trace": {"evidence_refs": ["evidence:fdg_123456:1"]},
                "confidence_calibration": {"calibrated_confidence": 0.9},
            }
        ],
        "cyber_essentials_readiness": {
            "overall_readiness_score": 80.0,
            "pillars": [
                {
                    "pillar_id": "firewalls",
                    "pillar_name": "Firewalls",
                    "status": "partial",
                    "active_control_ids": ["NET-001"],
                }
            ],
        },
        "cyber_insurance_evidence": {
            "questions": [
                {
                    "question_id": "INS-003",
                    "status": "partial",
                    "evidence_statement": "Administrative access is partially restricted.",
                    "related_controls": ["NET-001"],
                    "recommended_next_step": "Restrict administrative exposure.",
                    "supporting_findings": [
                        {
                            "control_id": "NET-001",
                            "evidence": ["RDP exposed"],
                        }
                    ],
                }
            ]
        },
    }

    pack = build_claim_verification_pack(report)

    assert pack.claim_count >= 7
    assert pack.verified_claim_count >= 3
    assert pack.caveated_claim_count >= 2
    assert pack.claim_type_counts["overall_risk"] == 1
    assert pack.claim_type_counts["top_risk"] == 1
    assert pack.claim_type_counts["insurance_question"] == 1
    top_risk = next(claim for claim in pack.claims if claim.claim_type == "top_risk")
    assert top_risk.evidence_refs == ["evidence:fdg_123456:1"]
    assert top_risk.provenance_node_ids == [
        "finding:fdg_123456",
        "score:fdg_123456",
        "evidence_sufficiency:fdg_123456",
    ]


def test_claim_verification_pack_caveats_unverified_replay_and_missing_rbom() -> None:
    pack = build_claim_verification_pack(
        {
            "overall_risk_score": 10.0,
            "assessment_replay": {"replay": {"deterministic_match": False}},
            "prioritized_risks": [],
        }
    )

    replay_claim = next(claim for claim in pack.claims if claim.claim_type == "replay")
    rbom_claim = next(claim for claim in pack.claims if claim.claim_type == "integrity")

    assert replay_claim.verification_status == "caveated"
    assert rbom_claim.verification_status == "unverified"
    assert rbom_claim.caveats
