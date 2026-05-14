# Tests for the repeatable Azure evidence lab harness.
from __future__ import annotations

import json
import subprocess

import pytest

from scripts import azure_evidence_lab as lab


def test_catalog_lists_expected_lab_scenarios() -> None:
    catalog = lab.load_catalog()
    summary = lab.summarize_catalog(catalog)
    ids = {item["id"] for item in summary["scenarios"]}

    assert {
        "clean-baseline",
        "public-exposure",
        "governance-drift",
        "data-risk",
        "media-office-demo",
        "media-office-delegated",
    } <= ids
    public_exposure = next(item for item in summary["scenarios"] if item["id"] == "public-exposure")
    assert public_exposure["dataset_source_type"] == "vulnerable_lab"
    assert "NET-001" in public_exposure["expected_controls"]


def test_main_requires_yes_for_resource_changes(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["azure_evidence_lab.py", "deploy", "--scenario", "public-exposure"],
    )

    with pytest.raises(SystemExit) as exc:
        lab.main()

    assert "without --yes" in str(exc.value)


def test_deploy_public_exposure_builds_expected_az_commands(monkeypatch, tmp_path) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr(lab, "DEFAULT_OUTPUT_ROOT", tmp_path)

    def fake_run(command, cwd=None, env=None, check=False):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(lab.subprocess, "run", fake_run)
    scenario = lab.find_scenario(lab.load_catalog(), "public-exposure")
    context = lab.build_context(
        scenario=scenario,
        run_id="paper-run",
        location="uksouth",
        resource_group="cris-lab-public-exposure-paper-run",
        dry_run=False,
    )

    lab.deploy(context)

    joined = [" ".join(command) for command in commands]
    assert any("az group create" in command for command in joined)
    assert any("network nsg rule create" in command and "Allow-Internet-22" in command for command in joined)
    assert any("network nsg rule create" in command and "Allow-Internet-3389" in command for command in joined)
    assert any("storage account create" in command and "--allow-blob-public-access true" in command for command in joined)
    manifest = json.loads((tmp_path / "paper-run" / "public-exposure" / "lab_manifest.json").read_text())
    assert manifest["scenario"]["id"] == "public-exposure"
    assert manifest["status"] == "deployed"
    assert manifest["tags"]["cris-sme-owner"]
    assert manifest["tags"]["cris-sme-delete-after"]
    assert manifest["tags"]["cris-sme-managed-by"] == "cris-sme-azure-evidence-lab"


def test_governance_drift_does_not_pass_empty_tags(monkeypatch, tmp_path) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr(lab, "DEFAULT_OUTPUT_ROOT", tmp_path)

    def fake_run(command, cwd=None, env=None, check=False):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(lab.subprocess, "run", fake_run)
    scenario = lab.find_scenario(lab.load_catalog(), "governance-drift")
    context = lab.build_context(
        scenario=scenario,
        run_id="drift-run",
        location="uksouth",
        resource_group="cris-lab-governance-drift-drift-run",
        dry_run=False,
    )

    lab.deploy(context)

    untagged_resource_commands = [
        command
        for command in commands
        if command[:4] in (["az", "network", "nsg", "create"], ["az", "storage", "account", "create"])
    ]
    assert untagged_resource_commands
    assert all("--tags" not in command for command in untagged_resource_commands)


def test_assess_sets_dataset_metadata(monkeypatch, tmp_path) -> None:
    calls: list[dict] = []
    monkeypatch.setattr(lab, "DEFAULT_OUTPUT_ROOT", tmp_path)

    def fake_run(command, cwd=None, env=None, check=False):
        calls.append({"command": command, "env": env, "cwd": cwd, "check": check})
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(lab.subprocess, "run", fake_run)
    scenario = lab.find_scenario(lab.load_catalog(), "data-risk")
    context = lab.build_context(
        scenario=scenario,
        run_id="data-run",
        location="uksouth",
        resource_group="cris-lab-data-risk-data-run",
        dry_run=False,
    )

    lab.assess(context, tmp_path / "dataset")

    call = calls[0]
    command = call["command"]
    assert "--collector" in command
    assert "azure" in command
    assert "--dataset-source-type" in command
    assert "vulnerable_lab" in command
    assert call["env"]["CRIS_SME_AZURE_ORGANIZATION_NAME"] == "Data Protection Stress Lab"


def test_deploy_media_office_demo_builds_web_only_lab(monkeypatch, tmp_path) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr(lab, "DEFAULT_OUTPUT_ROOT", tmp_path)

    def fake_run(command, cwd=None, env=None, check=False):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(lab.subprocess, "run", fake_run)
    scenario = lab.find_scenario(lab.load_catalog(), "media-office-demo")
    context = lab.build_context(
        scenario=scenario,
        run_id="media-001",
        location="uksouth",
        resource_group="cris-lab-media-office-demo-media-001",
        dry_run=False,
    )

    lab.deploy(context)

    joined = [" ".join(command) for command in commands]
    assert any("network nsg rule create" in command and "Allow-Web-80" in command for command in joined)
    assert any("network nsg rule create" in command and "Allow-Web-443" in command for command in joined)
    assert not any("Allow-Internet-22" in command for command in joined)
    assert not any("Allow-Internet-3389" in command for command in joined)
    assert any("storage account create" in command and "--allow-blob-public-access true" in command for command in joined)
    assert any("keyvault create" in command and "--enable-purge-protection true" in command for command in joined)


def test_deploy_media_office_delegated_builds_segmented_architecture(monkeypatch, tmp_path) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr(lab, "DEFAULT_OUTPUT_ROOT", tmp_path)

    def fake_run(command, cwd=None, env=None, check=False):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(lab.subprocess, "run", fake_run)
    scenario = lab.find_scenario(lab.load_catalog(), "media-office-delegated")
    context = lab.build_context(
        scenario=scenario,
        run_id="media-del-001",
        location="germanywestcentral",
        resource_group="cris-lab-media-office-delegated-media-del-001",
        dry_run=False,
    )

    lab.deploy(context)

    joined = [" ".join(command) for command in commands]
    assert any("network vnet create" in command and "--subnet-name edge" in command for command in joined)
    assert any("network vnet subnet create" in command and "--name editorial" in command for command in joined)
    assert any("network vnet subnet create" in command and "--name data" in command for command in joined)
    assert any("network vnet subnet create" in command and "--name monitoring" in command for command in joined)
    assert any("Allow-Web-80" in command for command in joined)
    assert any("Allow-Web-443" in command for command in joined)
    assert any("Allow-VNet-Inbound" in command for command in joined)
    assert any("storage account create" in command and "crismediapub" in command and "--allow-blob-public-access true" in command for command in joined)
    assert any("storage account create" in command and "crismediaedit" in command and "--allow-blob-public-access false" in command for command in joined)
    assert any("keyvault create" in command and "--enable-purge-protection true" in command for command in joined)
    assert any("monitor log-analytics workspace create" in command for command in joined)
    assert not any("Allow-Internet-22" in command for command in joined)
    assert not any("Allow-Internet-3389" in command for command in joined)


def test_cleanup_deletes_resource_group_and_waits(monkeypatch, tmp_path) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr(lab, "DEFAULT_OUTPUT_ROOT", tmp_path)

    def fake_run(command, cwd=None, env=None, check=False):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(lab.subprocess, "run", fake_run)
    scenario = lab.find_scenario(lab.load_catalog(), "public-exposure")
    context = lab.build_context(
        scenario=scenario,
        run_id="cleanup-run",
        location="uksouth",
        resource_group="cris-lab-public-exposure-cleanup-run",
        dry_run=False,
    )

    lab.cleanup(context)

    assert commands[0][:4] == ["az", "group", "delete", "--name"]
    assert "--yes" in commands[0]
    assert "--no-wait" in commands[0]
    assert commands[1] == [
        "az",
        "group",
        "wait",
        "--name",
        "cris-lab-public-exposure-cleanup-run",
        "--deleted",
    ]
