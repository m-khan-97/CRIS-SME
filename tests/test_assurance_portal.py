# Tests for the customer-facing assurance portal renderer.
from pathlib import Path

from cris_sme.reporting.assurance_portal import (
    build_assurance_portal_html,
    write_assurance_portal_html,
)


def test_assurance_portal_renders_trust_artifacts_and_escapes_claims() -> None:
    html = build_assurance_portal_html(
        {
            "report_trust_badge": {
                "label": "Verified CRIS-SME Report",
                "risk_score_impact": "No impact. Portal only presents existing assurance artifacts.",
            },
            "assurance_case": {
                "assurance_score": 91.5,
                "overall_conclusion": "External reliance is supported with caveats.",
                "arguments": [
                    {
                        "top_claim": "Replay integrity is verified",
                        "conclusion": "supported",
                        "confidence": 0.92,
                        "reasoning": "Replay and RBOM both support the claim.",
                        "supporting_claim_ids": ["clm_replay", "clm_rbom"],
                    }
                ],
            },
            "claim_verification_pack": {
                "claim_count": 2,
                "verified_claim_count": 1,
                "claims": [
                    {
                        "claim_id": "clm_replay",
                        "verification_status": "verified",
                        "statement": "Replay matched deterministic output.",
                    },
                    {
                        "claim_id": "clm_escape",
                        "verification_status": "caveated",
                        "statement": "<script>alert('claim')</script>",
                    },
                ],
            },
            "decision_provenance_graph": {
                "path_count": 1,
                "node_count": 3,
                "top_decision_paths": [
                    {
                        "control_id": "IAM-01",
                        "summary": "Evidence supports the control decision.",
                        "node_ids": ["snapshot:demo", "control:IAM-01", "finding:f-1"],
                    }
                ],
            },
            "claim_bound_narrative": {
                "sections": [
                    {
                        "heading": "Replay And Integrity",
                        "text": "Replay matched deterministic output. [clm_replay]",
                        "cited_claim_ids": ["clm_replay"],
                        "caveats": [],
                    }
                ]
            },
            "assessment_replay": {"replay": {"deterministic_match": True, "overall_risk_delta": 0}},
            "risk_bill_of_materials": {
                "canonical_report_sha256": "abc",
                "artifacts": [{"path": "outputs/reports/cris_sme_report.json"}],
            },
            "evidence_gap_backlog": {"item_count": 3, "high_priority_count": 1},
        }
    )

    assert "CRIS-SME Assurance Portal" in html
    assert "Verified CRIS-SME Report" in html
    assert "Claim-Bound Narrative" in html
    assert "Top Provenance Paths" in html
    assert "Replay integrity is verified" in html
    assert "&lt;script&gt;alert(&#x27;claim&#x27;)&lt;/script&gt;" in html
    assert "<script>alert" not in html


def test_write_assurance_portal_html_writes_file(tmp_path: Path) -> None:
    target = tmp_path / "portal" / "assurance.html"

    written = write_assurance_portal_html("<html>portal</html>", target)

    assert written == target
    assert target.read_text(encoding="utf-8") == "<html>portal</html>"
