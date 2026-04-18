# Unit tests for UK readiness profiling in CRIS-SME.
from cris_sme.engine.uk_readiness import build_cyber_essentials_readiness
from cris_sme.models.finding import Finding, FindingCategory, FindingSeverity, RemediationCostTier


def make_finding(control_id: str, category: FindingCategory) -> Finding:
    """Create a compact non-compliant finding for UK-readiness tests."""
    return Finding(
        control_id=control_id,
        title="Synthetic finding",
        category=category,
        severity=FindingSeverity.HIGH,
        evidence=["evidence"],
        resource_scope="scope",
        is_compliant=False,
        confidence=0.9,
        exposure=0.8,
        data_sensitivity=0.7,
        remediation_effort=0.3,
        remediation_summary="Fix it",
        remediation_cost_tier=RemediationCostTier.FREE,
        mapping=[],
        metadata={},
    )


def test_build_cyber_essentials_readiness_reports_pillar_statuses() -> None:
    readiness = build_cyber_essentials_readiness(
        [
            make_finding("NET-002", FindingCategory.NETWORK),
            make_finding("CMP-002", FindingCategory.COMPUTE),
        ]
    )

    assert readiness["profile_name"] == "Cyber Essentials readiness profile"
    assert readiness["pillar_count"] == 5
    assert any(
        pillar["pillar_name"] == "Firewalls" and pillar["controls_not_met"] >= 1
        for pillar in readiness["pillars"]
    )
