# Governance and cost hygiene controls that convert synthetic cloud posture into explainable findings.
from __future__ import annotations

from cris_sme.models.cloud_profile import CloudProfile
from cris_sme.models.finding import Finding, FindingSeverity
from cris_sme.controls.common import build_control_finding


def evaluate_governance_controls(profiles: list[CloudProfile]) -> list[Finding]:
    """Evaluate governance and cost hygiene controls across synthetic SME profiles."""
    findings: list[Finding] = []

    for profile in profiles:
        findings.extend(_evaluate_tagging_coverage(profile))
        findings.extend(_evaluate_budget_alerting(profile))
        findings.extend(_evaluate_policy_assignment_coverage(profile))
        findings.extend(_evaluate_orphaned_resources(profile))

    return findings


def _evaluate_tagging_coverage(profile: CloudProfile) -> list[Finding]:
    """Check coverage of required governance tags."""
    coverage = profile.governance.tagging_coverage_ratio
    if coverage >= 0.9:
        return []

    severity = FindingSeverity.MEDIUM if coverage >= 0.7 else FindingSeverity.HIGH
    return [
        build_control_finding(
            profile=profile,
            control_id="GOV-001",
            severity=severity,
            evidence=[f"Required tagging coverage is approximately {coverage:.0%}"],
            is_compliant=False,
            confidence=0.84,
            exposure=0.25,
            remediation_effort=0.4,
            generated_by="governance_controls",
        )
    ]


def _evaluate_budget_alerting(profile: CloudProfile) -> list[Finding]:
    """Check whether budget alerts are enabled for cloud spending oversight."""
    governance = profile.governance
    if governance.budget_alerts_enabled:
        return []

    metadata = {
        "budget_api_accessible": governance.budget_api_accessible,
        "budget_alert_count": governance.budget_alert_count,
        "budget_evidence_state": governance.budget_evidence_state,
    }
    if governance.budget_api_accessible:
        evidence = ["Budget or spend alerting is not configured"]
        confidence = 0.8
    else:
        evidence = [
            "Budget or spend alerting could not be verified because Azure budget APIs were inaccessible",
            "The finding is conservative and should be reviewed as an evidence availability gap",
        ]
        confidence = 0.62

    return [
        build_control_finding(
            profile=profile,
            control_id="GOV-002",
            severity=FindingSeverity.MEDIUM,
            evidence=evidence,
            is_compliant=False,
            confidence=confidence,
            exposure=0.2,
            remediation_effort=0.25,
            generated_by="governance_controls",
            metadata=metadata,
        )
    ]


def _evaluate_policy_assignment_coverage(profile: CloudProfile) -> list[Finding]:
    """Check assignment coverage for baseline governance policies."""
    coverage = profile.governance.policy_assignment_coverage_ratio
    if coverage >= 0.9:
        return []

    severity = FindingSeverity.HIGH if coverage < 0.7 else FindingSeverity.MEDIUM
    return [
        build_control_finding(
            profile=profile,
            control_id="GOV-003",
            severity=severity,
            evidence=[f"Baseline policy assignment coverage is approximately {coverage:.0%}"],
            is_compliant=False,
            confidence=0.87,
            exposure=0.35,
            remediation_effort=0.45,
            generated_by="governance_controls",
        )
    ]


def _evaluate_orphaned_resources(profile: CloudProfile) -> list[Finding]:
    """Check for orphaned resources that increase cost and governance noise."""
    count = profile.governance.orphaned_resource_count
    if count == 0:
        return []

    severity = FindingSeverity.HIGH if count >= 5 else FindingSeverity.MEDIUM
    return [
        build_control_finding(
            profile=profile,
            control_id="GOV-004",
            severity=severity,
            evidence=[f"{count} orphaned resource(s) were identified"],
            is_compliant=False,
            confidence=0.82,
            exposure=0.3,
            remediation_effort=0.35,
            generated_by="governance_controls",
        )
    ]
