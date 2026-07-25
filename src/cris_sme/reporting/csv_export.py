# CSV export helpers for SME/MSP spreadsheet workflows.
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def write_csv_export_bundle(
    report: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write spreadsheet-friendly CRIS-SME CSV exports."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "findings_csv": target_dir / "cris_sme_findings.csv",
        "assets_csv": target_dir / "cris_sme_assets.csv",
        "evidence_csv": target_dir / "cris_sme_evidence.csv",
        "actions_csv": target_dir / "cris_sme_actions.csv",
    }
    _write_findings_csv(report, paths["findings_csv"])
    _write_assets_csv(report, paths["assets_csv"])
    _write_evidence_csv(report, paths["evidence_csv"])
    _write_actions_csv(report, paths["actions_csv"])
    return paths


def _write_findings_csv(report: dict[str, Any], output_path: Path) -> None:
    rows = _list_of_dicts(report.get("prioritized_risks"))
    _write_rows(
        output_path,
        [
            "finding_id",
            "control_id",
            "title",
            "category",
            "severity",
            "priority",
            "score",
            "provider",
            "organization",
            "organization_id",
            "resource_scope",
            "asset_ids",
            "evidence_ids",
            "lifecycle_status",
            "evidence_sufficiency",
            "remediation_cost_tier",
            "remediation_summary",
            "mapping",
        ],
        [
            {
                "finding_id": row.get("finding_id", ""),
                "control_id": row.get("control_id", ""),
                "title": row.get("title", ""),
                "category": row.get("category", ""),
                "severity": row.get("severity", ""),
                "priority": row.get("priority", ""),
                "score": row.get("score", ""),
                "provider": row.get("provider", ""),
                "organization": row.get("organization", ""),
                "organization_id": row.get("organization_id", ""),
                "resource_scope": row.get("resource_scope", ""),
                "asset_ids": _join_list(row.get("asset_ids")),
                "evidence_ids": _join_list(row.get("evidence_ids")),
                "lifecycle_status": _dict(row.get("lifecycle")).get("status", ""),
                "evidence_sufficiency": _dict(row.get("evidence_quality")).get(
                    "sufficiency",
                    "",
                ),
                "remediation_cost_tier": row.get("remediation_cost_tier", ""),
                "remediation_summary": row.get("remediation_summary", ""),
                "mapping": _join_list(row.get("mapping")),
            }
            for row in rows
        ],
    )


def _write_assets_csv(report: dict[str, Any], output_path: Path) -> None:
    resource_context = _dict(report.get("resource_context"))
    rows = _list_of_dicts(resource_context.get("assets"))
    _write_rows(
        output_path,
        [
            "asset_id",
            "provider",
            "asset_type",
            "name",
            "scope",
            "criticality",
            "internet_exposed",
            "tags",
            "metadata",
        ],
        [
            {
                "asset_id": row.get("asset_id", ""),
                "provider": row.get("provider", ""),
                "asset_type": row.get("asset_type", ""),
                "name": row.get("name", ""),
                "scope": row.get("scope", ""),
                "criticality": row.get("criticality", ""),
                "internet_exposed": row.get("internet_exposed", ""),
                "tags": _json_cell(row.get("tags")),
                "metadata": _json_cell(row.get("metadata")),
            }
            for row in rows
        ],
    )


def _write_evidence_csv(report: dict[str, Any], output_path: Path) -> None:
    resource_context = _dict(report.get("resource_context"))
    rows = _list_of_dicts(resource_context.get("evidence_records"))
    _write_rows(
        output_path,
        [
            "evidence_id",
            "provider",
            "collector",
            "record_type",
            "observation_class",
            "observed_at",
            "source_ref",
            "freshness_hours",
            "finding_id",
            "control_id",
            "resource_scope",
            "statement",
        ],
        [
            {
                "evidence_id": row.get("evidence_id", ""),
                "provider": row.get("provider", ""),
                "collector": row.get("collector", ""),
                "record_type": row.get("record_type", ""),
                "observation_class": row.get("observation_class", ""),
                "observed_at": row.get("observed_at", ""),
                "source_ref": row.get("source_ref", ""),
                "freshness_hours": row.get("freshness_hours", ""),
                "finding_id": _dict(row.get("payload")).get("finding_id", ""),
                "control_id": _dict(row.get("payload")).get("control_id", ""),
                "resource_scope": _dict(row.get("payload")).get("resource_scope", ""),
                "statement": _dict(row.get("payload")).get("statement", ""),
            }
            for row in rows
        ],
    )


def _write_actions_csv(report: dict[str, Any], output_path: Path) -> None:
    phases = _list_of_dicts(_dict(report.get("action_plan_30_day")).get("phases"))
    rows = []
    for phase in phases:
        for action in _list_of_dicts(phase.get("actions")):
            rows.append(
                {
                    "phase_id": phase.get("phase_id", ""),
                    "phase_label": phase.get("label", ""),
                    "time_window": phase.get("time_window", ""),
                    "control_id": action.get("control_id", ""),
                    "title": action.get("title", ""),
                    "organization": action.get("organization", ""),
                    "category": action.get("category", ""),
                    "priority": action.get("priority", ""),
                    "score": action.get("score", ""),
                    "remediation_cost_tier": action.get(
                        "remediation_cost_tier",
                        "",
                    ),
                    "remediation_summary": action.get("remediation_summary", ""),
                    "action_rationale": action.get("action_rationale", ""),
                }
            )
    _write_rows(
        output_path,
        [
            "phase_id",
            "phase_label",
            "time_window",
            "control_id",
            "title",
            "organization",
            "category",
            "priority",
            "score",
            "remediation_cost_tier",
            "remediation_summary",
            "action_rationale",
        ],
        rows,
    )


def _write_rows(
    output_path: Path,
    fieldnames: list[str],
    rows: list[dict[str, Any]],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _list_of_dicts(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _join_list(value: object) -> str:
    if not isinstance(value, list):
        return ""
    return "; ".join(str(item) for item in value if str(item))


def _json_cell(value: object) -> str:
    if value in (None, {}, []):
        return ""
    return json.dumps(value, sort_keys=True)
