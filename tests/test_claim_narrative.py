# Tests for deterministic claim-bound narrative generation.
from cris_sme.engine.claim_narrative import (
    build_claim_bound_narrative,
    build_claim_bound_narrative_markdown,
)


def test_claim_bound_narrative_cites_claim_ids_and_caveats() -> None:
    report = {
        "generated_at": "2026-05-04T00:00:00Z",
        "claim_verification_pack": {
            "claims": [
                {
                    "claim_id": "clm_overall",
                    "claim_type": "overall_risk",
                    "statement": "Overall risk score is 42/100.",
                    "verification_status": "verified",
                    "caveats": [],
                },
                {
                    "claim_id": "clm_badge",
                    "claim_type": "trust_badge",
                    "statement": "Report assurance is caveated.",
                    "verification_status": "caveated",
                    "caveats": ["Evidence gap remains."],
                },
                {
                    "claim_id": "clm_replay",
                    "claim_type": "replay",
                    "statement": "Replay verified deterministic score.",
                    "verification_status": "verified",
                    "caveats": [],
                },
                {
                    "claim_id": "clm_integrity",
                    "claim_type": "integrity",
                    "statement": "RBOM is present.",
                    "verification_status": "verified",
                    "caveats": [],
                },
            ]
        },
    }

    narrative = build_claim_bound_narrative(report)
    markdown = build_claim_bound_narrative_markdown(narrative)

    assert narrative.section_count == 2
    assert narrative.cited_claim_count == 4
    assert "clm_overall" in narrative.sections[0].cited_claim_ids
    assert "Evidence gap remains." in narrative.sections[0].caveats
    assert "Supported claims: clm_overall, clm_badge" in markdown
    assert "never changes deterministic CRIS-SME risk scores" in narrative.deterministic_score_impact


def test_claim_bound_narrative_marks_unverified_claims() -> None:
    narrative = build_claim_bound_narrative(
        {
            "claim_verification_pack": {
                "claims": [
                    {
                        "claim_id": "clm_integrity",
                        "claim_type": "integrity",
                        "statement": "RBOM is missing.",
                        "verification_status": "unverified",
                        "caveats": ["RBOM missing."],
                    }
                ]
            }
        }
    )

    assert narrative.sections[0].section_id == "assurance"
    assert "not verified" in narrative.sections[0].text
