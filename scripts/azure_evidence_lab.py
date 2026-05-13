# Repeatable Azure evidence lab harness for CRIS-SME live dataset generation.
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
SCENARIO_FILE = REPO_ROOT / "labs" / "azure-evidence-lab" / "scenarios.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "outputs" / "evidence-lab"


@dataclass(frozen=True)
class LabContext:
    scenario: dict[str, Any]
    run_id: str
    location: str
    resource_group: str
    suffix: str
    tags: dict[str, str]
    dry_run: bool


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deploy, assess, and clean up controlled Azure evidence-lab scenarios.",
    )
    parser.add_argument(
        "action",
        choices=("list", "deploy", "assess", "cleanup", "cycle"),
        help="Action to perform. cycle = deploy, assess, then cleanup.",
    )
    parser.add_argument(
        "--scenario",
        default="public-exposure",
        help="Scenario id from labs/azure-evidence-lab/scenarios.json.",
    )
    parser.add_argument(
        "--location",
        default=os.getenv("CRIS_SME_AZURE_LAB_LOCATION", "uksouth"),
        help="Azure region for lab resources.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Stable run id. Defaults to UTC timestamp.",
    )
    parser.add_argument(
        "--resource-group",
        default=None,
        help="Override resource group name. Defaults to cris-lab-{scenario}-{run_id}.",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Root directory for assessment outputs.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print Azure and CRIS commands without executing them.",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="For cycle action, keep lab resources after assessment instead of deleting them.",
    )
    args = parser.parse_args()

    catalog = load_catalog()
    if args.action == "list":
        print(json.dumps(summarize_catalog(catalog), indent=2))
        return 0

    scenario = find_scenario(catalog, args.scenario)
    run_id = normalize_run_id(args.run_id or datetime.now(UTC).strftime("%Y%m%d%H%M%S"))
    resource_group = args.resource_group or f"cris-lab-{scenario['id']}-{run_id}"
    context = build_context(
        scenario=scenario,
        run_id=run_id,
        location=args.location,
        resource_group=resource_group,
        dry_run=args.dry_run,
    )

    if args.action == "deploy":
        deploy(context)
    elif args.action == "assess":
        assess(context, Path(args.output_root))
    elif args.action == "cleanup":
        cleanup(context)
    elif args.action == "cycle":
        deploy(context)
        assess(context, Path(args.output_root))
        if not args.keep:
            cleanup(context)

    return 0


def load_catalog(path: Path = SCENARIO_FILE) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("Azure evidence lab catalog must contain at least one scenario.")
    return payload


def summarize_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": catalog.get("version"),
        "scenarios": [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "dataset_source_type": item.get("dataset_source_type"),
                "dataset_use": item.get("dataset_use"),
                "expected_controls": [
                    finding.get("control_id")
                    for finding in item.get("expected_findings", [])
                    if isinstance(finding, dict)
                ],
            }
            for item in catalog.get("scenarios", [])
        ],
    }


def find_scenario(catalog: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    for scenario in catalog.get("scenarios", []):
        if scenario.get("id") == scenario_id:
            return scenario
    valid = ", ".join(str(item.get("id")) for item in catalog.get("scenarios", []))
    raise ValueError(f"Unknown scenario '{scenario_id}'. Valid scenarios: {valid}")


def build_context(
    *,
    scenario: dict[str, Any],
    run_id: str,
    location: str,
    resource_group: str,
    dry_run: bool,
) -> LabContext:
    suffix = re.sub(r"[^a-z0-9]", "", f"{scenario['id']}{run_id}".lower())[-14:]
    tags = {
        "cris-sme-lab": "true",
        "cris-sme-scenario": str(scenario["id"]),
        "cris-sme-run-id": run_id,
        "cris-sme-purpose": "evidence-dataset",
    }
    return LabContext(
        scenario=scenario,
        run_id=run_id,
        location=location,
        resource_group=resource_group,
        suffix=suffix,
        tags=tags,
        dry_run=dry_run,
    )


def deploy(context: LabContext) -> None:
    scenario_id = context.scenario["id"]
    print(f"Deploying Azure evidence lab scenario '{scenario_id}' into {context.resource_group}")
    run_az(
        [
            "group",
            "create",
            "--name",
            context.resource_group,
            "--location",
            context.location,
            *tag_args(context.tags),
        ],
        context,
    )

    if scenario_id == "clean-baseline":
        create_clean_baseline(context)
    elif scenario_id == "public-exposure":
        create_public_exposure(context)
    elif scenario_id == "governance-drift":
        create_governance_drift(context)
    elif scenario_id == "data-risk":
        create_data_risk(context)
    elif scenario_id == "media-office-demo":
        create_media_office_demo(context)
    elif scenario_id == "media-office-delegated":
        create_media_office_delegated(context)
    else:
        raise ValueError(f"Scenario '{scenario_id}' has no deployer.")

    write_manifest(context, status="deployed")


def assess(context: LabContext, output_root: Path) -> None:
    output_dir = output_root / context.run_id / str(context.scenario["id"]) / "reports"
    figure_dir = output_root / context.run_id / str(context.scenario["id"]) / "figures"
    if not context.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        figure_dir.mkdir(parents=True, exist_ok=True)
    write_manifest(context, status="assessment_started", output_dir=output_dir)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    env["CRIS_SME_AZURE_ORGANIZATION_NAME"] = str(context.scenario.get("title", "Azure Evidence Lab"))
    env["CRIS_SME_AZURE_SECTOR"] = "Research Lab"

    command = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_assessment_snapshot.py"),
        "--collector",
        "azure",
        "--output-dir",
        str(output_dir),
        "--figure-dir",
        str(figure_dir),
        "--dataset-source-type",
        str(context.scenario["dataset_source_type"]),
        "--authorization-basis",
        str(context.scenario["authorization_basis"]),
        "--dataset-use",
        str(context.scenario["dataset_use"]),
    ]
    run_command(command, context, env=env, cwd=REPO_ROOT)
    if not context.dry_run:
        copy_manifest_to_output(context, output_dir)


def cleanup(context: LabContext) -> None:
    print(f"Deleting Azure evidence lab resource group {context.resource_group}")
    run_az(
        [
            "group",
            "delete",
            "--name",
            context.resource_group,
            "--yes",
            "--no-wait",
        ],
        context,
    )
    write_manifest(context, status="cleanup_requested")


def create_clean_baseline(context: LabContext) -> None:
    create_nsg(context, "clean-nsg", allow_management=False, tags=context.tags)
    create_storage(context, "clean", public_blob=False, tags=context.tags)


def create_public_exposure(context: LabContext) -> None:
    create_nsg(context, "open-admin-nsg", allow_management=True, tags=context.tags)
    create_storage(context, "public", public_blob=True, tags=context.tags)


def create_governance_drift(context: LabContext) -> None:
    create_nsg(context, "untagged-nsg", allow_management=False, tags={})
    create_storage(context, "drift", public_blob=False, tags={})


def create_data_risk(context: LabContext) -> None:
    create_storage(context, "datarisk", public_blob=True, tags=context.tags)
    vault_name = unique_name("criskv", context.suffix, max_len=24)
    run_az(
        [
            "keyvault",
            "create",
            "--name",
            vault_name,
            "--resource-group",
            context.resource_group,
            "--location",
            context.location,
            "--enable-purge-protection",
            "false",
            *tag_args(context.tags),
        ],
        context,
    )


def create_media_office_demo(context: LabContext) -> None:
    create_nsg(
        context,
        "media-web-nsg",
        allow_management=False,
        tags=context.tags,
        web_only=True,
    )
    create_storage(
        context,
        "media",
        public_blob=True,
        tags=context.tags,
        intentional_public=True,
    )
    vault_name = unique_name("crismediakv", context.suffix, max_len=24)
    run_az(
        [
            "keyvault",
            "create",
            "--name",
            vault_name,
            "--resource-group",
            context.resource_group,
            "--location",
            context.location,
            "--enable-purge-protection",
            "true",
            "--retention-days",
            "7",
            *tag_args(context.tags),
        ],
        context,
    )


def create_media_office_delegated(context: LabContext) -> None:
    vnet_name = f"media-vnet-{context.run_id}"[:64]
    create_vnet_with_subnets(context, vnet_name)
    create_nsg(
        context,
        "media-edge-nsg",
        allow_management=False,
        tags=context.tags,
        web_only=True,
    )
    create_nsg(
        context,
        "media-editorial-nsg",
        allow_management=False,
        tags=context.tags,
        internal_only=True,
    )
    create_nsg(
        context,
        "media-data-nsg",
        allow_management=False,
        tags=context.tags,
        internal_only=True,
    )
    create_storage(
        context,
        "mediapub",
        public_blob=True,
        tags=context.tags,
        intentional_public=True,
    )
    create_storage(context, "mediaedit", public_blob=False, tags=context.tags)
    vault_name = unique_name("crismediadkv", context.suffix, max_len=24)
    run_az(
        [
            "keyvault",
            "create",
            "--name",
            vault_name,
            "--resource-group",
            context.resource_group,
            "--location",
            context.location,
            "--enable-purge-protection",
            "true",
            "--retention-days",
            "7",
            *tag_args(context.tags),
        ],
        context,
    )
    workspace_name = f"media-law-{context.run_id}"[:63]
    run_az(
        [
            "monitor",
            "log-analytics",
            "workspace",
            "create",
            "--workspace-name",
            workspace_name,
            "--resource-group",
            context.resource_group,
            "--location",
            context.location,
            "--sku",
            "PerGB2018",
            *tag_args(context.tags),
        ],
        context,
    )


def create_vnet_with_subnets(context: LabContext, vnet_name: str) -> None:
    run_az(
        [
            "network",
            "vnet",
            "create",
            "--resource-group",
            context.resource_group,
            "--name",
            vnet_name,
            "--location",
            context.location,
            "--address-prefixes",
            "10.42.0.0/16",
            "--subnet-name",
            "edge",
            "--subnet-prefixes",
            "10.42.1.0/24",
            *tag_args(context.tags),
        ],
        context,
    )
    for name, prefix in (
        ("editorial", "10.42.2.0/24"),
        ("data", "10.42.3.0/24"),
        ("monitoring", "10.42.4.0/24"),
    ):
        run_az(
            [
                "network",
                "vnet",
                "subnet",
                "create",
                "--resource-group",
                context.resource_group,
                "--vnet-name",
                vnet_name,
                "--name",
                name,
                "--address-prefixes",
                prefix,
            ],
            context,
        )


def create_nsg(
    context: LabContext,
    name: str,
    *,
    allow_management: bool,
    tags: dict[str, str],
    web_only: bool = False,
    internal_only: bool = False,
) -> None:
    nsg_name = f"{name}-{context.run_id}"[:80]
    run_az(
        [
            "network",
            "nsg",
            "create",
            "--resource-group",
            context.resource_group,
            "--name",
            nsg_name,
            "--location",
            context.location,
            *tag_args(tags),
        ],
        context,
    )
    if web_only:
        for priority, port in ((120, "80"), (130, "443")):
            run_az(
                [
                    "network",
                    "nsg",
                    "rule",
                    "create",
                    "--resource-group",
                    context.resource_group,
                    "--nsg-name",
                    nsg_name,
                    "--name",
                    f"Allow-Web-{port}",
                    "--priority",
                    str(priority),
                    "--access",
                    "Allow",
                    "--direction",
                    "Inbound",
                    "--protocol",
                    "Tcp",
                    "--source-address-prefixes",
                    "Internet",
                    "--source-port-ranges",
                    "*",
                    "--destination-address-prefixes",
                    "*",
                    "--destination-port-ranges",
                    port,
                ],
                context,
            )
    if internal_only:
        run_az(
            [
                "network",
                "nsg",
                "rule",
                "create",
                "--resource-group",
                context.resource_group,
                "--nsg-name",
                nsg_name,
                "--name",
                "Allow-VNet-Inbound",
                "--priority",
                "140",
                "--access",
                "Allow",
                "--direction",
                "Inbound",
                "--protocol",
                "*",
                "--source-address-prefixes",
                "VirtualNetwork",
                "--source-port-ranges",
                "*",
                "--destination-address-prefixes",
                "*",
                "--destination-port-ranges",
                "*",
            ],
            context,
        )
    if allow_management:
        for priority, port in ((100, "22"), (110, "3389")):
            run_az(
                [
                    "network",
                    "nsg",
                    "rule",
                    "create",
                    "--resource-group",
                    context.resource_group,
                    "--nsg-name",
                    nsg_name,
                    "--name",
                    f"Allow-Internet-{port}",
                    "--priority",
                    str(priority),
                    "--access",
                    "Allow",
                    "--direction",
                    "Inbound",
                    "--protocol",
                    "Tcp",
                    "--source-address-prefixes",
                    "Internet",
                    "--source-port-ranges",
                    "*",
                    "--destination-address-prefixes",
                    "*",
                    "--destination-port-ranges",
                    port,
                ],
                context,
            )


def create_storage(
    context: LabContext,
    prefix: str,
    *,
    public_blob: bool,
    tags: dict[str, str],
    intentional_public: bool = False,
) -> None:
    account_name = unique_name(f"cris{prefix}", context.suffix, max_len=24)
    storage_tags = dict(tags)
    if intentional_public:
        storage_tags["cris-sme-public-intent"] = "public-media-content"
    run_az(
        [
            "storage",
            "account",
            "create",
            "--name",
            account_name,
            "--resource-group",
            context.resource_group,
            "--location",
            context.location,
            "--sku",
            "Standard_LRS",
            "--kind",
            "StorageV2",
            "--allow-blob-public-access",
            "true" if public_blob else "false",
            "--min-tls-version",
            "TLS1_2",
            *tag_args(storage_tags),
        ],
        context,
    )
    if public_blob:
        container_name = "public-evidence"
        run_az(
            [
                "storage",
                "container",
                "create",
                "--name",
                container_name,
                "--account-name",
                account_name,
                "--public-access",
                "blob",
                "--auth-mode",
                "login",
            ],
            context,
        )


def unique_name(prefix: str, suffix: str, *, max_len: int) -> str:
    raw = re.sub(r"[^a-z0-9]", "", f"{prefix}{suffix}".lower())
    if len(raw) > max_len:
        keep_suffix = min(len(suffix), max_len - len(prefix))
        raw = f"{prefix[: max_len - keep_suffix]}{suffix[-keep_suffix:]}"
    return raw


def format_tags(tags: dict[str, str]) -> list[str]:
    if not tags:
        return []
    return [f"{key}={value}" for key, value in tags.items()]


def tag_args(tags: dict[str, str]) -> list[str]:
    formatted = format_tags(tags)
    return ["--tags", *formatted] if formatted else []


def normalize_run_id(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9-]", "-", value.strip()).strip("-").lower()
    if not normalized:
        raise ValueError("run id cannot be empty")
    return normalized[:24]


def run_az(args: list[str], context: LabContext) -> None:
    run_command(["az", *args], context)


def run_command(
    command: list[str],
    context: LabContext,
    *,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> None:
    printable = " ".join(command)
    print(f"$ {printable}")
    if context.dry_run:
        return
    subprocess.run(command, cwd=cwd, env=env, check=True)


def manifest_path(context: LabContext) -> Path:
    directory = DEFAULT_OUTPUT_ROOT / context.run_id / str(context.scenario["id"])
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "lab_manifest.json"


def write_manifest(
    context: LabContext,
    *,
    status: str,
    output_dir: Path | None = None,
) -> None:
    if context.dry_run:
        print(f"Dry run: skipped lab manifest write for status '{status}'.")
        return
    payload = {
        "status": status,
        "generated_at": datetime.now(UTC).isoformat(),
        "run_id": context.run_id,
        "scenario": context.scenario,
        "location": context.location,
        "resource_group": context.resource_group,
        "tags": context.tags,
        "output_dir": str(output_dir) if output_dir else None,
    }
    path = manifest_path(context)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote lab manifest: {path}")


def copy_manifest_to_output(context: LabContext, output_dir: Path) -> None:
    source = manifest_path(context)
    if source.exists():
        shutil.copy2(source, output_dir / "lab_manifest.json")


if __name__ == "__main__":
    raise SystemExit(main())
