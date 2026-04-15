# Monitoring and logging controls that convert synthetic cloud posture into explainable findings.
from __future__ import annotations

from cris_sme.models.cloud_profile import CloudProfile
from cris_sme.models.finding import Finding, FindingSeverity
from cris_sme.controls.common import build_control_finding


def evaluate_monitoring_controls(profiles: list[CloudProfile]) -> list[Finding]:
    """Evaluate monitoring and logging controls across synthetic SME profiles."""
    findings: list[Finding] = []

    for profile in profiles:
        findings.extend(_evaluate_activity_log_retention(profile))
        findings.extend(_evaluate_alert_coverage(profile))
        findings.extend(_evaluate_defender_coverage(profile))
        findings.extend(_evaluate_log_centralization_and_runbooks(profile))

    return findings


def _evaluate_activity_log_retention(profile: CloudProfile) -> list[Finding]:
    """Check whether activity log retention supports governance investigation needs."""
    retention_days = profile.monitoring.activity_log_retention_days
    if retention_days >= 90:
        return []

    severity = FindingSeverity.HIGH if retention_days < 60 else FindingSeverity.MEDIUM
    return [
        build_control_finding(
            profile=profile,
            control_id="MON-001",
            severity=severity,
            evidence=[f"Activity logs are retained for only {retention_days} day(s)"],
            is_compliant=False,
            confidence=0.9,
            exposure=0.45,
            remediation_effort=0.3,
            generated_by="monitoring_controls",
        )
    ]


def _evaluate_alert_coverage(profile: CloudProfile) -> list[Finding]:
    """Check coverage of critical administrative and security alerting."""
    coverage = profile.monitoring.critical_alert_coverage_ratio
    if coverage >= 0.9:
        return []

    severity = FindingSeverity.HIGH if coverage < 0.6 else FindingSeverity.MEDIUM
    return [
        build_control_finding(
            profile=profile,
            control_id="MON-002",
            severity=severity,
            evidence=[f"Critical alert coverage is approximately {coverage:.0%}"],
            is_compliant=False,
            confidence=0.86,
            exposure=0.55,
            remediation_effort=0.4,
            generated_by="monitoring_controls",
        )
    ]


def _evaluate_defender_coverage(profile: CloudProfile) -> list[Finding]:
    """Check whether security monitoring coverage is deployed consistently."""
    coverage = profile.monitoring.defender_coverage_ratio
    if coverage >= 0.9:
        return []

    severity = FindingSeverity.HIGH if coverage < 0.7 else FindingSeverity.MEDIUM
    return [
        build_control_finding(
            profile=profile,
            control_id="MON-003",
            severity=severity,
            evidence=[f"Security monitoring coverage is approximately {coverage:.0%}"],
            is_compliant=False,
            confidence=0.84,
            exposure=0.5,
            remediation_effort=0.45,
            generated_by="monitoring_controls",
        )
    ]


def _evaluate_log_centralization_and_runbooks(profile: CloudProfile) -> list[Finding]:
    """Check whether logging and incident handling foundations are operationally ready."""
    evidence: list[str] = []
    if not profile.monitoring.centralized_logging_enabled:
        evidence.append("Centralized logging is not enabled")
    if not profile.monitoring.incident_response_runbooks_enabled:
        evidence.append("Incident response runbooks are not defined or enabled")

    if not evidence:
        return []

    severity = (
        FindingSeverity.HIGH
        if not profile.monitoring.centralized_logging_enabled
        else FindingSeverity.MEDIUM
    )
    return [
        build_control_finding(
            profile=profile,
            control_id="MON-004",
            severity=severity,
            evidence=evidence,
            is_compliant=False,
            confidence=0.82,
            exposure=0.4,
            remediation_effort=0.5,
            generated_by="monitoring_controls",
        )
    ]
