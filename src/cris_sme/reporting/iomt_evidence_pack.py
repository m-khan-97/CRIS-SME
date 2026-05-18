# IoMT evidence-pack export for healthcare IoT research and demonstrations.
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


IOMT_MAPPING_PATH = Path("data/iomt_healthcare_control_mapping.json")


def build_iomt_evidence_pack(
    report: dict[str, Any],
    *,
    lab_manifest: dict[str, Any] | None = None,
    mapping_path: str | Path = IOMT_MAPPING_PATH,
) -> dict[str, Any]:
    """Build a focused IoMT evidence pack from a CRIS report."""
    risks = [
        item
        for item in report.get("prioritized_risks", [])
        if isinstance(item, dict)
        and (
            str(item.get("control_id", "")).startswith("IOT-")
            or item.get("category") == "Healthcare IoT"
        )
    ]
    mapping = _load_iomt_mapping(mapping_path)
    mapped_controls = {
        str(item.get("control_id")): item
        for item in mapping.get("controls", [])
        if isinstance(item, dict) and item.get("control_id")
    }
    triggered_ids = {str(item.get("control_id")) for item in risks}
    profiles = report.get("organizations", [])
    iot_metadata = _iot_metadata_from_organizations(profiles)

    control_rows = []
    for control_id, control_mapping in mapped_controls.items():
        matching_risks = [item for item in risks if item.get("control_id") == control_id]
        control_rows.append(
            {
                "control_id": control_id,
                "title": control_mapping.get("title"),
                "status": "risk_found" if matching_risks else "not_triggered",
                "risk_count": len(matching_risks),
                "highest_score": max(
                    [float(item.get("score", 0.0)) for item in matching_risks],
                    default=0.0,
                ),
                "evidence_class": control_mapping.get("evidence_class"),
                "azure_evidence": control_mapping.get("azure_evidence", []),
                "manual_or_external_evidence": control_mapping.get(
                    "manual_or_external_evidence",
                    [],
                ),
                "nhs_dspt_themes": control_mapping.get("nhs_dspt_themes", []),
                "ncsc_caf_objectives": control_mapping.get("ncsc_caf_objectives", []),
                "findings": [
                    {
                        "finding_id": item.get("finding_id"),
                        "title": item.get("title"),
                        "severity": item.get("severity"),
                        "priority": item.get("priority"),
                        "score": item.get("score"),
                        "evidence": item.get("evidence", []),
                        "evidence_quality": item.get("evidence_quality", {}),
                        "remediation_summary": item.get("remediation_summary"),
                    }
                    for item in matching_risks
                ],
            }
        )

    evidence_gap_rows = [
        {
            "control_id": row["control_id"],
            "title": row["title"],
            "manual_or_external_evidence": row["manual_or_external_evidence"],
        }
        for row in control_rows
        if row["manual_or_external_evidence"]
    ]

    return {
        "pack_schema_version": "1.0.0",
        "pack_name": "CRIS-IoMT Evidence Pack",
        "generated_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "source_report_generated_at": report.get("generated_at"),
        "overall_risk_score": report.get("overall_risk_score"),
        "iomt_category_score": report.get("category_scores", {}).get("Healthcare IoT", 0.0)
        if isinstance(report.get("category_scores"), dict)
        else 0.0,
        "iomt_findings_total": len(risks),
        "iomt_controls_triggered": sorted(triggered_ids),
        "certification_boundary": mapping.get("certification_boundary"),
        "lab_context": _lab_context(lab_manifest),
        "iot_collection_metadata": iot_metadata,
        "control_evidence": control_rows,
        "manual_evidence_backlog": evidence_gap_rows,
        "research_positioning": {
            "claim": (
                "CRIS-IoMT converts cloud control-plane IoT evidence into deterministic "
                "healthcare IoT governance findings with explicit clinical and device-level "
                "human-verification boundaries."
            ),
            "non_claims": [
                "Does not certify NHS DSPT readiness.",
                "Does not certify NCSC CAF compliance.",
                "Does not certify medical-device safety or firmware security.",
                "Does not inspect patient data or clinical telemetry payloads.",
            ],
        },
    }


def write_iomt_evidence_pack(
    pack: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write IoMT evidence pack JSON and Markdown artifacts."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    json_path = target_dir / "cris_iomt_evidence_pack.json"
    markdown_path = target_dir / "cris_iomt_evidence_pack.md"
    json_path.write_text(json.dumps(pack, indent=2), encoding="utf-8")
    markdown_path.write_text(build_iomt_evidence_pack_markdown(pack), encoding="utf-8")
    return {
        "iomt_evidence_pack_json": json_path,
        "iomt_evidence_pack_markdown": markdown_path,
    }


def build_iomt_evidence_pack_markdown(pack: dict[str, Any]) -> str:
    """Render the IoMT evidence pack as paper-friendly Markdown."""
    lines = [
        "# CRIS-IoMT Evidence Pack",
        "",
        f"- Generated at: `{pack.get('generated_at', 'unknown')}`",
        f"- Source report generated at: `{pack.get('source_report_generated_at', 'unknown')}`",
        f"- Overall CRIS risk score: `{float(pack.get('overall_risk_score') or 0.0):.2f}`",
        f"- Healthcare IoT category score: `{float(pack.get('iomt_category_score') or 0.0):.2f}`",
        f"- IoMT findings: `{int(pack.get('iomt_findings_total') or 0)}`",
        "",
        "## Certification Boundary",
        "",
        str(pack.get("certification_boundary") or ""),
        "",
    ]

    lab_context = pack.get("lab_context", {})
    if isinstance(lab_context, dict) and lab_context:
        lines.extend(
            [
                "## Lab Context",
                "",
                f"- Scenario: `{lab_context.get('scenario_id', 'unknown')}`",
                f"- Dataset use: `{lab_context.get('dataset_use', 'unknown')}`",
                f"- Authorization basis: `{lab_context.get('authorization_basis', 'unknown')}`",
                f"- Resource group: `{lab_context.get('resource_group', 'unknown')}`",
                "",
            ]
        )

    metadata = pack.get("iot_collection_metadata", {})
    if isinstance(metadata, dict) and metadata:
        lines.extend(
            [
                "## IoT Collection Metadata",
                "",
                "| Signal | Value |",
                "| --- | ---: |",
            ]
        )
        for key, value in sorted(metadata.items()):
            lines.append(f"| `{key}` | `{value}` |")
        lines.append("")

    control_rows = pack.get("control_evidence", [])
    if isinstance(control_rows, list):
        lines.extend(
            [
                "## Control Evidence",
                "",
                "| Control | Status | Evidence class | Highest score | NHS/DSPT themes | NCSC CAF objectives |",
                "| --- | --- | --- | ---: | --- | --- |",
            ]
        )
        for row in control_rows:
            if not isinstance(row, dict):
                continue
            lines.append(
                "| "
                f"{row.get('control_id', '')} | "
                f"{row.get('status', '')} | "
                f"{row.get('evidence_class', '')} | "
                f"{float(row.get('highest_score') or 0.0):.2f} | "
                f"{', '.join(row.get('nhs_dspt_themes', []) or [])} | "
                f"{', '.join(row.get('ncsc_caf_objectives', []) or [])} |"
            )
        lines.append("")

    backlog = pack.get("manual_evidence_backlog", [])
    if isinstance(backlog, list) and backlog:
        lines.extend(
            [
                "## Manual Evidence Backlog",
                "",
                "| Control | Evidence required beyond cloud telemetry |",
                "| --- | --- |",
            ]
        )
        for row in backlog:
            if not isinstance(row, dict):
                continue
            evidence = "; ".join(row.get("manual_or_external_evidence", []) or [])
            lines.append(f"| {row.get('control_id', '')} | {evidence} |")
        lines.append("")

    positioning = pack.get("research_positioning", {})
    if isinstance(positioning, dict):
        lines.extend(["## Research Positioning", "", str(positioning.get("claim", "")), ""])
        non_claims = positioning.get("non_claims", [])
        if isinstance(non_claims, list):
            lines.append("Non-claims:")
            for item in non_claims:
                lines.append(f"- {item}")
            lines.append("")

    return "\n".join(lines)


def _load_iomt_mapping(path: str | Path) -> dict[str, Any]:
    mapping_path = Path(path)
    return json.loads(mapping_path.read_text(encoding="utf-8"))


def _lab_context(lab_manifest: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(lab_manifest, dict):
        return {}
    scenario = lab_manifest.get("scenario", {})
    scenario = scenario if isinstance(scenario, dict) else {}
    return {
        "status": lab_manifest.get("status"),
        "run_id": lab_manifest.get("run_id"),
        "scenario_id": scenario.get("id"),
        "scenario_title": scenario.get("title"),
        "dataset_source_type": scenario.get("dataset_source_type"),
        "dataset_use": scenario.get("dataset_use"),
        "authorization_basis": scenario.get("authorization_basis"),
        "resource_group": lab_manifest.get("resource_group"),
        "location": lab_manifest.get("location"),
    }


def _iot_metadata_from_organizations(organizations: Any) -> dict[str, Any]:
    if not isinstance(organizations, list):
        return {}
    merged: dict[str, Any] = {}
    for organization in organizations:
        if not isinstance(organization, dict):
            continue
        details = organization.get("collection_details", {})
        if not isinstance(details, dict):
            continue
        for key, value in details.items():
            if str(key).startswith("iot_"):
                merged[str(key)] = value
        evidence_counts = details.get("evidence_counts", {})
        if isinstance(evidence_counts, dict):
            for key, value in evidence_counts.items():
                if str(key).startswith("iot_"):
                    merged[str(key)] = value
    return merged
