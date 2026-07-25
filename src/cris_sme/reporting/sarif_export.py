# SARIF export helpers for CRIS-SME interoperability outputs.
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SARIF_SCHEMA_URL = (
    "https://json.schemastore.org/sarif-2.1.0.json"
)
SARIF_VERSION = "2.1.0"


def build_sarif_report(report: dict[str, Any]) -> dict[str, Any]:
    """Build a SARIF 2.1.0 report from CRIS-SME prioritized risks."""
    prioritized_risks = _list_of_dicts(report.get("prioritized_risks", []))
    rules = _build_rules(prioritized_risks)
    results = [_build_result(risk) for risk in prioritized_risks]
    run_metadata = _dict(report.get("run_metadata"))

    return {
        "$schema": SARIF_SCHEMA_URL,
        "version": SARIF_VERSION,
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "CRIS-SME",
                        "semanticVersion": str(
                            run_metadata.get("engine_version")
                            or report.get("report_schema_version")
                            or "0.1.0"
                        ),
                        "informationUri": "https://github.com/",
                        "rules": rules,
                    }
                },
                "automationDetails": {
                    "id": str(run_metadata.get("run_id", "cris-sme-assessment")),
                    "description": {
                        "text": "CRIS-SME deterministic cloud risk assessment."
                    },
                },
                "results": results,
                "properties": {
                    "report_schema_version": report.get("report_schema_version"),
                    "generated_at": report.get("generated_at"),
                    "collector_mode": report.get("collector_mode"),
                    "summary": report.get("summary"),
                    "overall_risk_score": report.get("overall_risk_score"),
                    "resource_context_model": _dict(
                        report.get("resource_context")
                    ).get("context_model"),
                    "provider_contract_conformance_passed": _dict(
                        report.get("provider_contract_conformance")
                    ).get("passed"),
                },
            }
        ],
    }


def write_sarif_report(
    report: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """Write a SARIF report to disk and return the output path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(build_sarif_report(report), indent=2),
        encoding="utf-8",
    )
    return path


def _build_rules(prioritized_risks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rules_by_id: dict[str, dict[str, Any]] = {}
    for risk in prioritized_risks:
        control_id = str(risk.get("control_id", "UNKNOWN"))
        if control_id in rules_by_id:
            continue
        rules_by_id[control_id] = {
            "id": control_id,
            "name": control_id,
            "shortDescription": {
                "text": str(risk.get("title") or control_id),
            },
            "fullDescription": {
                "text": str(
                    risk.get("remediation_summary")
                    or risk.get("title")
                    or control_id
                ),
            },
            "help": {
                "text": _rule_help_text(risk),
            },
            "properties": {
                "category": risk.get("category"),
                "severity": risk.get("severity"),
                "remediation_cost_tier": risk.get("remediation_cost_tier"),
                "mapping": risk.get("mapping", []),
            },
        }
    return [rules_by_id[control_id] for control_id in sorted(rules_by_id)]


def _build_result(risk: dict[str, Any]) -> dict[str, Any]:
    finding_id = str(risk.get("finding_id") or _fallback_finding_id(risk))
    evidence_ids = _string_list(risk.get("evidence_ids"))
    asset_ids = _string_list(risk.get("asset_ids"))
    lifecycle = _dict(risk.get("lifecycle"))

    result: dict[str, Any] = {
        "ruleId": str(risk.get("control_id", "UNKNOWN")),
        "ruleIndex": 0,
        "level": _level_for_severity(str(risk.get("severity", ""))),
        "message": {
            "text": _result_message(risk),
        },
        "locations": _locations_for_risk(risk, asset_ids),
        "partialFingerprints": {
            "crisSmeFindingId": finding_id,
            "crisSmeControlResource": _fingerprint_source(risk),
        },
        "properties": {
            "finding_id": finding_id,
            "control_id": risk.get("control_id"),
            "provider": risk.get("provider"),
            "organization": risk.get("organization"),
            "organization_id": risk.get("organization_id"),
            "category": risk.get("category"),
            "severity": risk.get("severity"),
            "priority": risk.get("priority"),
            "score": risk.get("score"),
            "resource_scope": risk.get("resource_scope"),
            "asset_ids": asset_ids,
            "evidence_ids": evidence_ids,
            "evidence_quality": risk.get("evidence_quality", {}),
            "lifecycle": lifecycle,
            "remediation_summary": risk.get("remediation_summary"),
            "remediation_cost_tier": risk.get("remediation_cost_tier"),
            "mapping": risk.get("mapping", []),
        },
    }
    if lifecycle.get("is_new") is False:
        result["baselineState"] = "unchanged"
    elif lifecycle:
        result["baselineState"] = "new"
    related_locations = _related_evidence_locations(risk, evidence_ids)
    if related_locations:
        result["relatedLocations"] = related_locations
    return result


def _rule_help_text(risk: dict[str, Any]) -> str:
    summary = str(risk.get("remediation_summary") or "Review this CRIS-SME finding.")
    mapping = ", ".join(_string_list(risk.get("mapping")))
    if mapping:
        return f"{summary}\n\nMappings: {mapping}"
    return summary


def _result_message(risk: dict[str, Any]) -> str:
    title = str(risk.get("title") or risk.get("control_id") or "CRIS-SME finding")
    priority = str(risk.get("priority") or "Unprioritized")
    score = risk.get("score")
    if isinstance(score, (int, float)):
        return f"{title} Priority: {priority}. CRIS-SME score: {score:.2f}."
    return f"{title} Priority: {priority}."


def _locations_for_risk(
    risk: dict[str, Any],
    asset_ids: list[str],
) -> list[dict[str, Any]]:
    finding_id = str(risk.get("finding_id") or _fallback_finding_id(risk))
    provider = str(risk.get("provider") or "cloud")
    organization_id = str(risk.get("organization_id") or "unknown-org")
    control_id = str(risk.get("control_id") or "unknown-control")
    if not asset_ids:
        asset_ids = [str(risk.get("resource_scope") or "assessment-scope")]

    locations = []
    for asset_id in asset_ids:
        locations.append(
            {
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": _cloud_uri(
                            provider=provider,
                            organization_id=organization_id,
                            control_id=control_id,
                            finding_id=finding_id,
                            asset_id=asset_id,
                        )
                    }
                },
                "logicalLocations": [
                    {
                        "name": asset_id,
                        "fullyQualifiedName": asset_id,
                        "kind": "resource",
                    }
                ],
            }
        )
    return locations


def _related_evidence_locations(
    risk: dict[str, Any],
    evidence_ids: list[str],
) -> list[dict[str, Any]]:
    evidence = _string_list(risk.get("evidence"))
    related = []
    for index, evidence_id in enumerate(evidence_ids, start=1):
        message = evidence[index - 1] if index <= len(evidence) else evidence_id
        related.append(
            {
                "id": index,
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": f"cris-sme-evidence://{_slug(evidence_id)}",
                    }
                },
                "message": {"text": message},
            }
        )
    return related


def _level_for_severity(severity: str) -> str:
    normalized = severity.strip().lower()
    if normalized in {"critical", "high"}:
        return "error"
    if normalized == "medium":
        return "warning"
    if normalized == "low":
        return "note"
    return "warning"


def _cloud_uri(
    *,
    provider: str,
    organization_id: str,
    control_id: str,
    finding_id: str,
    asset_id: str,
) -> str:
    return (
        f"cris-sme://{_slug(provider)}/{_slug(organization_id)}/"
        f"{_slug(control_id)}/{_slug(finding_id)}/{_slug(asset_id)}"
    )


def _fallback_finding_id(risk: dict[str, Any]) -> str:
    return (
        "fdg_"
        + _slug(
            "|".join(
                [
                    str(risk.get("control_id", "")),
                    str(risk.get("provider", "")),
                    str(risk.get("organization_id", "")),
                    str(risk.get("resource_scope", "")),
                ]
            )
        )[:24]
    )


def _fingerprint_source(risk: dict[str, Any]) -> str:
    return "|".join(
        [
            str(risk.get("control_id", "")),
            str(risk.get("provider", "")),
            str(risk.get("organization_id", "")),
            str(risk.get("resource_scope", "")),
        ]
    )


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


def _slug(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.:-]+", "-", value.strip())
    return normalized.strip("-") or "unknown"
