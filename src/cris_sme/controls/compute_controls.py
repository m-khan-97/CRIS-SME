# Compute and workload controls that convert synthetic cloud posture into explainable findings.
from __future__ import annotations

from cris_sme.models.cloud_profile import CloudProfile
from cris_sme.models.finding import Finding, FindingSeverity
from cris_sme.controls.common import build_control_finding


def evaluate_compute_controls(profiles: list[CloudProfile]) -> list[Finding]:
    """Evaluate compute and workload controls across synthetic SME profiles."""
    findings: list[Finding] = []

    for profile in profiles:
        findings.extend(_evaluate_patch_management(profile))
        findings.extend(_evaluate_endpoint_protection(profile))
        findings.extend(_evaluate_hardening_baseline(profile))
        findings.extend(_evaluate_workload_backup_agents(profile))
        findings.extend(_evaluate_linux_password_authentication(profile))

    return findings


def _evaluate_patch_management(profile: CloudProfile) -> list[Finding]:
    """Check whether critical virtual machines remain unpatched."""
    count = profile.compute.unpatched_critical_vms
    if count == 0:
        return []

    severity = FindingSeverity.CRITICAL if count >= 2 else FindingSeverity.HIGH
    return [
        build_control_finding(
            profile=profile,
            control_id="CMP-001",
            severity=severity,
            evidence=[f"{count} critical VM(s) require urgent patching"],
            is_compliant=False,
            confidence=0.92,
            exposure=0.7,
            remediation_effort=0.45,
            generated_by="compute_controls",
        )
    ]


def _evaluate_endpoint_protection(profile: CloudProfile) -> list[Finding]:
    """Check endpoint protection coverage on workloads."""
    coverage = profile.compute.endpoint_protection_coverage_ratio
    if coverage >= 0.9:
        return []

    severity = FindingSeverity.HIGH if coverage < 0.7 else FindingSeverity.MEDIUM
    return [
        build_control_finding(
            profile=profile,
            control_id="CMP-002",
            severity=severity,
            evidence=[f"Endpoint protection coverage is approximately {coverage:.0%}"],
            is_compliant=False,
            confidence=0.88,
            exposure=0.6,
            remediation_effort=0.35,
            generated_by="compute_controls",
        )
    ]


def _evaluate_hardening_baseline(profile: CloudProfile) -> list[Finding]:
    """Check workload hardening baseline coverage."""
    coverage = profile.compute.hardened_baseline_coverage_ratio
    if coverage >= 0.9:
        return []

    severity = FindingSeverity.HIGH if coverage < 0.7 else FindingSeverity.MEDIUM
    return [
        build_control_finding(
            profile=profile,
            control_id="CMP-003",
            severity=severity,
            evidence=[f"Hardened baseline coverage is approximately {coverage:.0%}"],
            is_compliant=False,
            confidence=0.85,
            exposure=0.55,
            remediation_effort=0.5,
            generated_by="compute_controls",
        )
    ]


def _evaluate_workload_backup_agents(profile: CloudProfile) -> list[Finding]:
    """Check coverage of backup or recovery agents across workloads."""
    coverage = profile.compute.workload_backup_agent_coverage_ratio
    if coverage >= 0.9:
        return []

    severity = FindingSeverity.HIGH if coverage < 0.7 else FindingSeverity.MEDIUM
    return [
        build_control_finding(
            profile=profile,
            control_id="CMP-004",
            severity=severity,
            evidence=[f"Workload backup agent coverage is approximately {coverage:.0%}"],
            is_compliant=False,
            confidence=0.83,
            exposure=0.5,
            remediation_effort=0.4,
            generated_by="compute_controls",
        )
    ]


def _evaluate_linux_password_authentication(profile: CloudProfile) -> list[Finding]:
    """Check whether Linux workloads still allow password-based SSH authentication."""
    count = profile.compute.linux_password_auth_enabled_vms
    if count == 0:
        return []

    severity = FindingSeverity.HIGH if count >= 2 else FindingSeverity.MEDIUM
    return [
        build_control_finding(
            profile=profile,
            control_id="CMP-005",
            severity=severity,
            evidence=[
                f"{count} Linux VM(s) permit password authentication for administrative access"
            ],
            is_compliant=False,
            confidence=0.94,
            exposure=0.65,
            remediation_effort=0.3,
            generated_by="compute_controls",
        )
    ]
