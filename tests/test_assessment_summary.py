# Tests for canonical assessment summary generation.
from cris_sme.engine import build_assessment_summary
from tests.test_sarif_export import _build_report


def test_assessment_summary_precomputes_core_report_sections() -> None:
    report = _build_report()

    summary = build_assessment_summary(report).model_dump(mode="json")

    assert summary["summary_schema_version"] == "1.0.0"
    assert summary["generated_at"] == "2026-06-15T00:00:00Z"
    assert summary["collector_mode"] == "mock"
    assert summary["overall_risk_score"] == report["overall_risk_score"]
    assert summary["risk_band"] in {"clear", "low", "moderate", "high", "critical"}
    assert summary["finding_summary"]["finding_count"] == len(
        report["prioritized_risks"]
    )
    assert summary["finding_summary"]["top_controls"]
    assert summary["resource_summary"]["context_model"] == (
        "cris_sme_resource_evidence_context_v1"
    )
    assert summary["resource_summary"]["asset_count"] == len(
        report["resource_context"]["assets"]
    )
    assert summary["resource_summary"]["evidence_record_count"] == len(
        report["resource_context"]["evidence_records"]
    )
    assert summary["evidence_summary"]["sufficiency_counts"]
    assert summary["provider_summary"]["contract_count"] == 108
    assert summary["provider_summary"]["conformance_passed"] is True
    assert summary["compliance_summary"]["uk_sme_mapped_control_count"] >= 1


def test_assessment_summary_includes_late_stage_assurance_and_drift() -> None:
    report = _build_report()
    report["claim_verification_pack"] = {
        "pack_schema_version": "1.0.0",
        "claim_count": 4,
        "verified_claim_count": 3,
        "caveated_claim_count": 1,
        "claim_type_counts": {"overall_risk": 1, "top_risk": 3},
    }
    report["risk_drift_analysis"] = {
        "status": "changed",
        "direction": "worse",
        "overall_risk_delta": 4.25,
    }
    report["control_drift_attribution"] = {
        "comparable": True,
        "primary_attribution": "evidence_drift",
        "overall_risk_delta": 4.25,
        "attribution_counts": {"evidence_drift": 2},
        "evidence_changed": True,
        "policy_pack_changed": False,
        "collector_mode_changed": False,
    }
    report["assessment_assurance"] = {
        "assurance_score": 87.5,
        "assurance_level": "strong",
    }
    report["report_trust_badge"] = {
        "level": "verified",
        "assurance_score": 90.0,
    }
    report["assurance_case"] = {
        "overall_conclusion": "supported_with_caveats",
        "assurance_score": 86.0,
    }

    summary = build_assessment_summary(report).model_dump(mode="json")

    assert summary["claim_summary"]["claim_count"] == 4
    assert summary["claim_summary"]["verified_claim_count"] == 3
    assert summary["drift_summary"]["risk_drift_direction"] == "worse"
    assert summary["drift_summary"]["control_drift_primary_attribution"] == (
        "evidence_drift"
    )
    assert summary["drift_summary"]["evidence_changed"] is True
    assert summary["action_summary"]["phase_count"] == 3
    assert "Fix this week" in summary["action_summary"]["phase_action_counts"]
    assert summary["assurance_summary"]["assessment_assurance_level"] == "strong"
    assert summary["assurance_summary"]["trust_badge_level"] == "verified"
    assert summary["assurance_summary"]["assurance_case_conclusion"] == (
        "supported_with_caveats"
    )
