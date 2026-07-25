# Deterministic-ID query tools backing the CRIS-SME MCP tool surface.
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from cris_sme.engine.lifecycle import load_exception_registry, load_mute_rules
from cris_sme.models.platform import ExceptionRecord, MuteRule
from cris_sme.reporting.history import load_report_history

DEFAULT_OUTPUT_DIR = Path("outputs/reports")
DEFAULT_REPORT_FILENAME = "cris_sme_report.json"


def load_report(path: str | Path | None = None) -> dict[str, Any]:
    """Load the CRIS-SME JSON report from disk."""
    if path is None:
        output_dir = Path(os.getenv("CRIS_SME_OUTPUT_DIR", DEFAULT_OUTPUT_DIR))
        path = output_dir / DEFAULT_REPORT_FILENAME
    report_path = Path(path)
    return json.loads(report_path.read_text(encoding="utf-8"))


def get_assessment_summary(report: dict[str, Any]) -> dict[str, Any]:
    """Return headline assessment identifiers and risk scores."""
    return {
        "generated_at": report.get("generated_at"),
        "collector_mode": report.get("collector_mode"),
        "report_schema_version": report.get("report_schema_version"),
        "overall_risk_score": report.get("overall_risk_score"),
        "category_scores": report.get("category_scores", {}),
        "adjusted_risk_scores": report.get("adjusted_risk_scores", {}),
        "finding_count": len(report.get("prioritized_risks", [])),
        "finding_lifecycle_summary": report.get("finding_lifecycle_summary", {}),
        "evidence_snapshot_id": report.get("evidence_snapshot", {}).get("snapshot_id"),
        "risk_bill_of_materials_sha256": report.get("risk_bill_of_materials", {}).get(
            "canonical_report_sha256"
        ),
    }


def list_assessment_history(history_dir: str | Path = "outputs/reports/history") -> list[dict[str, Any]]:
    """Return a deterministic-ID summary of previously archived assessment runs."""
    history_reports = load_report_history(history_dir)
    return [
        {
            "generated_at": historical.get("generated_at"),
            "collector_mode": historical.get("collector_mode"),
            "overall_risk_score": historical.get("overall_risk_score"),
            "finding_count": len(historical.get("prioritized_risks", [])),
            "evidence_snapshot_id": historical.get("evidence_snapshot", {}).get("snapshot_id"),
        }
        for historical in history_reports
    ]


def list_findings(
    report: dict[str, Any],
    *,
    severity: str | None = None,
    category: str | None = None,
    organization: str | None = None,
    control_id: str | None = None,
    lifecycle_status: str | None = None,
) -> list[dict[str, Any]]:
    """Return prioritized findings, optionally filtered, citing finding_id/control_id."""
    results = []
    for risk in report.get("prioritized_risks", []):
        if severity and str(risk.get("severity", "")).lower() != severity.lower():
            continue
        if category and str(risk.get("category", "")).lower() != category.lower():
            continue
        if organization and risk.get("organization") != organization:
            continue
        if control_id and risk.get("control_id") != control_id:
            continue
        risk_lifecycle_status = risk.get("lifecycle", {}).get("status")
        if lifecycle_status and risk_lifecycle_status != lifecycle_status:
            continue
        results.append(
            {
                "finding_id": risk.get("finding_id"),
                "control_id": risk.get("control_id"),
                "title": risk.get("title"),
                "severity": risk.get("severity"),
                "category": risk.get("category"),
                "score": risk.get("score"),
                "priority": risk.get("priority"),
                "organization": risk.get("organization"),
                "resource_scope": risk.get("resource_scope"),
                "asset_ids": risk.get("asset_ids", []),
                "evidence_ids": risk.get("evidence_ids", []),
                "lifecycle_status": risk_lifecycle_status,
            }
        )
    return results


def get_finding(report: dict[str, Any], finding_id: str) -> dict[str, Any] | None:
    """Return the full prioritized-risk record for one finding_id, or None."""
    for risk in report.get("prioritized_risks", []):
        if risk.get("finding_id") == finding_id:
            return risk
    return None


def list_evidence(
    report: dict[str, Any],
    *,
    finding_id: str | None = None,
    control_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return evidence records, optionally filtered, citing evidence_id/finding_id."""
    records = report.get("resource_context", {}).get("evidence_records", [])
    results = []
    for record in records:
        payload = record.get("payload", {})
        if finding_id and payload.get("finding_id") != finding_id:
            continue
        if control_id and payload.get("control_id") != control_id:
            continue
        results.append(
            {
                "evidence_id": record.get("evidence_id"),
                "provider": record.get("provider"),
                "collector": record.get("collector"),
                "record_type": record.get("record_type"),
                "observation_class": record.get("observation_class"),
                "observed_at": record.get("observed_at"),
                "finding_id": payload.get("finding_id"),
                "control_id": payload.get("control_id"),
                "resource_scope": payload.get("resource_scope"),
                "statement": payload.get("statement"),
            }
        )
    return results


def list_claims(
    report: dict[str, Any],
    *,
    claim_type: str | None = None,
    verification_status: str | None = None,
) -> list[dict[str, Any]]:
    """Return assurance claims, optionally filtered, citing claim_id/evidence_refs."""
    claims = report.get("claim_verification_pack", {}).get("claims", [])
    results = []
    for claim in claims:
        if claim_type and claim.get("claim_type") != claim_type:
            continue
        if verification_status and claim.get("verification_status") != verification_status:
            continue
        results.append(
            {
                "claim_id": claim.get("claim_id"),
                "claim_type": claim.get("claim_type"),
                "audience": claim.get("audience"),
                "statement": claim.get("statement"),
                "verification_status": claim.get("verification_status"),
                "confidence": claim.get("confidence"),
                "evidence_refs": claim.get("evidence_refs", []),
            }
        )
    return results


def list_exceptions(
    *,
    exception_registry: list[ExceptionRecord] | None = None,
) -> list[dict[str, Any]]:
    """Return approved finding exceptions, citing exception_id/control_id."""
    exceptions = (
        exception_registry if exception_registry is not None else load_exception_registry()
    )
    return [exception.model_dump(mode="json") for exception in exceptions]


def list_mute_rules(
    *,
    mute_rule_registry: list[MuteRule] | None = None,
) -> list[dict[str, Any]]:
    """Return operational mute rules, citing rule_id/control_id."""
    rules = mute_rule_registry if mute_rule_registry is not None else load_mute_rules()
    return [rule.model_dump(mode="json") for rule in rules]


def list_action_plan(
    report: dict[str, Any],
    *,
    phase_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return 30-day action plan items, optionally filtered by phase_id."""
    phases = report.get("action_plan_30_day", {}).get("phases", [])
    results = []
    for phase in phases:
        if phase_id and phase.get("phase_id") != phase_id:
            continue
        for action in phase.get("actions", []):
            results.append(
                {
                    "phase_id": phase.get("phase_id"),
                    "phase_label": phase.get("label"),
                    "time_window": phase.get("time_window"),
                    "control_id": action.get("control_id"),
                    "title": action.get("title"),
                    "organization": action.get("organization"),
                    "category": action.get("category"),
                    "priority": action.get("priority"),
                    "score": action.get("score"),
                    "remediation_cost_tier": action.get("remediation_cost_tier"),
                    "remediation_summary": action.get("remediation_summary"),
                    "action_rationale": action.get("action_rationale"),
                }
            )
    return results
