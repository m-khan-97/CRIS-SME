# Structured JSON reporting for machine-readable CRIS-SME outputs.
from __future__ import annotations

import json
from pathlib import Path

from cris_sme.engine.remediation import (
    COST_TIER_WEIGHTS,
    build_budget_aware_remediation_plan,
    budget_fit_profile_ids,
)
from cris_sme.engine.confidence import summarize_confidence_calibration
from cris_sme.engine.action_plan import build_30_day_action_plan
from cris_sme.models.compliance_result import ComplianceAssessmentResult
from cris_sme.engine.scoring import ScoredFinding, ScoringResult
from cris_sme.models.cloud_profile import CloudProfile
from cris_sme.models.finding import Finding
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
    report: dict[str, object] = {
        "report_schema_version": "1.5.0",
        "summary": scoring_result.summary,
        "overall_risk_score": scoring_result.overall_risk_score,
        "category_scores": scoring_result.category_scores,
        "confidence_calibration": summarize_confidence_calibration(
            scoring_result.prioritized_findings
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
            {
                "control_id": item.finding.control_id,
                "title": item.finding.title,
                "organization": item.finding.metadata.get("organization_name"),
                "provider": item.finding.metadata.get("provider", "azure"),
                "category": item.finding.category.value,
                "severity": item.finding.severity.value,
                "score": item.score,
                "priority": item.priority,
                "resource_scope": item.finding.resource_scope,
                "evidence": item.finding.evidence,
                "remediation_summary": item.finding.remediation_summary,
                "remediation_cost_tier": (
                    item.finding.remediation_cost_tier.value
                    if item.finding.remediation_cost_tier is not None
                    else None
                ),
                "remediation_value_score": _remediation_value_score(item),
                "budget_fit_profiles": budget_fit_profile_ids(
                    item.finding.remediation_cost_tier
                ),
                "confidence_calibration": {
                    "observed_confidence": item.breakdown.observed_confidence,
                    "calibrated_confidence": item.breakdown.calibrated_confidence,
                    "calibration_status": item.breakdown.calibration_status,
                },
                "mapping": item.finding.mapping,
                "score_breakdown": item.breakdown.model_dump(),
            }
            for item in scoring_result.prioritized_findings
        ],
        "budget_aware_remediation": remediation_plan.model_dump(),
        "action_plan_30_day": build_30_day_action_plan(
            scoring_result.prioritized_findings
        ).model_dump(),
    }

    if compliance_result is not None:
        report["compliance"] = compliance_result.model_dump()

    report["cyber_insurance_evidence"] = build_cyber_insurance_evidence_pack(report)

    return report


def _build_collection_details(profile: CloudProfile) -> dict[str, object]:
    """Build a compact, reader-friendly collection summary for a profile."""
    metadata = profile.metadata
    details: dict[str, object] = {
        "profile_source": metadata.get("profile_source", "unknown"),
    }

    for key in (
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
    }
    details["evidence_counts"] = {
        key: value for key, value in evidence_counts.items() if value is not None
    }

    if "conditional_access_accessible" in metadata:
        details["conditional_access_accessible"] = metadata[
            "conditional_access_accessible"
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


def write_json_report(report: dict[str, object], output_path: str | Path) -> Path:
    """Write a JSON report to disk and return the resolved output path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path
