# Tests for Assurance Case generation.
from cris_sme.engine.assurance_case import build_assurance_case


def test_assurance_case_builds_structured_arguments_from_claims() -> None:
    report = {
        "generated_at": "2026-05-04T00:00:00Z",
        "assessment_assurance": {
            "assurance_score": 88.0,
            "gaps": [],
        },
        "evidence_snapshot": {"snapshot_id": "evs_123456"},
        "evidence_gap_backlog": {"high_priority_count": 0},
        "claim_verification_pack": {
            "claims": [
                {
                    "claim_id": "clm_replay",
                    "claim_type": "replay",
                    "verification_status": "verified",
                    "confidence": 1.0,
                    "evidence_refs": [],
                    "provenance_node_ids": ["replay:assessment"],
                    "rbom_artifact_refs": ["evidence_snapshot"],
                    "caveats": [],
                },
                {
                    "claim_id": "clm_integrity",
                    "claim_type": "integrity",
                    "verification_status": "verified",
                    "confidence": 1.0,
                    "evidence_refs": [],
                    "provenance_node_ids": ["rbom:assessment"],
                    "rbom_artifact_refs": ["risk_bill_of_materials"],
                    "caveats": [],
                },
                {
                    "claim_id": "clm_overall",
                    "claim_type": "overall_risk",
                    "verification_status": "verified",
                    "confidence": 0.95,
                    "evidence_refs": ["evidence:fdg_1:1"],
                    "provenance_node_ids": ["assurance:assessment"],
                    "rbom_artifact_refs": ["json_report"],
                    "caveats": [],
                },
                {
                    "claim_id": "clm_top",
                    "claim_type": "top_risk",
                    "verification_status": "verified",
                    "confidence": 0.9,
                    "evidence_refs": ["evidence:fdg_1:1"],
                    "provenance_node_ids": ["finding:fdg_1"],
                    "rbom_artifact_refs": ["decision_provenance_graph"],
                    "caveats": [],
                },
                {
                    "claim_id": "clm_badge",
                    "claim_type": "trust_badge",
                    "verification_status": "verified",
                    "confidence": 0.88,
                    "evidence_refs": [],
                    "provenance_node_ids": ["trust_badge:report"],
                    "rbom_artifact_refs": ["json_report"],
                    "caveats": [],
                },
                {
                    "claim_id": "clm_ce",
                    "claim_type": "cyber_essentials_readiness",
                    "verification_status": "verified",
                    "confidence": 0.8,
                    "evidence_refs": [],
                    "provenance_node_ids": ["control:NET-001"],
                    "rbom_artifact_refs": ["json_report"],
                    "caveats": [],
                },
                {
                    "claim_id": "clm_ins",
                    "claim_type": "insurance_question",
                    "verification_status": "verified",
                    "confidence": 0.8,
                    "evidence_refs": [],
                    "provenance_node_ids": ["control:NET-001"],
                    "rbom_artifact_refs": ["cyber_insurance_pack.cyber_insurance_json"],
                    "caveats": [],
                },
            ]
        },
    }

    case = build_assurance_case(report)

    assert case.argument_count == 4
    assert case.supported_argument_count == 4
    assert case.caveated_argument_count == 0
    assert case.overall_conclusion == "supported"
    assert case.deterministic_score_impact.startswith("No impact")
    assert case.arguments[0].supporting_claim_ids == ["clm_replay", "clm_integrity"]


def test_assurance_case_surfaces_caveats_and_residual_gaps() -> None:
    report = {
        "assessment_assurance": {
            "assurance_score": 60.0,
            "gaps": ["Evidence sufficiency is low."],
        },
        "evidence_snapshot": {"snapshot_id": "evs_123456"},
        "evidence_gap_backlog": {"high_priority_count": 2},
        "claim_verification_pack": {
            "claims": [
                {
                    "claim_id": "clm_replay",
                    "claim_type": "replay",
                    "verification_status": "verified",
                    "confidence": 1.0,
                    "caveats": [],
                    "evidence_refs": [],
                    "provenance_node_ids": [],
                    "rbom_artifact_refs": [],
                }
            ]
        },
    }

    case = build_assurance_case(report)

    assert case.overall_conclusion in {"limited", "caveated"}
    assert case.open_caveats
    assert case.residual_gaps
    assert any(argument.conclusion == "unsupported" for argument in case.arguments)
