# Unit tests for the confidence calibration layer in CRIS-SME scoring.
from cris_sme.engine.confidence import (
    calibrate_finding_confidence,
    summarize_confidence_calibration,
)
from cris_sme.engine.scoring import score_findings
from cris_sme.models.finding import Finding, FindingCategory, FindingSeverity, RemediationCostTier


def make_finding(
    control_id: str = "NET-001",
    confidence: float = 0.94,
    category: FindingCategory = FindingCategory.NETWORK,
) -> Finding:
    """Create a compact finding for confidence-calibration tests."""
    return Finding(
        control_id=control_id,
        title="Administrative services are exposed to the public internet",
        category=category,
        severity=FindingSeverity.CRITICAL,
        evidence=["3 asset(s) expose SSH to the public internet"],
        resource_scope="subscription/test",
        is_compliant=False,
        confidence=confidence,
        exposure=1.0,
        data_sensitivity=0.8,
        remediation_effort=0.4,
        remediation_summary="Restrict SSH exposure.",
        remediation_cost_tier=RemediationCostTier.MEDIUM,
        mapping=["Cyber Essentials Firewalls"],
        metadata={"organization_name": "Calibration SME"},
    )


def test_calibrate_finding_confidence_blends_observed_and_empirical_values() -> None:
    finding = make_finding(control_id="NET-001", confidence=0.94)

    result = calibrate_finding_confidence(finding)

    assert result.calibration_status == "validated"
    assert result.empirical_weight == 0.5
    assert result.calibrated_confidence == 0.95


def test_score_findings_exposes_calibration_details_in_breakdown() -> None:
    finding = make_finding(control_id="IAM-002", confidence=0.96)

    scoring = score_findings([finding])
    breakdown = scoring.prioritized_findings[0].breakdown

    assert breakdown.observed_confidence == 0.96
    assert breakdown.calibrated_confidence > 0.0
    assert breakdown.calibration_status in {"validated", "provisional", "unmapped"}


def test_iomt_controls_use_provisional_lab_calibration() -> None:
    finding = make_finding(
        control_id="IOT-009",
        confidence=0.82,
        category=FindingCategory.IOT,
    )

    result = calibrate_finding_confidence(finding)

    assert result.calibration_status == "provisional"
    assert result.validation_method == "controlled_lab_scenario_comparison"
    assert result.benchmark_source == "azure_iomt_lab_scenarios"
    assert result.sample_size == 3
    assert result.empirical_weight == 0.3
    assert result.calibrated_confidence == 0.802


def test_summarize_confidence_calibration_reports_status_counts() -> None:
    scoring = score_findings([make_finding("NET-001"), make_finding("IAM-003", 0.84)])

    summary = summarize_confidence_calibration(scoring.prioritized_findings)

    assert summary["controls_with_calibration"] == 2
    assert summary["average_calibrated_confidence"] > 0.0
    assert summary["status_counts"]
