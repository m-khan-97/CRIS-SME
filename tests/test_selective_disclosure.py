# Tests for stakeholder-specific selective disclosure evidence rooms.
from pathlib import Path

from cris_sme.engine.selective_disclosure import (
    build_selective_disclosure_package,
    write_selective_disclosure_package,
)
from cris_sme.reporting.evidence_room import (
    build_evidence_room_html,
    write_evidence_room_html,
)


def test_selective_disclosure_builds_profiles_and_redacts_sensitive_values() -> None:
    package = build_selective_disclosure_package(_report())
    payload = package.model_dump(mode="json")

    assert package.profile_count == 5
    assert {room.profile_id for room in package.rooms} == {
        "executive",
        "customer",
        "insurer",
        "auditor",
        "technical_appendix",
    }
    customer = next(room for room in package.rooms if room.profile_id == "customer")
    assert customer.included_claim_count >= 2
    assert customer.redaction_count > 0
    assert customer.shared_evidence_count > 0
    assert customer.integrity["room_sha256"]
    rendered = str(payload)
    assert "11111111-1111-1111-1111-111111111111" not in rendered
    assert "10.1.2.3" not in rendered
    assert "admin@example.com" not in rendered
    assert "/subscriptions/" not in rendered
    assert "[redacted-id]" in rendered
    assert "[redacted-ip]" in rendered


def test_selective_disclosure_records_withheld_evidence_for_summary_profile() -> None:
    package = build_selective_disclosure_package(_report())

    executive = next(room for room in package.rooms if room.profile_id == "executive")

    assert executive.shared_evidence_count == 0
    assert executive.withheld_count > 0
    assert "summary-only" in executive.withheld_items[0].reason
    assert "never changes deterministic" in package.deterministic_score_impact


def test_evidence_room_html_renders_profiles_and_escapes_claim_text() -> None:
    package = build_selective_disclosure_package(_report())
    html = build_evidence_room_html(package.model_dump(mode="json"))

    assert "CRIS-SME Evidence Room" in html
    assert "Customer Assurance" in html
    assert "Withheld Evidence" in html
    assert "Redaction Register" in html
    assert "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;" in html
    assert "<script>alert" not in html


def test_write_selective_disclosure_artifacts(tmp_path: Path) -> None:
    package = build_selective_disclosure_package(_report())
    json_path = write_selective_disclosure_package(package, tmp_path / "room.json")
    html_path = write_evidence_room_html(
        build_evidence_room_html(package.model_dump(mode="json")),
        tmp_path / "room.html",
    )

    assert json_path.read_text(encoding="utf-8").startswith("{")
    assert "CRIS-SME Evidence Room" in html_path.read_text(encoding="utf-8")


def _report() -> dict[str, object]:
    return {
        "generated_at": "2026-05-05T10:00:00Z",
        "overall_risk_score": 42.5,
        "risk_bill_of_materials": {"canonical_report_sha256": "a" * 64},
        "report_artifacts": {
            "claim_verification_pack": "outputs/reports/cris_sme_claim_verification_pack.json",
            "assurance_case": "outputs/reports/cris_sme_assurance_case.json",
            "decision_provenance_graph": "outputs/reports/cris_sme_decision_provenance_graph.json",
        },
        "claim_verification_pack": {
            "claims": [
                {
                    "claim_id": "clm_overall",
                    "claim_type": "overall_risk",
                    "audience": "executive",
                    "statement": "Overall score references admin@example.com.",
                    "verification_status": "verified",
                    "confidence": 0.95,
                    "control_ids": ["IAM-001"],
                    "finding_ids": ["fdg_1"],
                    "provenance_node_ids": ["snapshot:demo"],
                    "rbom_artifact_refs": ["json_report"],
                    "caveats": [],
                    "deterministic_score_impact": "No impact.",
                },
                {
                    "claim_id": "clm_top",
                    "claim_type": "top_risk",
                    "audience": "executive",
                    "statement": "<script>alert('x')</script>",
                    "verification_status": "caveated",
                    "confidence": 0.72,
                    "control_ids": ["NET-001"],
                    "finding_ids": ["fdg_2"],
                    "provenance_node_ids": ["finding:fdg_2"],
                    "rbom_artifact_refs": ["json_report"],
                    "caveats": ["Evidence sufficiency is partial."],
                    "deterministic_score_impact": "No impact.",
                },
                {
                    "claim_id": "clm_ins",
                    "claim_type": "insurance_question",
                    "audience": "insurance",
                    "statement": "INS-001 is not_met.",
                    "verification_status": "caveated",
                    "confidence": 0.7,
                    "control_ids": ["IAM-001"],
                    "finding_ids": ["fdg_1"],
                    "provenance_node_ids": ["control:IAM-001"],
                    "rbom_artifact_refs": ["cyber_insurance_pack"],
                    "caveats": ["Require MFA."],
                    "deterministic_score_impact": "No impact.",
                },
            ]
        },
        "assurance_case": {
            "case_name": "CRIS-SME Assessment Assurance Case",
            "overall_conclusion": "caveated",
            "assurance_score": 88.0,
            "arguments": [
                {
                    "argument_id": "case_1",
                    "top_claim": "Risk is traceable.",
                    "conclusion": "caveated",
                    "confidence": 0.8,
                    "supporting_claim_ids": ["clm_overall", "clm_top"],
                    "evidence_refs": ["admin@example.com used privileged access"],
                    "provenance_node_ids": ["snapshot:demo"],
                    "rbom_artifact_refs": ["json_report"],
                    "caveats": ["Some evidence redacted."],
                    "residual_gaps": [],
                    "reasoning": "Claims link to findings and evidence.",
                }
            ],
            "open_caveats": ["Some evidence redacted."],
            "residual_gaps": [],
            "deterministic_score_impact": "No impact.",
        },
        "claim_bound_narrative": {
            "sections": [
                {
                    "section_id": "summary",
                    "heading": "Executive Summary",
                    "text": "Overall score references admin@example.com. [clm_overall]",
                    "cited_claim_ids": ["clm_overall"],
                    "caveats": [],
                }
            ],
            "guardrails": ["Narrative is claim-bound."],
        },
        "decision_provenance_graph": {
            "top_decision_paths": [
                {
                    "control_id": "NET-001",
                    "finding_id": "fdg_2",
                    "summary": "Path includes 10.1.2.3 and sensitive resource.",
                    "node_ids": [
                        "snapshot:11111111-1111-1111-1111-111111111111",
                        "finding:fdg_2",
                    ],
                }
            ]
        },
        "prioritized_risks": [
            {
                "finding_id": "fdg_1",
                "control_id": "IAM-001",
                "title": "Privileged MFA gap",
                "priority": "high",
                "score": 82.0,
                "resource_scope": "/subscriptions/11111111-1111-1111-1111-111111111111/resourceGroups/prod/providers/Microsoft.Compute/virtualMachines/vm1",
                "evidence": [
                    "admin@example.com signed in from 10.1.2.3.",
                    "Resource id 11111111-1111-1111-1111-111111111111 lacks MFA.",
                ],
                "evidence_quality": {
                    "sufficiency": "partial",
                    "direct_evidence_count": 1,
                },
            }
        ],
    }
