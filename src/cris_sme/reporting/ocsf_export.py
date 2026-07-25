# OCSF-aligned finding export helpers for security data-lake interoperability.
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


OCSF_VERSION = "1.1.0"
OCSF_CATEGORY_FINDINGS_UID = 2
OCSF_CATEGORY_FINDINGS_NAME = "Findings"
OCSF_DETECTION_FINDING_CLASS_UID = 2004
OCSF_DETECTION_FINDING_CLASS_NAME = "Detection Finding"
OCSF_ACTIVITY_CREATE_ID = 1
OCSF_ACTIVITY_CREATE_NAME = "Create"


def build_ocsf_findings(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Build OCSF-aligned Detection Finding events from a CRIS-SME report."""
    generated_at = str(report.get("generated_at") or _now_iso())
    event_time = _epoch_millis(generated_at)
    run_metadata = _dict(report.get("run_metadata"))
    resource_context = _dict(report.get("resource_context"))
    assets_by_id = {
        str(asset.get("asset_id")): asset
        for asset in _list_of_dicts(resource_context.get("assets"))
    }
    evidence_by_id = {
        str(evidence.get("evidence_id")): evidence
        for evidence in _list_of_dicts(resource_context.get("evidence_records"))
    }

    return [
        _build_ocsf_finding(
            risk,
            report=report,
            generated_at=generated_at,
            event_time=event_time,
            run_metadata=run_metadata,
            assets_by_id=assets_by_id,
            evidence_by_id=evidence_by_id,
        )
        for risk in _list_of_dicts(report.get("prioritized_risks"))
    ]


def write_ocsf_findings(
    report: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """Write OCSF-aligned finding events to a JSON file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(build_ocsf_findings(report), indent=2),
        encoding="utf-8",
    )
    return path


def _build_ocsf_finding(
    risk: dict[str, Any],
    *,
    report: dict[str, Any],
    generated_at: str,
    event_time: int,
    run_metadata: dict[str, Any],
    assets_by_id: dict[str, dict[str, Any]],
    evidence_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    finding_id = str(risk.get("finding_id") or "")
    severity = str(risk.get("severity") or "")
    lifecycle = _dict(risk.get("lifecycle"))
    asset_ids = _string_list(risk.get("asset_ids"))
    evidence_ids = _string_list(risk.get("evidence_ids"))
    score = risk.get("score")

    return {
        "activity_id": OCSF_ACTIVITY_CREATE_ID,
        "activity_name": OCSF_ACTIVITY_CREATE_NAME,
        "category_uid": OCSF_CATEGORY_FINDINGS_UID,
        "category_name": OCSF_CATEGORY_FINDINGS_NAME,
        "class_uid": OCSF_DETECTION_FINDING_CLASS_UID,
        "class_name": OCSF_DETECTION_FINDING_CLASS_NAME,
        "type_uid": (
            OCSF_DETECTION_FINDING_CLASS_UID * 100
            + OCSF_ACTIVITY_CREATE_ID
        ),
        "type_name": (
            f"{OCSF_DETECTION_FINDING_CLASS_NAME}: {OCSF_ACTIVITY_CREATE_NAME}"
        ),
        "time": event_time,
        "time_dt": generated_at,
        "severity_id": _severity_id(severity),
        "severity": severity or "Unknown",
        "status": str(lifecycle.get("status") or "open"),
        "status_id": _status_id(str(lifecycle.get("status") or "open")),
        "count": 1,
        "metadata": {
            "version": OCSF_VERSION,
            "event_code": "finding",
            "uid": finding_id,
            "correlation_uid": str(run_metadata.get("run_id") or "unknown-run"),
            "processed_time": event_time,
            "processed_time_dt": generated_at,
            "product": {
                "vendor_name": "CRIS-SME",
                "name": "CRIS-SME",
                "feature": {"name": "Risk Assessment"},
                "version": str(
                    run_metadata.get("engine_version")
                    or report.get("report_schema_version")
                    or "0.1.0"
                ),
            },
            "profiles": ["cloud", "security_control"],
        },
        "finding_info": {
            "uid": finding_id,
            "title": str(risk.get("title") or risk.get("control_id") or ""),
            "desc": str(risk.get("decision_rationale") or ""),
            "product_uid": str(risk.get("control_id") or ""),
            "created_time": event_time,
            "created_time_dt": generated_at,
            "modified_time": event_time,
            "modified_time_dt": generated_at,
            "types": [str(risk.get("category") or "Cloud Risk")],
        },
        "resources": [
            _resource_object(asset_id, assets_by_id.get(asset_id), risk)
            for asset_id in asset_ids
        ],
        "evidences": [
            _evidence_object(evidence_id, evidence_by_id.get(evidence_id))
            for evidence_id in evidence_ids
        ],
        "remediation": {
            "desc": str(risk.get("remediation_summary") or ""),
        },
        "cloud": {
            "provider": str(risk.get("provider") or "unknown"),
            "account_uid": str(risk.get("organization_id") or "unknown"),
            "account_name": str(risk.get("organization") or "unknown"),
        },
        "unmapped": {
            "cris_sme": {
                "priority": risk.get("priority"),
                "score": score,
                "resource_scope": risk.get("resource_scope"),
                "asset_ids": asset_ids,
                "evidence_ids": evidence_ids,
                "evidence_quality": risk.get("evidence_quality", {}),
                "lifecycle": lifecycle,
                "mapping": risk.get("mapping", []),
                "remediation_cost_tier": risk.get("remediation_cost_tier"),
                "report_schema_version": report.get("report_schema_version"),
                "collector_mode": report.get("collector_mode"),
            }
        },
    }


def _resource_object(
    asset_id: str,
    asset: dict[str, Any] | None,
    risk: dict[str, Any],
) -> dict[str, Any]:
    asset = asset or {}
    return {
        "uid": asset_id,
        "name": str(asset.get("name") or asset_id),
        "type": str(asset.get("asset_type") or risk.get("category") or "resource"),
        "cloud_partition": str(risk.get("provider") or asset.get("provider") or ""),
        "criticality": str(asset.get("criticality") or ""),
        "labels": _labels_from_asset(asset),
    }


def _evidence_object(
    evidence_id: str,
    evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    evidence = evidence or {}
    payload = _dict(evidence.get("payload"))
    return {
        "uid": evidence_id,
        "name": str(evidence.get("record_type") or "control_evidence"),
        "type": str(evidence.get("observation_class") or "observed"),
        "desc": str(payload.get("statement") or evidence_id),
        "data": payload,
    }


def _severity_id(severity: str) -> int:
    normalized = severity.strip().lower()
    if normalized == "critical":
        return 5
    if normalized == "high":
        return 4
    if normalized == "medium":
        return 3
    if normalized == "low":
        return 2
    return 1


def _status_id(status: str) -> int:
    normalized = status.strip().lower()
    if normalized in {"open", "new"}:
        return 1
    if normalized in {"in_progress", "accepted_risk"}:
        return 2
    if normalized in {"resolved", "suppressed"}:
        return 3
    return 0


def _epoch_millis(value: str) -> int:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        parsed = datetime.now(UTC)
    return int(parsed.timestamp() * 1000)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _labels_from_asset(asset: dict[str, Any]) -> list[str]:
    labels = []
    if asset.get("internet_exposed") is True:
        labels.append("internet_exposed")
    criticality = asset.get("criticality")
    if criticality:
        labels.append(f"criticality:{criticality}")
    return labels


def _list_of_dicts(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return []
