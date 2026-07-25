# Tests for the non-executing remediation script pack export.
import json

from cris_sme.controls.definitions import load_control_definitions
from cris_sme.reporting import write_remediation_script_pack
from tests.test_sarif_export import _build_report


def test_write_remediation_script_pack_persists_manifest_and_scripts(tmp_path) -> None:
    report = _build_report()

    paths = write_remediation_script_pack(report, tmp_path)

    assert "manifest" in paths
    assert all(path.exists() for path in paths.values())

    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    assert manifest["execution_policy"] == "non_executing_reference_only"

    definitions = load_control_definitions()
    risk_control_ids = {risk["control_id"] for risk in report["prioritized_risks"]}
    expected_control_ids = risk_control_ids & set(definitions)
    assert expected_control_ids
    assert {control["control_id"] for control in manifest["controls"]} == expected_control_ids


def test_manifest_includes_remediation_guidance_and_findings(tmp_path) -> None:
    report = _build_report()
    definitions = load_control_definitions()

    paths = write_remediation_script_pack(report, tmp_path)
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))

    for control in manifest["controls"]:
        definition = definitions[control["control_id"]]
        assert control["manual_steps"] == definition.remediation.manual_steps
        assert control["remediation_cost_tier"] == definition.remediation.cost_tier.value
        assert control["findings"]
        for finding in control["findings"]:
            assert finding["finding_id"]


def test_azure_cli_script_contains_referenced_snippets(tmp_path) -> None:
    report = _build_report()
    definitions = load_control_definitions()

    paths = write_remediation_script_pack(report, tmp_path)

    assert "azure_cli_script" in paths
    script = paths["azure_cli_script"].read_text(encoding="utf-8")
    assert script.startswith("#!/usr/bin/env bash")

    risk_control_ids = {risk["control_id"] for risk in report["prioritized_risks"]}
    for control_id in risk_control_ids & set(definitions):
        definition = definitions[control_id]
        for code in definition.remediation.code:
            if code.kind == "azure_cli":
                assert code.snippet in script


def test_aws_report_emits_only_aws_remediation_commands(tmp_path) -> None:
    report = _build_report()
    write_remediation_script_pack(report, tmp_path)
    report["collector_mode"] = "aws"

    paths = write_remediation_script_pack(report, tmp_path)
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))

    assert manifest["provider"] == "aws"
    assert "aws_cli_script" in paths
    assert "azure_cli_script" not in paths
    assert not (tmp_path / "remediation_scripts" / "cris_sme_remediation_azure_cli.sh").exists()
    script = paths["aws_cli_script"].read_text(encoding="utf-8")
    assert "aws " in script
    assert "az " not in script
