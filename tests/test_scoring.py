# Unit tests for the deterministic CRIS-SME scoring engine.
from cris_sme.engine.scoring import score_findings
from cris_sme.models.finding import Finding, FindingCategory, FindingSeverity


def make_finding(
    *,
    control_id: str,
    category: FindingCategory,
    severity: FindingSeverity,
    is_compliant: bool,
    exposure: float,
    data_sensitivity: float,
    confidence: float,
    remediation_effort: float = 0.3,
) -> Finding:
    """Create compact test findings with explicit scoring inputs."""
    return Finding(
        control_id=control_id,
        title=f"Test finding {control_id}",
        category=category,
        severity=severity,
        evidence=["Synthetic test evidence"],
        resource_scope="Subscription / Test",
        is_compliant=is_compliant,
        confidence=confidence,
        exposure=exposure,
        data_sensitivity=data_sensitivity,
        remediation_effort=remediation_effort,
        mapping=["Test mapping"],
    )


def test_score_findings_excludes_compliant_items_from_risk_output() -> None:
    findings = [
        make_finding(
            control_id="IAM-001",
            category=FindingCategory.IAM,
            severity=FindingSeverity.CRITICAL,
            is_compliant=False,
            exposure=0.9,
            data_sensitivity=0.9,
            confidence=0.95,
        ),
        make_finding(
            control_id="CMP-001",
            category=FindingCategory.COMPUTE,
            severity=FindingSeverity.MEDIUM,
            is_compliant=True,
            exposure=0.2,
            data_sensitivity=0.3,
            confidence=0.9,
        ),
    ]

    result = score_findings(findings)

    assert result.total_findings == 2
    assert result.non_compliant_findings == 1
    assert len(result.prioritized_findings) == 1
    assert result.prioritized_findings[0].finding.control_id == "IAM-001"


def test_score_findings_orders_results_by_highest_risk_first() -> None:
    findings = [
        make_finding(
            control_id="LOW-001",
            category=FindingCategory.GOVERNANCE,
            severity=FindingSeverity.LOW,
            is_compliant=False,
            exposure=0.1,
            data_sensitivity=0.1,
            confidence=0.75,
        ),
        make_finding(
            control_id="HIGH-001",
            category=FindingCategory.NETWORK,
            severity=FindingSeverity.HIGH,
            is_compliant=False,
            exposure=1.0,
            data_sensitivity=0.8,
            confidence=0.95,
        ),
    ]

    result = score_findings(findings)

    assert result.prioritized_findings[0].finding.control_id == "HIGH-001"
    assert result.prioritized_findings[0].score > result.prioritized_findings[1].score


def test_score_findings_generates_weighted_overall_and_category_scores() -> None:
    findings = [
        make_finding(
            control_id="IAM-001",
            category=FindingCategory.IAM,
            severity=FindingSeverity.CRITICAL,
            is_compliant=False,
            exposure=1.0,
            data_sensitivity=0.9,
            confidence=0.95,
        ),
        make_finding(
            control_id="NET-001",
            category=FindingCategory.NETWORK,
            severity=FindingSeverity.HIGH,
            is_compliant=False,
            exposure=0.9,
            data_sensitivity=0.6,
            confidence=0.9,
        ),
    ]

    result = score_findings(findings)

    assert result.category_scores["IAM"] > 0
    assert result.category_scores["Network"] > 0
    assert result.overall_risk_score > 0
    assert result.overall_risk_score <= 100
