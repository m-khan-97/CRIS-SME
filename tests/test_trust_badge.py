# Tests for report trust badge generation.
from cris_sme.engine.trust_badge import build_report_trust_badge


def test_report_trust_badge_marks_verified_report() -> None:
    badge = build_report_trust_badge(
        {
            "assessment_assurance": {"assurance_score": 92.0},
            "assessment_replay": {"replay": {"deterministic_match": True}},
            "risk_bill_of_materials": {"canonical_report_sha256": "a" * 64},
            "provider_contract_conformance": {"passed": True},
            "evidence_gap_backlog": {"high_priority_count": 0},
        }
    )

    assert badge.level == "verified"
    assert badge.replay_verified is True
    assert badge.rbom_present is True
    assert badge.provider_conformance_passed is True
    assert badge.caveats == []
    assert "never changes deterministic CRIS-SME risk scores" in badge.risk_score_impact


def test_report_trust_badge_preserves_caveats() -> None:
    badge = build_report_trust_badge(
        {
            "assessment_assurance": {"assurance_score": 70.0},
            "assessment_replay": {"replay": {"deterministic_match": True}},
            "risk_bill_of_materials": {"canonical_report_sha256": "a" * 64},
            "provider_contract_conformance": {"passed": False},
            "evidence_gap_backlog": {"high_priority_count": 2},
        }
    )

    assert badge.level == "assured"
    assert badge.provider_conformance_passed is False
    assert len(badge.caveats) == 2
