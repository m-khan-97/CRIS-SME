# Structured assessment runner for CRIS-SME collection, evaluation, and scoring phases.
from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from cris_sme.collectors.aws_collector import AwsCollector
from cris_sme.collectors.azure_collector import AzureCollector
from cris_sme.collectors.mock_collector import MockCollector
from cris_sme.config import get_aws_collector_settings, get_azure_collector_settings
from cris_sme.controls import (
    evaluate_compute_controls,
    evaluate_data_controls,
    evaluate_governance_controls,
    evaluate_iam_controls,
    evaluate_iot_controls,
    evaluate_monitoring_controls,
    evaluate_network_controls,
)
from cris_sme.controls.registry import load_control_registry
from cris_sme.engine.assessment_context import (
    AssessmentResourceContext,
    build_assessment_resource_context,
)
from cris_sme.engine.compliance import (
    assess_compliance_mappings,
    load_compliance_mappings,
)
from cris_sme.engine.lineage import build_evidence_sufficiency_assessment, build_finding_trace
from cris_sme.engine.scoring import ScoringResult, score_findings
from cris_sme.models.cloud_profile import CloudProfile
from cris_sme.models.compliance_result import ComplianceAssessmentResult
from cris_sme.models.finding import Finding, FindingCategory
from cris_sme.models.platform import EvidenceSufficiency


class AssessmentPhase(str, Enum):
    """Assessment phases emitted by the structured runner."""

    COLLECT_EVIDENCE = "collect_evidence"
    EVALUATE_CONTROLS = "evaluate_controls"
    SCORE_FINDINGS = "score_findings"
    MAP_COMPLIANCE = "map_compliance"
    ASSESS_EVIDENCE_SUFFICIENCY = "assess_evidence_sufficiency"


class AssessmentEventStatus(str, Enum):
    """Progress event status for an assessment phase."""

    STARTED = "started"
    COMPLETED = "completed"


class AssessmentEvent(BaseModel):
    """One structured runner progress event."""

    sequence: int = Field(..., ge=1)
    phase: AssessmentPhase
    status: AssessmentEventStatus
    message: str = Field(..., min_length=3)
    generated_at: str = Field(..., min_length=10)
    detail: dict[str, Any] = Field(default_factory=dict)


class AssessmentControlSelection(BaseModel):
    """Describe the control scope applied to a runner execution."""

    requested_control_ids: list[str] = Field(default_factory=list)
    selected_control_ids: list[str] = Field(default_factory=list)
    selected_domains: list[str] = Field(default_factory=list)
    registry_filtered: bool = False


class AssessmentEvidenceSufficiencyOverview(BaseModel):
    """Run-level rollup of per-finding evidence sufficiency assessments."""

    sufficiency_counts: dict[str, int] = Field(default_factory=dict)
    sufficient_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    findings_requiring_attention: list[str] = Field(default_factory=list)


class AssessmentRunnerResult(BaseModel):
    """Core assessment result before report artifact generation."""

    collector_mode: str = Field(..., min_length=2)
    profiles: list[CloudProfile]
    findings: list[Finding]
    scoring_result: ScoringResult
    compliance_result: ComplianceAssessmentResult
    resource_context: AssessmentResourceContext
    evidence_sufficiency: AssessmentEvidenceSufficiencyOverview
    events: list[AssessmentEvent] = Field(default_factory=list)
    control_selection: AssessmentControlSelection = Field(
        default_factory=AssessmentControlSelection
    )


EventHandler = Callable[[AssessmentEvent], None]
ProfileCollector = Callable[[], list[CloudProfile]]
ControlEvaluator = Callable[[list[CloudProfile]], list[Finding]]


CONTROL_EVALUATORS: dict[FindingCategory, ControlEvaluator] = {
    FindingCategory.IAM: evaluate_iam_controls,
    FindingCategory.NETWORK: evaluate_network_controls,
    FindingCategory.DATA: evaluate_data_controls,
    FindingCategory.MONITORING: evaluate_monitoring_controls,
    FindingCategory.COMPUTE: evaluate_compute_controls,
    FindingCategory.GOVERNANCE: evaluate_governance_controls,
    FindingCategory.IOT: evaluate_iot_controls,
}


class AssessmentRunner:
    """Run CRIS-SME's core evidence-to-risk assessment phases."""

    def __init__(
        self,
        *,
        collector_mode: str = "mock",
        profile_collector: ProfileCollector | None = None,
        control_ids: Iterable[str] | None = None,
        event_handler: EventHandler | None = None,
    ) -> None:
        self.collector_mode = collector_mode
        self.profile_collector = profile_collector
        self.control_ids = [control_id.strip() for control_id in control_ids or []]
        self.event_handler = event_handler
        self._events: list[AssessmentEvent] = []

    def run(self) -> AssessmentRunnerResult:
        """Run collection, control evaluation, scoring, and compliance mapping."""
        self._events = []
        control_selection = self._build_control_selection()

        self._emit(
            AssessmentPhase.COLLECT_EVIDENCE,
            AssessmentEventStatus.STARTED,
            "Collecting provider-normalized evidence profiles.",
            {"collector_mode": self.collector_mode},
        )
        profiles = self._collect_profiles()
        self._emit(
            AssessmentPhase.COLLECT_EVIDENCE,
            AssessmentEventStatus.COMPLETED,
            "Evidence profile collection completed.",
            {
                "profile_count": len(profiles),
                "providers": sorted({profile.provider for profile in profiles}),
            },
        )

        self._emit(
            AssessmentPhase.EVALUATE_CONTROLS,
            AssessmentEventStatus.STARTED,
            "Evaluating deterministic CRIS-SME controls.",
            {
                "selected_control_ids": control_selection.selected_control_ids,
                "selected_domains": control_selection.selected_domains,
                "registry_filtered": control_selection.registry_filtered,
            },
        )
        findings = self._evaluate_controls(profiles, control_selection)
        resource_context = build_assessment_resource_context(profiles, findings)
        self._emit(
            AssessmentPhase.EVALUATE_CONTROLS,
            AssessmentEventStatus.COMPLETED,
            "Control evaluation completed.",
            {
                "finding_count": len(findings),
                "non_compliant_findings": sum(
                    1 for finding in findings if finding.is_risk
                ),
            },
        )

        self._emit(
            AssessmentPhase.SCORE_FINDINGS,
            AssessmentEventStatus.STARTED,
            "Scoring findings with deterministic risk model.",
        )
        scoring_result = score_findings(findings)
        self._emit(
            AssessmentPhase.SCORE_FINDINGS,
            AssessmentEventStatus.COMPLETED,
            "Finding scoring completed.",
            {
                "overall_risk_score": scoring_result.overall_risk_score,
                "prioritized_findings": len(scoring_result.prioritized_findings),
            },
        )

        self._emit(
            AssessmentPhase.MAP_COMPLIANCE,
            AssessmentEventStatus.STARTED,
            "Mapping findings to compliance and governance frameworks.",
        )
        compliance_result = assess_compliance_mappings(
            findings,
            load_compliance_mappings(),
        )
        self._emit(
            AssessmentPhase.MAP_COMPLIANCE,
            AssessmentEventStatus.COMPLETED,
            "Compliance mapping completed.",
            {
                "framework_count": len(compliance_result.frameworks_covered),
                "mapped_findings": len(compliance_result.mapped_findings),
            },
        )

        self._emit(
            AssessmentPhase.ASSESS_EVIDENCE_SUFFICIENCY,
            AssessmentEventStatus.STARTED,
            "Assessing evidence sufficiency for prioritized findings.",
        )
        evidence_sufficiency = self._assess_evidence_sufficiency(scoring_result)
        self._emit(
            AssessmentPhase.ASSESS_EVIDENCE_SUFFICIENCY,
            AssessmentEventStatus.COMPLETED,
            "Evidence sufficiency assessment completed.",
            {
                "sufficiency_counts": evidence_sufficiency.sufficiency_counts,
                "findings_requiring_attention": len(
                    evidence_sufficiency.findings_requiring_attention
                ),
            },
        )

        return AssessmentRunnerResult(
            collector_mode=self.collector_mode,
            profiles=profiles,
            findings=findings,
            scoring_result=scoring_result,
            compliance_result=compliance_result,
            resource_context=resource_context,
            evidence_sufficiency=evidence_sufficiency,
            events=list(self._events),
            control_selection=control_selection,
        )

    def _assess_evidence_sufficiency(
        self, scoring_result: ScoringResult
    ) -> AssessmentEvidenceSufficiencyOverview:
        sufficiency_counts: dict[str, int] = {}
        findings_requiring_attention: list[str] = []
        for item in scoring_result.prioritized_findings:
            trace = build_finding_trace(item)
            assessment = build_evidence_sufficiency_assessment(item, trace)
            sufficiency_counts[assessment.sufficiency.value] = (
                sufficiency_counts.get(assessment.sufficiency.value, 0) + 1
            )
            if assessment.sufficiency != EvidenceSufficiency.SUFFICIENT:
                findings_requiring_attention.append(trace.finding_id)

        total = sum(sufficiency_counts.values())
        sufficient = sufficiency_counts.get(EvidenceSufficiency.SUFFICIENT.value, 0)
        sufficient_ratio = (sufficient / total) if total else 1.0

        return AssessmentEvidenceSufficiencyOverview(
            sufficiency_counts=sufficiency_counts,
            sufficient_ratio=sufficient_ratio,
            findings_requiring_attention=findings_requiring_attention,
        )

    def _collect_profiles(self) -> list[CloudProfile]:
        if self.profile_collector is not None:
            return self.profile_collector()

        if self.collector_mode == "azure":
            return AzureCollector(
                settings=get_azure_collector_settings()
            ).collect_profiles()

        if self.collector_mode == "aws":
            return AwsCollector(
                settings=get_aws_collector_settings()
            ).collect_profiles()

        if self.collector_mode == "mock":
            return MockCollector().collect_profiles()

        raise ValueError(
            f"Unsupported collector mode '{self.collector_mode}'. Use 'mock', 'azure', or 'aws'."
        )

    def _build_control_selection(self) -> AssessmentControlSelection:
        if not self.control_ids:
            return AssessmentControlSelection()

        registry = load_control_registry()
        selected = registry.filter(control_ids=self.control_ids)
        selected_control_ids = [definition.control_id for definition in selected]
        selected_domains = sorted({definition.domain.value for definition in selected})
        missing_ids = sorted(set(self.control_ids).difference(selected_control_ids))
        if missing_ids:
            missing = ", ".join(missing_ids)
            raise KeyError(f"Control metadata v2 does not include: {missing}")

        return AssessmentControlSelection(
            requested_control_ids=list(self.control_ids),
            selected_control_ids=selected_control_ids,
            selected_domains=selected_domains,
            registry_filtered=True,
        )

    def _evaluate_controls(
        self,
        profiles: list[CloudProfile],
        control_selection: AssessmentControlSelection,
    ) -> list[Finding]:
        if control_selection.registry_filtered:
            selected_control_ids = set(control_selection.selected_control_ids)
            selected_domains = {
                FindingCategory(domain) for domain in control_selection.selected_domains
            }
            findings = [
                finding
                for domain in selected_domains
                for finding in CONTROL_EVALUATORS[domain](profiles)
            ]
            return [
                finding
                for finding in findings
                if finding.control_id in selected_control_ids
            ]

        return [
            finding
            for evaluator in CONTROL_EVALUATORS.values()
            for finding in evaluator(profiles)
        ]

    def _emit(
        self,
        phase: AssessmentPhase,
        status: AssessmentEventStatus,
        message: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        event = AssessmentEvent(
            sequence=len(self._events) + 1,
            phase=phase,
            status=status,
            message=message,
            generated_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            detail=detail or {},
        )
        self._events.append(event)
        if self.event_handler is not None:
            self.event_handler(event)
