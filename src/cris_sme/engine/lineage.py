# Evidence lineage and run-provenance helpers for CRIS-SME reports.
from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from typing import Any

from cris_sme.engine.scoring import ScoredFinding
from cris_sme.models.cloud_profile import CloudProfile
from cris_sme.models.finding import Finding
from cris_sme.models.platform import (
    CollectorCoverage,
    ConfidenceAssessment,
    FindingTrace,
    ObservationClass,
    PolicyPackMetadata,
    RunMetadata,
)


def build_stable_finding_id(finding: Finding) -> str:
    """Create a deterministic finding identifier from stable finding attributes."""
    raw = "|".join(
        [
            finding.control_id,
            finding.category.value,
            finding.resource_scope,
            str(finding.metadata.get("organization_id", "")),
            str(finding.metadata.get("provider", "azure")),
        ]
    )
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return f"fdg_{digest[:14]}"


def build_finding_trace(item: ScoredFinding) -> FindingTrace:
    """Build a structured finding trace from one scored finding."""
    finding = item.finding
    evidence_refs = [
        f"evidence:{build_stable_finding_id(finding)}:{index + 1}"
        for index in range(len(finding.evidence))
    ]
    observation_class = _observation_class_for_finding(finding)
    direct_count = sum(1 for _ in finding.evidence)
    inferred_count = 0 if direct_count > 0 else 1
    unavailable_count = 1 if finding.control_id == "IAM-005" else 0

    return FindingTrace(
        finding_id=build_stable_finding_id(finding),
        rule_version=str(finding.metadata.get("rule_version", "1.0.0")),
        evidence_refs=evidence_refs,
        failed_conditions=_failed_conditions_for_finding(finding),
        rationale=(
            f"Control {finding.control_id} is non-compliant with deterministic score "
            f"{item.score:.2f}; priority is {item.priority.lower()}."
        ),
        observation_class=observation_class,
        direct_evidence_count=direct_count,
        inferred_evidence_count=inferred_count,
        unavailable_evidence_count=unavailable_count,
    )


def build_confidence_assessment(item: ScoredFinding) -> ConfidenceAssessment:
    """Build a structured confidence assessment object for one scored finding."""
    return ConfidenceAssessment(
        observed_confidence=item.breakdown.observed_confidence,
        calibrated_confidence=item.breakdown.calibrated_confidence,
        calibration_status=item.breakdown.calibration_status,
        confidence_explanation=(
            "Calibrated confidence blends observed control confidence with control-level "
            "empirical agreement metadata according to calibration maturity."
        ),
    )


def build_collector_coverage(profiles: list[CloudProfile]) -> list[CollectorCoverage]:
    """Summarize per-provider collection coverage and observability boundaries."""
    coverage_items: list[CollectorCoverage] = []
    for profile in profiles:
        observed_domains = [
            str(profile.metadata.get("iam_collection_mode", "iam-default")),
            str(profile.metadata.get("network_collection_mode", "network-default")),
            str(profile.metadata.get("data_collection_mode", "data-default")),
            str(profile.metadata.get("monitoring_collection_mode", "monitoring-default")),
            str(profile.metadata.get("compute_collection_mode", "compute-default")),
            str(profile.metadata.get("governance_collection_mode", "governance-default")),
        ]
        partially_observed_domains: list[str] = []
        unavailable_domains: list[str] = []
        identity_observability = str(profile.metadata.get("identity_observability", "")).strip().lower()
        if identity_observability and identity_observability != "full":
            partially_observed_domains.append("tenant_identity_controls")
        if str(profile.metadata.get("conditional_access_accessible", "")).lower() == "false":
            unavailable_domains.append("conditional_access_tenant_scope")

        coverage_items.append(
            CollectorCoverage(
                provider=profile.provider,
                collection_mode=str(profile.metadata.get("collection_mode", "unknown")),
                observed_domains=observed_domains,
                partially_observed_domains=partially_observed_domains,
                unavailable_domains=unavailable_domains,
                evidence_quality_note=(
                    "Coverage reflects currently observable evidence paths. "
                    "Unavailable signals are recorded explicitly rather than inferred as compliant."
                ),
            )
        )
    return coverage_items


def build_run_metadata(
    *,
    generated_at: str,
    collector_mode: str,
    schema_version: str,
    narrator_enabled: bool,
    providers_in_scope: list[str],
    policy_pack: dict[str, Any],
    collector_coverage: list[CollectorCoverage],
) -> RunMetadata:
    """Build run-level metadata for reproducibility and governance traceability."""
    run_id = _run_id(generated_at=generated_at, collector_mode=collector_mode)
    return RunMetadata(
        run_id=run_id,
        generated_at=generated_at,
        collector_mode=collector_mode,
        schema_version=schema_version,
        engine_version="2.0.0",
        deterministic_scoring=True,
        narrator_enabled=narrator_enabled,
        providers_in_scope=sorted(set(providers_in_scope)),
        policy_pack=PolicyPackMetadata.model_validate(policy_pack),
        collector_coverage=collector_coverage,
    )


def _run_id(*, generated_at: str, collector_mode: str) -> str:
    raw = f"{collector_mode}|{generated_at}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()
    return f"run_{digest[:16]}"


def _observation_class_for_finding(finding: Finding) -> ObservationClass:
    if finding.control_id == "IAM-005":
        return ObservationClass.INFERRED
    if finding.evidence:
        return ObservationClass.OBSERVED
    return ObservationClass.UNAVAILABLE


def _failed_conditions_for_finding(finding: Finding) -> list[str]:
    if finding.is_compliant:
        return []
    if finding.evidence:
        return [str(item) for item in finding.evidence]
    return ["Control marked non-compliant without explicit evidence text."]


def now_iso_utc() -> str:
    """Return current UTC time in normalized RFC3339-like format."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
