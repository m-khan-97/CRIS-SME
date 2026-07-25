# Remediation script pack export for CRIS-SME prioritized findings.
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cris_sme.controls.definitions import ControlDefinition, load_control_definitions

AWS_CODE_BY_CONTROL: dict[str, list[dict[str, str]]] = {
    "IAM-001": [{"kind": "aws_cli", "label": "Review IAM users and MFA devices", "snippet": "aws iam list-users --output table"}],
    "NET-001": [{"kind": "aws_cli", "label": "Review security-group ingress on administrative ports", "snippet": "aws ec2 describe-security-groups --query 'SecurityGroups[].{GroupId:GroupId,Ingress:IpPermissions}' --output json"}],
    "NET-002": [{"kind": "aws_cli", "label": "Review broadly permissive security-group rules", "snippet": "aws ec2 describe-security-groups --query 'SecurityGroups[].{GroupId:GroupId,Ingress:IpPermissions}' --output json"}],
    "NET-004": [{"kind": "aws_cli", "label": "Review VPC endpoint coverage", "snippet": "aws ec2 describe-vpc-endpoints --output table"}],
    "DATA-001": [{"kind": "aws_cli", "label": "Review public S3 and RDS exposure", "snippet": "aws s3api list-buckets --query 'Buckets[].Name' --output table && aws rds describe-db-instances --query 'DBInstances[].{Id:DBInstanceIdentifier,Public:PubliclyAccessible}' --output table"}],
    "DATA-002": [{"kind": "aws_cli", "label": "Review RDS storage encryption", "snippet": "aws rds describe-db-instances --query 'DBInstances[].{Id:DBInstanceIdentifier,Encrypted:StorageEncrypted}' --output table"}],
    "MON-001": [{"kind": "aws_cli", "label": "Review CloudTrail and CloudWatch Logs retention", "snippet": "aws cloudtrail describe-trails --include-shadow-trails false --output table && aws logs describe-log-groups --query 'logGroups[].{Name:logGroupName,Retention:retentionInDays}' --output table"}],
    "CMP-001": [{"kind": "aws_cli", "label": "Review EC2 metadata and SSM management posture", "snippet": "aws ec2 describe-instances --query 'Reservations[].Instances[].{Id:InstanceId,MetadataTokens:MetadataOptions.HttpTokens}' --output table && aws ssm describe-instance-information --output table"}],
    "GOV-001": [{"kind": "aws_cli", "label": "Review AWS Config recorder status", "snippet": "aws configservice describe-configuration-recorder-status --output table"}],
    "IOT-001": [{"kind": "aws_cli", "label": "Review IoT device identities and certificates", "snippet": "aws iot list-things --output table && aws iot list-certificates --output table"}],
    "IOT-002": [{"kind": "aws_cli", "label": "Review AWS IoT policies", "snippet": "aws iot list-policies --output table"}],
    "IOT-005": [{"kind": "aws_cli", "label": "Review private IoT data endpoints", "snippet": "aws ec2 describe-vpc-endpoints --filters Name=service-name,Values='com.amazonaws.*.iot.data' --output table"}],
}


def write_remediation_script_pack(
    report: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write a non-executing remediation script pack for referenced controls."""
    target_dir = Path(output_dir) / "remediation_scripts"
    target_dir.mkdir(parents=True, exist_ok=True)
    for stale_script in target_dir.glob("cris_sme_remediation_*_cli.sh"):
        stale_script.unlink()

    definitions = load_control_definitions()
    findings_by_control = _findings_by_control(report)
    provider = str(report.get("collector_mode") or "unknown").lower()

    referenced_controls = [
        definitions[control_id]
        for control_id in sorted(findings_by_control)
        if control_id in definitions
    ]

    paths: dict[str, Path] = {}

    manifest_path = target_dir / "cris_sme_remediation_manifest.json"
    _write_manifest(referenced_controls, findings_by_control, provider, manifest_path)
    paths["manifest"] = manifest_path

    for kind, entries in _group_code_by_kind(referenced_controls, provider).items():
        script_path = target_dir / f"cris_sme_remediation_{kind}.sh"
        _write_script(kind, entries, script_path)
        paths[f"{kind}_script"] = script_path

    return paths


def _findings_by_control(report: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    findings_by_control: dict[str, list[dict[str, Any]]] = {}
    for risk in _list_of_dicts(report.get("prioritized_risks")):
        control_id = risk.get("control_id")
        if not control_id:
            continue
        findings_by_control.setdefault(control_id, []).append(risk)
    return findings_by_control


def _write_manifest(
    controls: list[ControlDefinition],
    findings_by_control: dict[str, list[dict[str, Any]]],
    provider: str,
    output_path: Path,
) -> None:
    manifest = {
        "generated_from": "prioritized_risks",
        "execution_policy": "non_executing_reference_only",
        "provider": provider,
        "controls": [
            {
                "control_id": control.control_id,
                "title": control.title,
                "domain": control.domain.value,
                "severity": control.severity.value,
                "remediation_summary": control.remediation.summary,
                "remediation_cost_tier": control.remediation.cost_tier.value,
                "manual_steps": control.remediation.manual_steps,
                "code": [
                    {
                        "kind": code["kind"],
                        "label": code["label"],
                        "snippet": code["snippet"],
                    }
                    for code in _code_for_control(control, provider)
                ],
                "findings": [
                    {
                        "finding_id": finding.get("finding_id", ""),
                        "title": finding.get("title", ""),
                        "priority": finding.get("priority", ""),
                        "organization": finding.get("organization", ""),
                    }
                    for finding in findings_by_control.get(control.control_id, [])
                ],
            }
            for control in controls
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _group_code_by_kind(
    controls: list[ControlDefinition],
    provider: str,
) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for control in controls:
        for code in _code_for_control(control, provider):
            grouped.setdefault(code["kind"], []).append(
                {
                    "control_id": control.control_id,
                    "title": control.title,
                    "label": code["label"],
                    "snippet": code["snippet"],
                }
            )
    return grouped


def _code_for_control(control: ControlDefinition, provider: str) -> list[dict[str, str]]:
    if provider == "aws":
        return AWS_CODE_BY_CONTROL.get(control.control_id, [])
    return [
        {"kind": code.kind, "label": code.label, "snippet": code.snippet}
        for code in control.remediation.code
    ]


def _write_script(kind: str, entries: list[dict[str, str]], output_path: Path) -> None:
    lines = [
        "#!/usr/bin/env bash",
        "# CRIS-SME remediation reference pack",
        f"# Snippet kind: {kind}",
        "#",
        "# These commands are reference-only and are not executed by CRIS-SME.",
        "# Review each command, adapt placeholders (e.g. <resource-group>), and",
        "# run it manually in your own change-controlled session.",
        "set -euo pipefail",
        "",
    ]
    for entry in entries:
        lines.append(f"# {entry['control_id']}: {entry['title']}")
        lines.append(f"# {entry['label']}")
        lines.append(entry["snippet"])
        lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _list_of_dicts(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
