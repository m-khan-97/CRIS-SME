# Repeatable Azure evidence lab harness for CRIS-SME live dataset generation.
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
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
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm creation or deletion of Azure lab resources. Required for non-dry-run deploy, cleanup, and cycle actions.",
    )
    args = parser.parse_args()

    catalog = load_catalog()
    if args.action == "list":
        print(json.dumps(summarize_catalog(catalog), indent=2))
        return 0
    if args.action in {"deploy", "cleanup", "cycle"} and not args.dry_run and not args.yes:
        raise SystemExit(
            "Refusing to create or delete Azure resources without --yes. "
            "Use --dry-run to preview commands."
        )

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
        "cris-sme-owner": os.getenv("CRIS_SME_AZURE_LAB_OWNER", os.getenv("USER", "unknown")),
        "cris-sme-delete-after": (datetime.now(UTC) + timedelta(days=2)).date().isoformat(),
        "cris-sme-managed-by": "cris-sme-azure-evidence-lab",
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
    elif scenario_id == "iomt-clean-baseline":
        create_iomt_clean_baseline(context)
    elif scenario_id == "iomt-weak-baseline":
        create_iomt_weak_baseline(context)
    elif scenario_id == "iomt-simulated-clinic":
        create_iomt_simulated_clinic(context)
    elif scenario_id == "iomt-hardened-clinic":
        create_iomt_hardened_clinic(context)
    else:
        raise ValueError(f"Scenario '{scenario_id}' has no deployer.")

    write_manifest(context, status="deployed")
    print_assessment_command(context)


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
    env["CRIS_SME_AZURE_RESOURCE_GROUP_SCOPE"] = context.resource_group

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
    run_az(
        [
            "group",
            "wait",
            "--name",
            context.resource_group,
            "--deleted",
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


def create_iomt_clean_baseline(context: LabContext) -> None:
    workspace_name = create_log_analytics_workspace(context, "iomt-clean-law")
    hub_name = create_iot_hub(context, "iomtclean", public_network_access="Enabled")
    create_iot_device_identity(context, hub_name, "ward-monitor-001")
    create_iot_certificate(context, hub_name, "clinical-root-ca")
    configure_iot_diagnostics(context, hub_name, workspace_name)
    create_iot_metric_alert(context, hub_name, "iomt-clean-connectivity-alert")
    update_iot_hub_public_network_access(context, hub_name, "Disabled")
    create_storage(context, "iomtclean", public_blob=False, tags=context.tags)
    vault_name = unique_name("crisiomtkv", context.suffix, max_len=24)
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


def create_iomt_weak_baseline(context: LabContext) -> None:
    hub_name = create_iot_hub(context, "iomtweak", public_network_access="Enabled")
    create_iot_device_identity(context, hub_name, "legacy-infusion-001")
    create_iot_policy(
        context,
        hub_name,
        "legacy-all-access",
        ["RegistryWrite", "ServiceConnect", "DeviceConnect"],
    )
    create_storage(context, "iomtweak", public_blob=True, tags=context.tags)


def create_iomt_simulated_clinic(context: LabContext) -> None:
    workspace_name = create_log_analytics_workspace(context, "iomt-clinic-law")
    create_vnet_with_subnets(context, f"iomt-vnet-{context.run_id}"[:64])
    hub_name = create_iot_hub(context, "iomtclinic", public_network_access="Enabled")
    for device_id in (
        "ward-monitor-001",
        "bedside-sensor-002",
        "mobile-cart-003",
    ):
        create_iot_device_identity(context, hub_name, device_id)
    create_iot_certificate(context, hub_name, "clinic-root-ca")
    configure_iot_diagnostics(context, hub_name, workspace_name)
    create_iot_metric_alert(context, hub_name, "iomt-clinic-message-alert")
    create_storage(context, "iomtclinic", public_blob=False, tags=context.tags)
    vault_name = unique_name("crisiomtckv", context.suffix, max_len=24)
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


def create_iomt_hardened_clinic(context: LabContext) -> None:
    workspace_name = create_log_analytics_workspace(context, "iomt-hard-law")
    create_vnet_with_subnets(context, f"iomt-hard-vnet-{context.run_id}"[:64])
    hub_name = create_iot_hub(context, "iomthardened", public_network_access="Enabled")
    for device_id in (
        "ward-monitor-001",
        "bedside-sensor-002",
        "mobile-cart-003",
    ):
        create_iot_device_identity(context, hub_name, device_id)
    create_iot_certificate(context, hub_name, "hardened-clinic-root-ca")
    configure_iot_diagnostics(context, hub_name, workspace_name)
    create_iot_metric_alert(context, hub_name, "iomt-hardened-message-alert")
    storage_account_name = create_storage(
        context,
        "iomthard",
        public_blob=False,
        tags=context.tags,
    )
    configure_iot_storage_route(
        context,
        hub_name=hub_name,
        storage_account_name=storage_account_name,
        container_name="iomt-telemetry",
        endpoint_name="hardenedTelemetryStorage",
        route_name="hardenedTelemetryRoute",
    )
    update_iot_hub_public_network_access(context, hub_name, "Disabled")
    vault_name = unique_name("crisiomthkv", context.suffix, max_len=24)
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


def create_iot_hub(
    context: LabContext,
    prefix: str,
    *,
    public_network_access: str,
) -> str:
    hub_name = unique_name(prefix, context.suffix, max_len=50)
    sku = os.getenv("CRIS_SME_IOMT_IOTHUB_SKU", "F1")
    command = [
        "iot",
        "hub",
        "create",
        "--name",
        hub_name,
        "--resource-group",
        context.resource_group,
        "--location",
        context.location,
        "--sku",
        sku,
        "--partition-count",
        "2",
        *tag_args(context.tags),
    ]
    if context.location.lower() == "qatarcentral":
        command.extend(["--enforce-data-residency", "true"])
    run_az(command, context)
    run_az(
        [
            "iot",
            "hub",
            "update",
            "--name",
            hub_name,
            "--resource-group",
            context.resource_group,
            "--set",
            f"properties.publicNetworkAccess={public_network_access}",
        ],
        context,
    )
    return hub_name


def update_iot_hub_public_network_access(
    context: LabContext,
    hub_name: str,
    public_network_access: str,
) -> None:
    run_az(
        [
            "iot",
            "hub",
            "update",
            "--name",
            hub_name,
            "--resource-group",
            context.resource_group,
            "--set",
            f"properties.publicNetworkAccess={public_network_access}",
        ],
        context,
    )


def create_iot_device_identity(
    context: LabContext,
    hub_name: str,
    device_id: str,
) -> None:
    run_az(
        [
            "iot",
            "hub",
            "device-identity",
            "create",
            "--hub-name",
            hub_name,
            "--resource-group",
            context.resource_group,
            "--device-id",
            device_id,
            "--auth-method",
            "shared_private_key",
        ],
        context,
    )


def create_iot_certificate(context: LabContext, hub_name: str, certificate_name: str) -> None:
    if context.dry_run:
        print("Dry run: IoT certificate upload uses a temporary self-signed lab certificate.")
        return
    certificate_path = create_temporary_lab_certificate(context, certificate_name)
    run_az(
        [
            "iot",
            "hub",
            "certificate",
            "create",
            "--hub-name",
            hub_name,
            "--resource-group",
            context.resource_group,
            "--name",
            certificate_name,
            "--path",
            str(certificate_path),
        ],
        context,
    )


def create_temporary_lab_certificate(context: LabContext, certificate_name: str) -> Path:
    certificate_dir = Path(tempfile.gettempdir()) / "cris-sme-iomt-certs" / context.run_id
    certificate_dir.mkdir(parents=True, exist_ok=True)
    key_path = certificate_dir / f"{certificate_name}.key"
    certificate_path = certificate_dir / f"{certificate_name}.cer"
    command = [
        "openssl",
        "req",
        "-x509",
        "-newkey",
        "rsa:2048",
        "-keyout",
        str(key_path),
        "-out",
        str(certificate_path),
        "-days",
        "2",
        "-nodes",
        "-subj",
        f"/CN={certificate_name}.cris-sme-iomt-lab",
    ]
    print(f"$ {' '.join(command)}")
    subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return certificate_path


def create_iot_policy(
    context: LabContext,
    hub_name: str,
    policy_name: str,
    rights: list[str],
) -> None:
    run_az(
        [
            "iot",
            "hub",
            "policy",
            "create",
            "--hub-name",
            hub_name,
            "--resource-group",
            context.resource_group,
            "--name",
            policy_name,
            "--permissions",
            *rights,
        ],
        context,
    )


def create_log_analytics_workspace(context: LabContext, prefix: str) -> str:
    workspace_name = unique_name(prefix, context.suffix, max_len=63)
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
    return workspace_name


def configure_iot_diagnostics(
    context: LabContext,
    hub_name: str,
    workspace_name: str,
) -> None:
    if context.dry_run:
        print(
            "Dry run: diagnostic settings use live resource IDs resolved after deployment."
        )
        return
    hub_id = capture_az_text(
        [
            "iot",
            "hub",
            "show",
            "--name",
            hub_name,
            "--resource-group",
            context.resource_group,
            "--query",
            "id",
            "--output",
            "tsv",
        ],
        context,
    )
    workspace_id = capture_az_text(
        [
            "monitor",
            "log-analytics",
            "workspace",
            "show",
            "--workspace-name",
            workspace_name,
            "--resource-group",
            context.resource_group,
            "--query",
            "id",
            "--output",
            "tsv",
        ],
        context,
    )
    run_az(
        [
            "monitor",
            "diagnostic-settings",
            "create",
            "--name",
            "cris-iomt-diagnostics",
            "--resource",
            hub_id,
            "--workspace",
            workspace_id,
            "--logs",
            '[{"categoryGroup":"allLogs","enabled":true}]',
            "--metrics",
            '[{"category":"AllMetrics","enabled":true}]',
        ],
        context,
    )


def create_iot_metric_alert(context: LabContext, hub_name: str, alert_name: str) -> None:
    if context.dry_run:
        print("Dry run: IoT metric alert uses the hub resource ID resolved after deployment.")
        return
    hub_id = capture_az_text(
        [
            "iot",
            "hub",
            "show",
            "--name",
            hub_name,
            "--resource-group",
            context.resource_group,
            "--query",
            "id",
            "--output",
            "tsv",
        ],
        context,
    )
    action_group_name = unique_name("iomt-ag", context.suffix, max_len=64)
    run_az(
        [
            "monitor",
            "action-group",
            "create",
            "--name",
            action_group_name,
            "--resource-group",
            context.resource_group,
            "--short-name",
            "iomtsec",
            *tag_args(context.tags),
        ],
        context,
    )
    run_az(
        [
            "monitor",
            "metrics",
            "alert",
            "create",
            "--name",
            alert_name,
            "--resource-group",
            context.resource_group,
            "--scopes",
            hub_id,
            "--condition",
            "avg dailyMessageQuotaUsed > 0",
            "--window-size",
            "5m",
            "--evaluation-frequency",
            "5m",
            "--action",
            action_group_name,
            *tag_args(context.tags),
        ],
        context,
    )


def configure_iot_storage_route(
    context: LabContext,
    *,
    hub_name: str,
    storage_account_name: str,
    container_name: str,
    endpoint_name: str,
    route_name: str,
) -> None:
    if context.dry_run:
        print("Dry run: IoT storage routing uses a storage connection string resolved after deployment.")
        return
    run_az(
        [
            "storage",
            "container",
            "create",
            "--name",
            container_name,
            "--account-name",
            storage_account_name,
            "--auth-mode",
            "login",
        ],
        context,
    )
    connection_string = capture_az_text(
        [
            "storage",
            "account",
            "show-connection-string",
            "--name",
            storage_account_name,
            "--resource-group",
            context.resource_group,
            "--query",
            "connectionString",
            "--output",
            "tsv",
        ],
        context,
    )
    subscription_id = capture_az_text(
        [
            "account",
            "show",
            "--query",
            "id",
            "--output",
            "tsv",
        ],
        context,
    )
    run_az(
        [
            "iot",
            "hub",
            "routing-endpoint",
            "create",
            "--hub-name",
            hub_name,
            "--resource-group",
            context.resource_group,
            "--endpoint-name",
            endpoint_name,
            "--endpoint-type",
            "azurestoragecontainer",
            "--endpoint-resource-group",
            context.resource_group,
            "--endpoint-subscription-id",
            subscription_id,
            "--connection-string",
            connection_string,
            "--container-name",
            container_name,
            "--encoding",
            "json",
            "--batch-frequency",
            "300",
            "--chunk-size",
            "100",
        ],
        context,
    )
    run_az(
        [
            "iot",
            "hub",
            "route",
            "create",
            "--hub-name",
            hub_name,
            "--resource-group",
            context.resource_group,
            "--endpoint-name",
            endpoint_name,
            "--source",
            "devicemessages",
            "--route-name",
            route_name,
            "--condition",
            "true",
            "--enabled",
            "true",
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
) -> str:
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
    return account_name


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


def capture_az_text(args: list[str], context: LabContext) -> str:
    command = ["az", *args]
    printable = " ".join(redact_command_for_logging(command))
    print(f"$ {printable}")
    completed = subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.strip()


def run_command(
    command: list[str],
    context: LabContext,
    *,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> None:
    printable = " ".join(redact_command_for_logging(command))
    print(f"$ {printable}")
    if context.dry_run:
        return
    subprocess.run(command, cwd=cwd, env=env, check=True)


def redact_command_for_logging(command: list[str]) -> list[str]:
    redacted = list(command)
    sensitive_flags = {
        "--connection-string",
        "--sas-token",
        "--account-key",
        "--key",
        "--password",
        "--client-secret",
    }
    for index, value in enumerate(redacted[:-1]):
        if value in sensitive_flags:
            redacted[index + 1] = "[redacted]"
    return redacted


def print_assessment_command(context: LabContext) -> None:
    command = [
        "python3",
        "scripts/azure_evidence_lab.py",
        "assess",
        "--scenario",
        str(context.scenario["id"]),
        "--run-id",
        context.run_id,
        "--resource-group",
        context.resource_group,
    ]
    print("Next assessment command:")
    print(f"$ {' '.join(command)}")


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
