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


class EvidenceSufficiency(str, Enum):
    """Classify whether evidence is strong enough to support a control decision."""

    SUFFICIENT = "sufficient"
    PARTIAL = "partial"
    INFERRED = "inferred"
    UNAVAILABLE = "unavailable"
    STALE = "stale"
    UNSUPPORTED = "unsupported"


class FindingStatus(str, Enum):
    """Lifecycle status for governance findings."""

    OPEN = "open"
    ACCEPTED_RISK = "accepted_risk"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    EXPIRED_EXCEPTION = "expired_exception"


class DecisionLedgerEventType(str, Enum):
    """Supported append-only governance events for the Decision Ledger."""

    ASSESSMENT_RECORDED = "assessment_recorded"
    FINDING_OPENED = "finding_opened"
    FINDING_RECURRED = "finding_recurred"
    FINDING_RESOLVED = "finding_resolved"
    SCORE_CHANGED = "score_changed"
    LIFECYCLE_STATUS_CHANGED = "lifecycle_status_changed"
    EXCEPTION_APPLIED = "exception_applied"
    EXCEPTION_EXPIRED = "exception_expired"


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


class EvidenceSufficiencyAssessment(BaseModel):
    """Explain whether available evidence is enough to support a finding decision."""

    sufficiency: EvidenceSufficiency
    provider_support: str = Field(..., min_length=3)
    evidence_requirements: list[str] = Field(default_factory=list)
    satisfied_requirements: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    limitation_notes: list[str] = Field(default_factory=list)
    explanation: str = Field(..., min_length=8)


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


class DecisionLedgerEvent(BaseModel):
    """One append-only governance event derived from assessment and finding history."""

    event_id: str = Field(..., min_length=8)
    event_type: DecisionLedgerEventType
    event_time: str = Field(..., min_length=10)
    run_id: str = Field(..., min_length=8)
    finding_id: str | None = None
    control_id: str | None = None
    provider: str | None = None
    organization: str | None = None
    resource_scope: str | None = None
    previous_score: float | None = Field(default=None, ge=0.0, le=100.0)
    current_score: float | None = Field(default=None, ge=0.0, le=100.0)
    previous_status: str | None = None
    current_status: str | None = None
    summary: str = Field(..., min_length=8)
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionLedger(BaseModel):
    """Append-only governance-memory view for one assessment run."""

    ledger_schema_version: str = Field(default="1.0.0", min_length=3)
    generated_at: str = Field(..., min_length=10)
    current_run_id: str = Field(..., min_length=8)
    previous_run_id: str | None = None
    current_evaluation_mode: str = Field(..., min_length=3)
    previous_evaluation_mode: str | None = None
    comparison_basis: str = Field(default="same_evaluation_mode", min_length=3)
    event_count: int = Field(..., ge=0)
    events: list[DecisionLedgerEvent] = Field(default_factory=list)


class RiskBillOfMaterialsArtifact(BaseModel):
    """One hashed artifact included in the Risk Bill of Materials."""

    artifact_name: str = Field(..., min_length=2)
    path: str = Field(..., min_length=1)
    sha256: str = Field(..., min_length=64, max_length=64)
    size_bytes: int = Field(..., ge=0)


class RiskBillOfMaterials(BaseModel):
    """Integrity and provenance manifest for one CRIS-SME assessment."""

    rbom_schema_version: str = Field(default="1.0.0", min_length=3)
    generated_at: str = Field(..., min_length=10)
    run_id: str = Field(..., min_length=8)
    report_schema_version: str = Field(..., min_length=3)
    engine_version: str = Field(..., min_length=3)
    scoring_model: str = Field(..., min_length=3)
    policy_pack_version: str = Field(..., min_length=3)
    collector_mode: str = Field(..., min_length=2)
    providers_in_scope: list[str] = Field(default_factory=list)
    canonical_report_sha256: str = Field(..., min_length=64, max_length=64)
    control_ids: list[str] = Field(default_factory=list)
    finding_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    evidence_sufficiency_counts: dict[str, int] = Field(default_factory=dict)
    decision_ledger_event_counts: dict[str, int] = Field(default_factory=dict)
    artifacts: list[RiskBillOfMaterialsArtifact] = Field(default_factory=list)
    integrity_algorithm: str = Field(default="sha256", min_length=3)
    signature_note: str = Field(..., min_length=8)


class RiskBillOfMaterialsSignature(BaseModel):
    """Detached cryptographic signature metadata for a CRIS-SME RBOM."""

    signature_schema_version: str = Field(default="1.0.0", min_length=3)
    signed_at: str = Field(..., min_length=10)
    algorithm: str = Field(default="hmac-sha256", min_length=3)
    key_id: str = Field(..., min_length=2)
    rbom_sha256: str = Field(..., min_length=64, max_length=64)
    signature: str = Field(..., min_length=64)
    signature_note: str = Field(..., min_length=8)


class RiskBillOfMaterialsVerificationResult(BaseModel):
    """Verification result for a CRIS-SME Risk Bill of Materials."""

    verified: bool
    report_hash_verified: bool
    artifact_hashes_verified: bool
    signature_verified: bool | None = None
    signature_algorithm: str | None = None
    signature_key_id: str | None = None
    checked_artifact_count: int = Field(..., ge=0)
    missing_artifacts: list[str] = Field(default_factory=list)
    mismatched_artifacts: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ProviderEvidenceContract(BaseModel):
    """Per-provider evidence contract for one CRIS-SME control."""

    contract_id: str = Field(..., min_length=6)
    provider: str = Field(..., min_length=2)
    control_id: str = Field(..., min_length=3)
    control_version: str = Field(..., min_length=3)
    domain: str = Field(..., min_length=2)
    support_status: str = Field(..., min_length=3)
    evidence_requirements: list[str] = Field(default_factory=list)
    freshness_hours: int | None = Field(default=None, ge=0)
    sufficiency_policy: str = Field(..., min_length=8)
    confidence_penalty_rules: list[str] = Field(default_factory=list)
    known_limitations: list[str] = Field(default_factory=list)
    activation_gate: str = Field(..., min_length=8)


class ProviderEvidenceContractCatalog(BaseModel):
    """Provider evidence contract catalog for the active policy pack."""

    contract_schema_version: str = Field(default="1.0.0", min_length=3)
    policy_pack_version: str = Field(..., min_length=3)
    provider_count: int = Field(..., ge=0)
    control_count: int = Field(..., ge=0)
    contract_count: int = Field(..., ge=0)
    support_status_counts: dict[str, int] = Field(default_factory=dict)
    contracts: list[ProviderEvidenceContract] = Field(default_factory=list)


class ProviderImplementationSignal(BaseModel):
    """Implementation evidence used to validate provider support claims."""

    provider: str = Field(..., min_length=2)
    adapter_registered: bool = False
    live_collector_present: bool = False
    collector_tests_present: bool = False
    docs_present: bool = False
    status: str = Field(..., min_length=3)
    notes: list[str] = Field(default_factory=list)


class ProviderContractConformanceCheck(BaseModel):
    """One executable conformance check for a provider evidence contract."""

    contract_id: str = Field(..., min_length=6)
    provider: str = Field(..., min_length=2)
    control_id: str = Field(..., min_length=3)
    support_status: str = Field(..., min_length=3)
    passed: bool
    required_signals: list[str] = Field(default_factory=list)
    satisfied_signals: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)


class ProviderContractConformanceReport(BaseModel):
    """Executable conformance result for provider evidence contracts."""

    conformance_schema_version: str = Field(default="1.0.0", min_length=3)
    policy_pack_version: str = Field(..., min_length=3)
    provider_count: int = Field(..., ge=0)
    control_count: int = Field(..., ge=0)
    active_contract_count: int = Field(..., ge=0)
    planned_contract_count: int = Field(..., ge=0)
    passed_contract_count: int = Field(..., ge=0)
    failed_contract_count: int = Field(..., ge=0)
    passed: bool
    provider_signals: list[ProviderImplementationSignal] = Field(default_factory=list)
    checks: list[ProviderContractConformanceCheck] = Field(default_factory=list)


class EvidenceSnapshot(BaseModel):
    """Replayable normalized evidence snapshot for one CRIS-SME assessment."""

    snapshot_schema_version: str = Field(default="1.0.0", min_length=3)
    snapshot_id: str = Field(..., min_length=8)
    generated_at: str = Field(..., min_length=10)
    collector_mode: str = Field(..., min_length=2)
    policy_pack_version: str = Field(..., min_length=3)
    profile_count: int = Field(..., ge=0)
    finding_count: int = Field(..., ge=0)
    non_compliant_finding_count: int = Field(..., ge=0)
    providers_in_scope: list[str] = Field(default_factory=list)
    control_ids: list[str] = Field(default_factory=list)
    profile_sha256: str = Field(..., min_length=64, max_length=64)
    finding_sha256: str = Field(..., min_length=64, max_length=64)
    snapshot_sha256: str = Field(..., min_length=64, max_length=64)
    profiles: list[dict[str, Any]] = Field(default_factory=list)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class AssessmentReplayResult(BaseModel):
    """Result of replaying a saved evidence snapshot through the current engine."""

    replay_schema_version: str = Field(default="1.0.0", min_length=3)
    snapshot_id: str = Field(..., min_length=8)
    replayed_at: str = Field(..., min_length=10)
    replayable: bool
    deterministic_match: bool
    policy_pack_version_at_capture: str = Field(..., min_length=3)
    policy_pack_version_at_replay: str = Field(..., min_length=3)
    collector_mode: str = Field(..., min_length=2)
    profile_hash_verified: bool
    finding_hash_verified: bool
    original_profile_sha256: str = Field(..., min_length=64, max_length=64)
    replay_profile_sha256: str = Field(..., min_length=64, max_length=64)
    original_finding_sha256: str = Field(..., min_length=64, max_length=64)
    replay_finding_sha256: str = Field(..., min_length=64, max_length=64)
    original_overall_risk_score: float = Field(..., ge=0.0, le=100.0)
    replayed_overall_risk_score: float = Field(..., ge=0.0, le=100.0)
    overall_risk_delta: float
    original_non_compliant_findings: int = Field(..., ge=0)
    replayed_non_compliant_findings: int = Field(..., ge=0)
    category_score_deltas: dict[str, float] = Field(default_factory=dict)
    change_reasons: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class EvidenceDiffResult(BaseModel):
    """Compare two evidence snapshots and classify what changed."""

    diff_schema_version: str = Field(default="1.0.0", min_length=3)
    current_snapshot_id: str = Field(..., min_length=8)
    previous_snapshot_id: str | None = None
    comparable: bool
    evidence_changed: bool
    policy_pack_changed: bool
    collector_mode_changed: bool
    profile_count_delta: int = 0
    finding_count_delta: int = 0
    non_compliant_finding_count_delta: int = 0
    added_control_ids: list[str] = Field(default_factory=list)
    removed_control_ids: list[str] = Field(default_factory=list)
    score_delta_reason: str = Field(..., min_length=8)


class AssessmentAssuranceSignal(BaseModel):
    """One non-risk assurance signal for an assessment artifact."""

    signal_id: str = Field(..., min_length=3)
    label: str = Field(..., min_length=3)
    score: float = Field(..., ge=0.0, le=100.0)
    weight: float = Field(..., ge=0.0, le=1.0)
    passed: bool
    explanation: str = Field(..., min_length=8)


class AssessmentAssuranceResult(BaseModel):
    """Trustworthiness score for the assessment artifact, separate from risk score."""

    assurance_schema_version: str = Field(default="1.0.0", min_length=3)
    assurance_score: float = Field(..., ge=0.0, le=100.0)
    assurance_level: str = Field(..., min_length=3)
    risk_score_impact: str = Field(..., min_length=8)
    signals: list[AssessmentAssuranceSignal] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class EvidenceGapBacklogItem(BaseModel):
    """One actionable evidence gap for improving assessment assurance or provider support."""

    gap_id: str = Field(..., min_length=6)
    gap_type: str = Field(..., min_length=3)
    provider: str = Field(..., min_length=2)
    domain: str = Field(..., min_length=2)
    control_id: str = Field(..., min_length=3)
    title: str = Field(..., min_length=5)
    priority: str = Field(..., min_length=3)
    evidence_gap: str = Field(..., min_length=3)
    recommended_action: str = Field(..., min_length=8)
    linked_finding_id: str | None = None
    support_status: str | None = None
    assurance_impact: str = Field(..., min_length=3)


class EvidenceGapBacklog(BaseModel):
    """Actionable backlog of evidence and provider-activation gaps."""

    backlog_schema_version: str = Field(default="1.0.0", min_length=3)
    item_count: int = Field(..., ge=0)
    high_priority_count: int = Field(..., ge=0)
    provider_counts: dict[str, int] = Field(default_factory=dict)
    domain_counts: dict[str, int] = Field(default_factory=dict)
    items: list[EvidenceGapBacklogItem] = Field(default_factory=list)


class ControlDriftAttributionItem(BaseModel):
    """Attribution for one control-level score or state movement."""

    control_id: str = Field(..., min_length=3)
    title: str | None = None
    category: str | None = None
    current_score: float = Field(..., ge=0.0, le=100.0)
    previous_score: float = Field(..., ge=0.0, le=100.0)
    delta: float
    direction: str = Field(..., min_length=3)
    attribution: str = Field(..., min_length=3)
    contributing_factors: list[str] = Field(default_factory=list)
    current_priority: str | None = None
    previous_priority: str | None = None


class ControlDriftAttributionReport(BaseModel):
    """Explain whether score movement came from evidence, policy, collector, or lifecycle drift."""

    attribution_schema_version: str = Field(default="1.0.0", min_length=3)
    comparable: bool
    current_generated_at: str | None = None
    previous_generated_at: str | None = None
    overall_risk_delta: float | None = None
    primary_attribution: str = Field(..., min_length=3)
    attribution_counts: dict[str, int] = Field(default_factory=dict)
    evidence_changed: bool = False
    policy_pack_changed: bool = False
    collector_mode_changed: bool = False
    lifecycle_changed: bool = False
    exception_state_changed: bool = False
    items: list[ControlDriftAttributionItem] = Field(default_factory=list)
    explanation: str = Field(..., min_length=8)


class PolicyPackChangelogEntry(BaseModel):
    """One policy-pack change entry for reproducible policy drift explanation."""

    version: str = Field(..., min_length=3)
    released_at: str = Field(..., min_length=10)
    change_type: str = Field(..., min_length=3)
    control_ids: list[str] = Field(default_factory=list)
    title: str = Field(..., min_length=5)
    summary: str = Field(..., min_length=8)
    risk_score_impact: str = Field(..., min_length=3)
    evidence_impact: str = Field(..., min_length=3)


class PolicyPackChangelog(BaseModel):
    """Machine-readable changelog for the active CRIS-SME policy pack."""

    changelog_schema_version: str = Field(default="1.0.0", min_length=3)
    active_policy_pack_version: str = Field(..., min_length=3)
    entry_count: int = Field(..., ge=0)
    entries: list[PolicyPackChangelogEntry] = Field(default_factory=list)


class ReportTrustBadge(BaseModel):
    """Compact stakeholder-facing trust label for a CRIS-SME report."""

    badge_schema_version: str = Field(default="1.0.0", min_length=3)
    label: str = Field(..., min_length=3)
    level: str = Field(..., min_length=3)
    assurance_score: float = Field(..., ge=0.0, le=100.0)
    replay_verified: bool
    rbom_present: bool
    provider_conformance_passed: bool
    high_priority_evidence_gaps: int = Field(..., ge=0)
    statement: str = Field(..., min_length=8)
    caveats: list[str] = Field(default_factory=list)
    risk_score_impact: str = Field(..., min_length=8)


class DecisionReviewQueueItem(BaseModel):
    """One stakeholder review item derived from risk, evidence, and lifecycle context."""

    review_id: str = Field(..., min_length=6)
    decision_type: str = Field(..., min_length=3)
    control_id: str = Field(..., min_length=3)
    finding_id: str | None = None
    title: str = Field(..., min_length=5)
    provider: str = Field(..., min_length=2)
    priority: str = Field(..., min_length=3)
    recommended_decision: str = Field(..., min_length=5)
    rationale: str = Field(..., min_length=8)
    evidence_sufficiency: str | None = None
    lifecycle_status: str | None = None
    owner_hint: str = Field(..., min_length=3)


class DecisionReviewQueue(BaseModel):
    """Governance review queue for explicit risk, evidence, and exception decisions."""

    queue_schema_version: str = Field(default="1.0.0", min_length=3)
    item_count: int = Field(..., ge=0)
    decision_type_counts: dict[str, int] = Field(default_factory=dict)
    priority_counts: dict[str, int] = Field(default_factory=dict)
    items: list[DecisionReviewQueueItem] = Field(default_factory=list)


class DecisionProvenanceNode(BaseModel):
    """One node in the CRIS-SME decision provenance graph."""

    node_id: str = Field(..., min_length=3)
    node_type: str = Field(..., min_length=3)
    label: str = Field(..., min_length=3)
    summary: str = Field(..., min_length=3)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionProvenanceEdge(BaseModel):
    """Directed provenance relationship between two decision graph nodes."""

    edge_id: str = Field(..., min_length=6)
    source_node_id: str = Field(..., min_length=3)
    target_node_id: str = Field(..., min_length=3)
    relationship: str = Field(..., min_length=3)
    explanation: str = Field(..., min_length=8)


class DecisionProvenancePath(BaseModel):
    """Compact path showing how evidence becomes a decision."""

    path_id: str = Field(..., min_length=6)
    finding_id: str | None = None
    control_id: str = Field(..., min_length=3)
    node_ids: list[str] = Field(default_factory=list)
    summary: str = Field(..., min_length=8)


class DecisionProvenanceGraph(BaseModel):
    """Traceable graph linking evidence, controls, findings, scores, assurance, and decisions."""

    graph_schema_version: str = Field(default="1.0.0", min_length=3)
    graph_model: str = Field(default="cris_sme_decision_provenance_graph_v1", min_length=3)
    node_count: int = Field(..., ge=0)
    edge_count: int = Field(..., ge=0)
    path_count: int = Field(..., ge=0)
    node_type_counts: dict[str, int] = Field(default_factory=dict)
    edge_type_counts: dict[str, int] = Field(default_factory=dict)
    nodes: list[DecisionProvenanceNode] = Field(default_factory=list)
    edges: list[DecisionProvenanceEdge] = Field(default_factory=list)
    top_decision_paths: list[DecisionProvenancePath] = Field(default_factory=list)


class ClaimVerification(BaseModel):
    """One stakeholder-facing claim with verification metadata."""

    claim_id: str = Field(..., min_length=6)
    claim_type: str = Field(..., min_length=3)
    audience: str = Field(..., min_length=3)
    statement: str = Field(..., min_length=8)
    verification_status: str = Field(..., min_length=3)
    confidence: float = Field(..., ge=0.0, le=1.0)
    source_sections: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    control_ids: list[str] = Field(default_factory=list)
    finding_ids: list[str] = Field(default_factory=list)
    provenance_node_ids: list[str] = Field(default_factory=list)
    rbom_artifact_refs: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    deterministic_score_impact: str = Field(..., min_length=8)


class ClaimVerificationPack(BaseModel):
    """Machine-readable pack of verifiable report claims."""

    pack_schema_version: str = Field(default="1.0.0", min_length=3)
    pack_name: str = Field(default="CRIS-SME Claim Verification Pack", min_length=3)
    generated_at: str | None = None
    claim_count: int = Field(..., ge=0)
    verified_claim_count: int = Field(..., ge=0)
    caveated_claim_count: int = Field(..., ge=0)
    claim_type_counts: dict[str, int] = Field(default_factory=dict)
    claims: list[ClaimVerification] = Field(default_factory=list)


class AssuranceCaseArgument(BaseModel):
    """One structured assurance argument with linked supporting claims and evidence."""

    argument_id: str = Field(..., min_length=6)
    top_claim: str = Field(..., min_length=8)
    conclusion: str = Field(..., min_length=3)
    confidence: float = Field(..., ge=0.0, le=1.0)
    supporting_claim_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    provenance_node_ids: list[str] = Field(default_factory=list)
    rbom_artifact_refs: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    residual_gaps: list[str] = Field(default_factory=list)
    reasoning: str = Field(..., min_length=8)


class AssuranceCase(BaseModel):
    """Structured assurance case for CRIS-SME report trustworthiness."""

    case_schema_version: str = Field(default="1.0.0", min_length=3)
    case_name: str = Field(default="CRIS-SME Assessment Assurance Case", min_length=3)
    generated_at: str | None = None
    overall_conclusion: str = Field(..., min_length=3)
    assurance_score: float = Field(..., ge=0.0, le=100.0)
    argument_count: int = Field(..., ge=0)
    supported_argument_count: int = Field(..., ge=0)
    caveated_argument_count: int = Field(..., ge=0)
    arguments: list[AssuranceCaseArgument] = Field(default_factory=list)
    open_caveats: list[str] = Field(default_factory=list)
    residual_gaps: list[str] = Field(default_factory=list)
    deterministic_score_impact: str = Field(..., min_length=8)
