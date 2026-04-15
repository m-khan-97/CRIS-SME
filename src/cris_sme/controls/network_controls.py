# Network governance controls that convert synthetic Azure posture into explainable findings.
from __future__ import annotations

from cris_sme.models.cloud_profile import CloudProfile
from cris_sme.models.finding import Finding, FindingSeverity
from cris_sme.controls.common import build_control_finding


def evaluate_network_controls(profiles: list[CloudProfile]) -> list[Finding]:
    """Evaluate network controls across synthetic SME profiles."""
    findings: list[Finding] = []

    for profile in profiles:
        findings.extend(_evaluate_remote_admin_exposure(profile))
        findings.extend(_evaluate_permissive_nsg_rules(profile))
        findings.extend(_evaluate_public_storage_exposure(profile))
        findings.extend(_evaluate_private_endpoint_coverage(profile))

    return findings


def _evaluate_remote_admin_exposure(profile: CloudProfile) -> list[Finding]:
    """Check whether RDP or SSH is exposed to the public internet."""
    network = profile.network
    exposed_assets = network.internet_exposed_rdp_assets + network.internet_exposed_ssh_assets

    if exposed_assets == 0:
        return []

    evidence: list[str] = []
    if network.internet_exposed_rdp_assets:
        evidence.append(
            f"{network.internet_exposed_rdp_assets} asset(s) expose RDP to the public internet"
        )
    if network.internet_exposed_ssh_assets:
        evidence.append(
            f"{network.internet_exposed_ssh_assets} asset(s) expose SSH to the public internet"
        )

    severity = (
        FindingSeverity.CRITICAL
        if network.internet_exposed_rdp_assets > 0
        else FindingSeverity.HIGH
    )

    return [
        build_control_finding(
            profile=profile,
            control_id="NET-001",
            severity=severity,
            evidence=evidence,
            is_compliant=False,
            confidence=0.94,
            exposure=1.0,
            remediation_effort=0.35,
            generated_by="network_controls",
        )
    ]


def _evaluate_permissive_nsg_rules(profile: CloudProfile) -> list[Finding]:
    """Check for overly permissive network security group rules."""
    count = profile.network.permissive_nsg_rules
    if count == 0:
        return []

    severity = FindingSeverity.HIGH if count >= 2 else FindingSeverity.MEDIUM

    return [
        build_control_finding(
            profile=profile,
            control_id="NET-002",
            severity=severity,
            evidence=[
                f"{count} permissive NSG rule(s) were identified",
            ],
            is_compliant=False,
            confidence=0.86,
            exposure=0.8,
            remediation_effort=0.4,
            generated_by="network_controls",
        )
    ]


def _evaluate_public_storage_exposure(profile: CloudProfile) -> list[Finding]:
    """Check for storage services exposed directly through public endpoints."""
    count = profile.network.public_storage_endpoints
    if count == 0:
        return []

    severity = FindingSeverity.HIGH if count == 1 else FindingSeverity.CRITICAL

    return [
        build_control_finding(
            profile=profile,
            control_id="NET-003",
            severity=severity,
            evidence=[
                f"{count} public storage endpoint(s) were identified",
            ],
            is_compliant=False,
            confidence=0.9,
            exposure=0.95,
            remediation_effort=0.3,
            generated_by="network_controls",
        )
    ]


def _evaluate_private_endpoint_coverage(profile: CloudProfile) -> list[Finding]:
    """Check whether workloads that require private endpoints are fully covered."""
    required = profile.network.private_endpoints_required
    configured = profile.network.private_endpoints_configured

    if required == 0 or configured >= required:
        return []

    missing = required - configured
    severity = FindingSeverity.HIGH if missing >= 2 else FindingSeverity.MEDIUM

    return [
        build_control_finding(
            profile=profile,
            control_id="NET-004",
            severity=severity,
            evidence=[
                f"{missing} required private endpoint(s) are not configured",
                f"{configured} of {required} expected private endpoint(s) are currently deployed",
            ],
            is_compliant=False,
            confidence=0.82,
            exposure=0.7,
            remediation_effort=0.5,
            generated_by="network_controls",
        )
    ]
