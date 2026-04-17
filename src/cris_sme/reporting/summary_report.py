# Concise summary reporting for executive and research-facing CRIS-SME outputs.
from __future__ import annotations

from collections import Counter
from pathlib import Path

from cris_sme.engine.confidence import summarize_confidence_calibration
from cris_sme.engine.remediation import build_budget_aware_remediation_plan
from cris_sme.engine.scoring import ScoringResult
from cris_sme.models.cloud_profile import CloudProfile
from cris_sme.reporting.insurance_pack import build_cyber_insurance_evidence_pack


def build_summary_report(
    *,
    profiles: list[CloudProfile],
    scoring_result: ScoringResult,
    top_n: int = 3,
) -> str:
    """Build a concise narrative summary suitable for demos and reports."""
    organizations = ", ".join(
        f"{profile.organization_name} ({profile.provider})" for profile in profiles
    )
    top_items = scoring_result.prioritized_findings[:top_n]

    if top_items:
        top_risks = "; ".join(
            (
                f"{item.finding.control_id} in "
                f"{item.finding.metadata.get('organization_name', 'unknown organization')} "
                f"scored {item.score:.2f} ({item.priority})"
            )
            for item in top_items
        )
    else:
        top_risks = "No non-compliant findings were identified."

    priority_counter = Counter(item.priority for item in scoring_result.prioritized_findings)
    priority_summary = ", ".join(
        f"{label}: {count}" for label, count in sorted(priority_counter.items())
    ) or "No active priorities"
    collection_summary = _build_collection_summary(profiles)
    remediation_summary = _build_remediation_summary(scoring_result)
    insurance_summary = _build_insurance_summary(profiles, scoring_result)
    confidence_summary = _build_confidence_summary(scoring_result)

    return (
        f"CRIS-SME evaluated {len(profiles)} profile(s): {organizations}. "
        f"The overall risk score is {scoring_result.overall_risk_score:.2f}/100, with "
        f"{scoring_result.non_compliant_findings} non-compliant finding(s). "
        f"Collection context: {collection_summary}. "
        f"Confidence calibration: {confidence_summary}. "
        f"Budget-aware remediation: {remediation_summary}. "
        f"Cyber insurance evidence: {insurance_summary}. "
        f"Priority distribution: {priority_summary}. "
        f"Top risk observations: {top_risks}"
    )


def write_summary_report(summary: str, output_path: str | Path) -> Path:
    """Write a plain-text summary report to disk and return the resolved output path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(summary + "\n", encoding="utf-8")
    return path


def _build_collection_summary(profiles: list[CloudProfile]) -> str:
    """Build a concise summary of how profile evidence was collected."""
    fragments: list[str] = []

    for profile in profiles:
        metadata = profile.metadata
        profile_source = str(metadata.get("profile_source", "unknown"))
        provider = profile.provider

        if profile_source == "synthetic":
            fragments.append(f"{profile.organization_name} uses synthetic mock posture data")
            continue

        mode_parts = [
            str(metadata.get("iam_collection_mode", "iam-default")),
            str(metadata.get("network_collection_mode", "network-default")),
            str(metadata.get("data_collection_mode", "data-default")),
            str(metadata.get("monitoring_collection_mode", "monitoring-default")),
            str(metadata.get("compute_collection_mode", "compute-default")),
            str(metadata.get("governance_collection_mode", "governance-default")),
        ]
        mode_summary = ", ".join(mode_parts)

        evidence_bits: list[str] = []
        if "privileged_assignment_count" in metadata:
            evidence_bits.append(
                f"{metadata['privileged_assignment_count']} privileged assignment(s)"
            )
        if "signed_in_user_directory_role_count" in metadata:
            evidence_bits.append(
                f"{metadata['signed_in_user_directory_role_count']} visible Entra directory role(s)"
            )
        if "virtual_machine_count" in metadata:
            evidence_bits.append(f"{metadata['virtual_machine_count']} VM(s)")
        if "storage_account_count" in metadata:
            evidence_bits.append(f"{metadata['storage_account_count']} storage account(s)")
        if "sql_database_count" in metadata:
            evidence_bits.append(f"{metadata['sql_database_count']} SQL database(s)")
        if "policy_assignment_count" in metadata:
            evidence_bits.append(f"{metadata['policy_assignment_count']} policy assignment(s)")

        evidence_summary = ", ".join(evidence_bits) if evidence_bits else "limited asset counts"
        fragments.append(
            f"{profile.organization_name} uses live {provider} evidence with {mode_summary}; observed {evidence_summary}"
        )

    return " | ".join(fragments) if fragments else "No collection context available"


def _build_remediation_summary(scoring_result: ScoringResult) -> str:
    """Summarize the most practical budget-aware remediation options."""
    plan = build_budget_aware_remediation_plan(scoring_result.prioritized_findings)
    by_id = {profile.profile_id: profile for profile in plan.budget_profiles}

    free_profile = by_id.get("free_this_week")
    lean_profile = by_id.get("under_200_month")
    if free_profile is None or lean_profile is None:
        return "no budget-aware action packs available"

    return (
        f"{free_profile.total_recommended} free fix(es) can be prioritized immediately, "
        f"and {lean_profile.total_recommended} action(s) fit within GBP200/month"
    )


def _build_insurance_summary(
    profiles: list[CloudProfile],
    scoring_result: ScoringResult,
) -> str:
    """Summarize insurer-facing evidence readiness from existing findings."""
    report_stub = {
        "generated_at": "not-yet-written",
        "collector_mode": "summary",
        "overall_risk_score": scoring_result.overall_risk_score,
        "organizations": [
            {
                "organization_id": profile.organization_id,
                "organization_name": profile.organization_name,
                "provider": profile.provider,
                "sector": profile.sector,
            }
            for profile in profiles
        ],
        "prioritized_risks": [
            {
                "control_id": item.finding.control_id,
                "title": item.finding.title,
                "priority": item.priority,
                "score": item.score,
                "evidence": item.finding.evidence,
                "remediation_summary": item.finding.remediation_summary,
            }
            for item in scoring_result.prioritized_findings
        ],
    }
    insurance_pack = build_cyber_insurance_evidence_pack(report_stub)
    readiness = insurance_pack.get("readiness_summary", {})
    if not isinstance(readiness, dict):
        return "insurer-facing readiness data unavailable"
    return (
        f"{int(readiness.get('met_count', 0))} question(s) are met, "
        f"{int(readiness.get('partial_count', 0))} are partial, and "
        f"{int(readiness.get('not_met_count', 0))} are not met "
        f"(readiness score {float(readiness.get('readiness_score', 0.0)):.2f})"
    )


def _build_confidence_summary(scoring_result: ScoringResult) -> str:
    """Summarize the new confidence calibration layer for narrative reporting."""
    calibration = summarize_confidence_calibration(scoring_result.prioritized_findings)
    status_counts = calibration.get("status_counts", {})
    if not isinstance(status_counts, dict):
        status_counts = {}
    status_text = ", ".join(
        f"{status}: {count}" for status, count in sorted(status_counts.items())
    ) or "no calibration states recorded"
    return (
        f"average observed confidence {float(calibration.get('average_observed_confidence', 0.0)):.2f}, "
        f"average calibrated confidence {float(calibration.get('average_calibrated_confidence', 0.0)):.2f}, "
        f"statuses: {status_text}"
    )
