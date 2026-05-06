# Structured JSON reporting for machine-readable CRIS-SME outputs.
from __future__ import annotations

import json
from pathlib import Path

from cris_sme.engine.graph_context import build_graph_context_summary
from cris_sme.engine.lineage import (
    build_collector_coverage,
    build_confidence_assessment,
    build_evidence_sufficiency_assessment,
    build_finding_trace,
    build_run_metadata,
    build_stable_finding_id,
)
from cris_sme.engine.remediation import (
    COST_TIER_WEIGHTS,
    build_budget_aware_remediation_plan,
    budget_fit_profile_ids,
)
from cris_sme.engine.remediation_simulator import build_remediation_simulation
from cris_sme.engine.action_plan import build_30_day_action_plan
from cris_sme.engine.benchmark import (
    build_benchmark_comparison,
    build_benchmark_observation,
    load_benchmark_dataset,
)
from cris_sme.engine.confidence import summarize_confidence_calibration
from cris_sme.engine.evidence_gap_backlog import build_evidence_gap_backlog
from cris_sme.engine.native_validation import build_native_validation_summary
from cris_sme.engine.policy_changelog import load_policy_pack_changelog
from cris_sme.engine.provider_conformance import (
    build_provider_contract_conformance_report,
)
from cris_sme.engine.provider_contracts import build_provider_evidence_contract_catalog
from cris_sme.engine.uk_readiness import build_cyber_essentials_readiness
from cris_sme.models.compliance_result import ComplianceAssessmentResult
from cris_sme.engine.scoring import ScoredFinding, ScoringResult
from cris_sme.models.cloud_profile import CloudProfile
from cris_sme.models.finding import Finding
from cris_sme.policies import load_policy_pack_metadata
from cris_sme.reporting.executive_pack import build_executive_pack
from cris_sme.reporting.insurance_pack import build_cyber_insurance_evidence_pack


def build_json_report(
    *,
    profiles: list[CloudProfile],
    findings: list[Finding],
    scoring_result: ScoringResult,
    compliance_result: ComplianceAssessmentResult | None = None,
) -> dict[str, object]:
    """Build a stable JSON-style report for demos, notebooks, and export."""
    remediation_plan = build_budget_aware_remediation_plan(
        scoring_result.prioritized_findings
    )
    collector_coverage = build_collector_coverage(profiles)
    provider_evidence_contracts = build_provider_evidence_contract_catalog()
    report: dict[str, object] = {
        "report_schema_version": "2.0.0",
        "summary": scoring_result.summary,
        "overall_risk_score": scoring_result.overall_risk_score,
        "category_scores": scoring_result.category_scores,
        "collector_coverage": [item.model_dump() for item in collector_coverage],
        "policy_pack_changelog": load_policy_pack_changelog().model_dump(mode="json"),
        "provider_evidence_contracts": provider_evidence_contracts.model_dump(),
        "provider_contract_conformance": build_provider_contract_conformance_report(
            provider_evidence_contracts
        ).model_dump(),
        "evaluation_dataset": _build_evaluation_dataset_summary(profiles),
        "confidence_calibration": summarize_confidence_calibration(
            scoring_result.prioritized_findings
        ),
        "native_validation": build_native_validation_summary(
            profiles,
            scoring_result.prioritized_findings,
        ),
        "evaluation_context": {
            "evaluated_profiles": len(profiles),
            "generated_findings": len(findings),
            "non_compliant_findings": scoring_result.non_compliant_findings,
        },
        "organizations": [
            {
                "organization_id": profile.organization_id,
                "organization_name": profile.organization_name,
                "provider": profile.provider,
                "sector": profile.sector,
                "tenant_scope": profile.tenant_scope,
                "collection_details": _build_collection_details(profile),
            }
            for profile in profiles
        ],
        "prioritized_risks": [
            _prioritized_risk_item(item)
            for item in scoring_result.prioritized_findings
        ],
        "budget_aware_remediation": remediation_plan.model_dump(),
        "remediation_simulation": build_remediation_simulation(
            scoring_result
        ).model_dump(),
        "action_plan_30_day": build_30_day_action_plan(
            scoring_result.prioritized_findings
        ).model_dump(),
        "cyber_essentials_readiness": build_cyber_essentials_readiness(findings),
        "graph_context": build_graph_context_summary(
            profiles,
            scoring_result.prioritized_findings,
        ),
    }
    report["evidence_gap_backlog"] = build_evidence_gap_backlog(report).model_dump()

    if compliance_result is not None:
        report["compliance"] = compliance_result.model_dump()

    report["cyber_insurance_evidence"] = build_cyber_insurance_evidence_pack(report)
    benchmark_dataset = load_benchmark_dataset()
    report["benchmark_observation"] = build_benchmark_observation(report).model_dump()
    report["benchmark_comparison"] = build_benchmark_comparison(
        report,
        benchmark_dataset,
    )
    report["executive_pack"] = build_executive_pack(report)
    report["run_metadata"] = build_run_metadata(
        generated_at=str(report.get("generated_at") or "1970-01-01T00:00:00Z"),
        collector_mode=str(report.get("collector_mode", "unknown")),
        schema_version=str(report["report_schema_version"]),
        narrator_enabled=False,
        providers_in_scope=[profile.provider for profile in profiles],
        policy_pack=load_policy_pack_metadata(),
        collector_coverage=collector_coverage,
    ).model_dump()

    return report


def _prioritized_risk_item(item: ScoredFinding) -> dict[str, object]:
    """Build a traceable prioritized-risk record from one scored finding."""
    trace = build_finding_trace(item)
    confidence = build_confidence_assessment(item)
    evidence_sufficiency = build_evidence_sufficiency_assessment(item, trace)
    finding_id = build_stable_finding_id(item.finding)
    return {
        "finding_id": finding_id,
        "control_id": item.finding.control_id,
        "rule_version": str(item.finding.metadata.get("rule_version", "1.0.0")),
        "title": item.finding.title,
        "organization": item.finding.metadata.get("organization_name"),
        "organization_id": item.finding.metadata.get("organization_id"),
        "provider": item.finding.metadata.get("provider", "azure"),
        "category": item.finding.category.value,
        "severity": item.finding.severity.value,
        "score": item.score,
        "priority": item.priority,
        "resource_scope": item.finding.resource_scope,
        "evidence": item.finding.evidence,
        "evidence_quality": {
            "observation_class": trace.observation_class.value,
            "sufficiency": evidence_sufficiency.sufficiency.value,
            "direct_evidence_count": trace.direct_evidence_count,
            "inferred_evidence_count": trace.inferred_evidence_count,
            "unavailable_evidence_count": trace.unavailable_evidence_count,
            "provider_support": evidence_sufficiency.provider_support,
            "missing_requirements": evidence_sufficiency.missing_requirements,
        },
        "finding_trace": trace.model_dump(),
        "evidence_sufficiency": evidence_sufficiency.model_dump(),
        "confidence_calibration": confidence.model_dump(),
        "remediation_summary": item.finding.remediation_summary,
        "remediation_cost_tier": (
            item.finding.remediation_cost_tier.value
            if item.finding.remediation_cost_tier is not None
            else None
        ),
        "remediation_value_score": _remediation_value_score(item),
        "budget_fit_profiles": budget_fit_profile_ids(item.finding.remediation_cost_tier),
        "mapping": item.finding.mapping,
        "score_breakdown": item.breakdown.model_dump(),
        "lifecycle": {
            "status": "open",
            "status_reason": "Active non-compliant finding in current assessment.",
            "first_seen": None,
            "last_seen": None,
            "previous_seen": None,
            "is_new": True,
            "seen_count": 1,
            "recurrence_count": 0,
        },
        "decision_rationale": (
            "Deterministic scoring prioritization using severity, exposure, data sensitivity, "
            "confidence calibration, and remediation effort factors."
        ),
    }


def _build_collection_details(profile: CloudProfile) -> dict[str, object]:
    """Build a compact, reader-friendly collection summary for a profile."""
    metadata = profile.metadata
    details: dict[str, object] = {
        "profile_source": metadata.get("profile_source", "unknown"),
    }

    for key in (
        "dataset_source_type",
        "authorization_basis",
        "dataset_use",
        "collection_mode",
        "collector_stage",
        "subscription_id",
        "subscription_display_name",
        "subscription_state",
        "tenant_id",
        "iam_collection_mode",
        "identity_observability",
        "network_collection_mode",
        "data_collection_mode",
        "monitoring_collection_mode",
        "compute_collection_mode",
        "governance_collection_mode",
        "native_recommendation_collection_mode",
    ):
        if key in metadata:
            details[key] = metadata[key]

    evidence_counts = {
        "privileged_assignment_count": metadata.get("privileged_assignment_count"),
        "privileged_principal_count": metadata.get("privileged_principal_count"),
        "privileged_user_assignment_count": metadata.get(
            "privileged_user_assignment_count"
        ),
        "privileged_service_principal_assignment_count": metadata.get(
            "privileged_service_principal_assignment_count"
        ),
        "conditional_access_policy_count": metadata.get(
            "conditional_access_policy_count"
        ),
        "signed_in_user_directory_role_count": metadata.get(
            "signed_in_user_directory_role_count"
        ),
        "visible_directory_role_catalog_count": metadata.get(
            "visible_directory_role_catalog_count"
        ),
        "service_principal_role_assignment_count": metadata.get(
            "service_principal_role_assignment_count"
        ),
        "disabled_service_principal_count": metadata.get(
            "disabled_service_principal_count"
        ),
        "storage_account_count": metadata.get("storage_account_count"),
        "sql_server_count": metadata.get("sql_server_count"),
        "sql_database_count": metadata.get("sql_database_count"),
        "activity_log_alert_count": metadata.get("activity_log_alert_count"),
        "logic_app_workflow_count": metadata.get("logic_app_workflow_count"),
        "virtual_machine_count": metadata.get("virtual_machine_count"),
        "vm_backup_protected_count": metadata.get("vm_backup_protected_count"),
        "linux_password_auth_enabled_vm_count": metadata.get(
            "linux_password_auth_enabled_vm_count"
        ),
        "governance_resource_count": metadata.get("governance_resource_count"),
        "policy_assignment_count": metadata.get("policy_assignment_count"),
        "native_security_recommendation_count": metadata.get(
            "native_security_recommendation_count"
        ),
        "native_unhealthy_recommendation_count": metadata.get(
            "native_unhealthy_recommendation_count"
        ),
    }
    details["evidence_counts"] = {
        key: value for key, value in evidence_counts.items() if value is not None
    }

    if "conditional_access_accessible" in metadata:
        details["conditional_access_accessible"] = metadata[
            "conditional_access_accessible"
        ]
    if "conditional_access_enforced_for_admins" in metadata:
        details["conditional_access_enforced_for_admins"] = metadata[
            "conditional_access_enforced_for_admins"
        ]
    if "signed_in_user_is_directory_admin" in metadata:
        details["signed_in_user_is_directory_admin"] = metadata[
            "signed_in_user_is_directory_admin"
        ]
    if "signed_in_user_directory_roles_visible" in metadata:
        details["signed_in_user_directory_roles_visible"] = metadata[
            "signed_in_user_directory_roles_visible"
        ]
    if "directory_role_catalog_visible" in metadata:
        details["directory_role_catalog_visible"] = metadata[
            "directory_role_catalog_visible"
        ]

    if "note" in metadata:
        details["note"] = metadata["note"]

    return details


def _remediation_value_score(item: object) -> float | None:
    """Return the remediation value score if a budget-aware recommendation exists."""
    if not isinstance(item, ScoredFinding):
        return None
    tier = item.finding.remediation_cost_tier
    if tier is None:
        return None
    return round(item.score / COST_TIER_WEIGHTS[tier], 2)


def _build_evaluation_dataset_summary(
    profiles: list[CloudProfile],
) -> dict[str, object]:
    """Summarize dataset provenance across the current assessment profiles."""
    source_types = sorted(
        {
            str(profile.metadata.get("dataset_source_type"))
            for profile in profiles
            if profile.metadata.get("dataset_source_type")
        }
    )
    authorization_bases = sorted(
        {
            str(profile.metadata.get("authorization_basis"))
            for profile in profiles
            if profile.metadata.get("authorization_basis")
        }
    )
    dataset_uses = sorted(
        {
            str(profile.metadata.get("dataset_use"))
            for profile in profiles
            if profile.metadata.get("dataset_use")
        }
    )
    return {
        "profile_count": len(profiles),
        "source_types": source_types,
        "authorization_bases": authorization_bases,
        "dataset_uses": dataset_uses,
        "note": (
            "CRIS-SME evaluation datasets should come from synthetic profiles, owned or "
            "explicitly authorized cloud environments, provider sandboxes, or intentionally "
            "vulnerable training labs rather than arbitrary public infrastructure."
        ),
    }


def write_json_report(report: dict[str, object], output_path: str | Path) -> Path:
    """Write a JSON report to disk and return the resolved output path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path
