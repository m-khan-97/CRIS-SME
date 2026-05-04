# Tests for artifact assurance scoring that stays separate from risk scoring.
from cris_sme.engine.assessment_assurance import build_assessment_assurance


def test_assessment_assurance_scores_complete_artifact() -> None:
    report = {
        "assessment_replay": {
            "replay": {
                "replayable": True,
                "deterministic_match": True,
            }
        },
        "risk_bill_of_materials": {
            "canonical_report_sha256": "a" * 64,
            "artifacts": [{"path": "outputs/reports/example.json"}],
            "evidence_sufficiency_counts": {"sufficient": 8, "partial": 2},
        },
        "provider_contract_conformance": {
            "passed": True,
            "failed_contract_count": 0,
        },
        "decision_ledger": {"event_count": 3},
        "collector_coverage": [{"provider": "azure"}],
    }

    assurance = build_assessment_assurance(report)

    assert assurance.assurance_score >= 90
    assert assurance.assurance_level == "high"
    assert "No impact" in assurance.risk_score_impact
    assert len(assurance.gaps) == 0


def test_assessment_assurance_separates_low_assurance_from_risk_score() -> None:
    report = {
        "overall_risk_score": 12.0,
        "assessment_replay": {"replay": {"replayable": False}},
        "provider_contract_conformance": {
            "passed": False,
            "failed_contract_count": 4,
        },
        "collector_coverage": [],
    }

    assurance = build_assessment_assurance(report)

    assert assurance.assurance_score < 50
    assert assurance.assurance_level in {"low", "limited"}
    assert "never changes deterministic CRIS-SME risk scores" in assurance.risk_score_impact
    assert assurance.gaps
