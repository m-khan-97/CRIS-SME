# Production-shape platform schemas for evidence, assets, decisions, lifecycle, and run metadata.
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ObservationClass(str, Enum):
    """Classify whether a datapoint is directly observed, inferred, or unavailable."""

    OBSERVED = "observed"
    INFERRED = "inferred"
    UNAVAILABLE = "unavailable"


class FindingStatus(str, Enum):
    """Lifecycle status for governance findings."""

    OPEN = "open"
    ACCEPTED_RISK = "accepted_risk"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    EXPIRED_EXCEPTION = "expired_exception"


class EvidenceRecord(BaseModel):
    """One raw or normalized evidence item collected during an assessment run."""

    evidence_id: str = Field(..., min_length=6)
    provider: str = Field(..., min_length=2)
    collector: str = Field(..., min_length=2)
    record_type: str = Field(..., min_length=3)
    observation_class: ObservationClass
    observed_at: str = Field(..., min_length=10)
    source_ref: str | None = None
    freshness_hours: float | None = Field(default=None, ge=0.0)
    payload: dict[str, Any] = Field(default_factory=dict)


class Asset(BaseModel):
    """Normalized cloud asset represented in CRIS-SME's internal context graph."""

    asset_id: str = Field(..., min_length=5)
    provider: str = Field(..., min_length=2)
    asset_type: str = Field(..., min_length=2)
    name: str = Field(..., min_length=2)
    scope: str = Field(..., min_length=2)
    criticality: str = Field(default="medium", min_length=3)
    internet_exposed: bool = False
    tags: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AssetRelationship(BaseModel):
    """Directed relationship between two normalized assets."""

    relationship_id: str = Field(..., min_length=6)
    from_asset_id: str = Field(..., min_length=5)
    to_asset_id: str = Field(..., min_length=5)
    relationship_type: str = Field(..., min_length=3)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CollectorCoverage(BaseModel):
    """Coverage summary of what a collector could and could not observe."""

    provider: str = Field(..., min_length=2)
    collection_mode: str = Field(..., min_length=3)
    observed_domains: list[str] = Field(default_factory=list)
    partially_observed_domains: list[str] = Field(default_factory=list)
    unavailable_domains: list[str] = Field(default_factory=list)
    evidence_quality_note: str = Field(..., min_length=8)


class FindingTrace(BaseModel):
    """Traceability payload linking a finding back to control logic and evidence."""

    finding_id: str = Field(..., min_length=6)
    rule_version: str = Field(..., min_length=3)
    evidence_refs: list[str] = Field(default_factory=list)
    failed_conditions: list[str] = Field(default_factory=list)
    rationale: str = Field(..., min_length=8)
    observation_class: ObservationClass
    direct_evidence_count: int = Field(default=0, ge=0)
    inferred_evidence_count: int = Field(default=0, ge=0)
    unavailable_evidence_count: int = Field(default=0, ge=0)


class ConfidenceAssessment(BaseModel):
    """Structured confidence assessment for a scored decision."""

    observed_confidence: float = Field(..., ge=0.0, le=1.0)
    calibrated_confidence: float = Field(..., ge=0.0, le=1.0)
    calibration_status: str = Field(..., min_length=3)
    confidence_explanation: str = Field(..., min_length=8)


class FrameworkMapping(BaseModel):
    """Mapping from one control to one governance/compliance reference."""

    control_id: str = Field(..., min_length=3)
    framework: str = Field(..., min_length=2)
    reference_id: str = Field(..., min_length=2)
    title: str = Field(..., min_length=3)
    relevance: str = Field(..., min_length=3)


class ExceptionRecord(BaseModel):
    """Approved finding exception with auditable scope and expiry."""

    exception_id: str = Field(..., min_length=6)
    control_id: str = Field(..., min_length=3)
    scope: str = Field(..., min_length=3)
    provider: str = Field(..., min_length=2)
    reason: str = Field(..., min_length=8)
    approved_by: str = Field(..., min_length=3)
    status: FindingStatus = FindingStatus.ACCEPTED_RISK
    expires_at: str = Field(..., min_length=10)
    compensating_control: str | None = None
    notes: str | None = None
    created_at: str = Field(..., min_length=10)


class ActionItem(BaseModel):
    """Actionable remediation task in the decision layer."""

    action_id: str = Field(..., min_length=6)
    control_id: str = Field(..., min_length=3)
    finding_id: str = Field(..., min_length=6)
    title: str = Field(..., min_length=5)
    priority: str = Field(..., min_length=2)
    owner: str | None = None
    target_window: str = Field(..., min_length=4)
    estimated_cost_tier: str = Field(..., min_length=2)
    expected_risk_reduction: float = Field(default=0.0, ge=0.0)
    status: str = Field(default="planned", min_length=3)


class HistoricalSnapshot(BaseModel):
    """Normalized summary of one historical report snapshot."""

    snapshot_id: str = Field(..., min_length=8)
    generated_at: str = Field(..., min_length=10)
    collector_mode: str = Field(..., min_length=2)
    overall_risk_score: float = Field(..., ge=0.0, le=100.0)
    non_compliant_findings: int = Field(..., ge=0)
    category_scores: dict[str, float] = Field(default_factory=dict)


class PolicyPackMetadata(BaseModel):
    """Metadata for the control specification pack used in a run."""

    policy_pack_version: str = Field(..., min_length=3)
    controls_total: int = Field(..., ge=0)
    controls_with_provider_support: int = Field(..., ge=0)
    generated_from_catalog: bool = True
    notes: str = Field(..., min_length=8)


class RunMetadata(BaseModel):
    """Run-level metadata for provenance and reproducibility."""

    run_id: str = Field(..., min_length=8)
    generated_at: str = Field(..., min_length=10)
    collector_mode: str = Field(..., min_length=2)
    schema_version: str = Field(..., min_length=3)
    engine_version: str = Field(..., min_length=3)
    deterministic_scoring: bool = True
    narrator_enabled: bool = False
    providers_in_scope: list[str] = Field(default_factory=list)
    policy_pack: PolicyPackMetadata
    collector_coverage: list[CollectorCoverage] = Field(default_factory=list)
