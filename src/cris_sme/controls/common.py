# Shared control helpers for consistent finding construction across CRIS-SME domains.
from __future__ import annotations

from typing import Any

from cris_sme.controls.catalog import get_control_entry
from cris_sme.policies import get_control_spec
from cris_sme.models.cloud_profile import CloudProfile
from cris_sme.models.finding import Finding, FindingSeverity


def build_control_finding(
    *,
    profile: CloudProfile,
    control_id: str,
    severity: FindingSeverity,
    evidence: list[str],
    is_compliant: bool,
    confidence: float,
    exposure: float,
    remediation_effort: float,
    generated_by: str,
    title_override: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Finding:
    """Build a finding using the central control catalog as the metadata source of truth."""
    control = get_control_entry(control_id)
    control_spec = get_control_spec(control_id)
    merged_metadata = {
        **base_metadata(profile, generated_by=generated_by),
        "control_category": control.category.value,
        "rule_version": control_spec.version,
        "control_intent": control_spec.intent,
        "control_applicability": control_spec.applicability,
        "control_known_limitations": list(control_spec.known_limitations),
        "evidence_requirements": list(control_spec.evidence_requirements),
        "provider_support": dict(control_spec.provider_support),
    }
    if metadata:
        merged_metadata.update(metadata)

    return Finding(
        control_id=control.control_id,
        title=title_override or control.title,
        category=control.category,
        severity=severity,
        evidence=evidence,
        resource_scope=profile.tenant_scope,
        is_compliant=is_compliant,
        confidence=confidence,
        exposure=exposure,
        data_sensitivity=sector_data_sensitivity(profile.sector),
        remediation_effort=remediation_effort,
        remediation_summary=control.remediation_summary,
        remediation_cost_tier=control.remediation_cost_tier,
        mapping=control.mapping,
        metadata=merged_metadata,
    )


def sector_data_sensitivity(sector: str) -> float:
    """Map broad SME sector types to a simple data sensitivity baseline."""
    normalized = sector.strip().lower()
    sensitivity_map = {
        "financial services": 0.95,
        "healthcare": 1.0,
        "retail": 0.75,
        "education": 0.7,
        "professional services": 0.65,
    }
    return sensitivity_map.get(normalized, 0.6)


def base_metadata(profile: CloudProfile, *, generated_by: str) -> dict[str, str]:
    """Provide consistent metadata for generated findings."""
    return {
        "organization_id": profile.organization_id,
        "organization_name": profile.organization_name,
        "provider": profile.provider,
        "sector": profile.sector,
        "profile_source": str(profile.metadata.get("profile_source", "synthetic")),
        "generated_by": generated_by,
    }
