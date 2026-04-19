# Azure-backed collector for building provider-normalized CRIS-SME profiles from Azure account context.
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
import signal
import subprocess
from typing import Any, Callable

from cris_sme.collectors.providers import get_profile_adapter
from cris_sme.models.cloud_profile import (
    CloudProfile,
    ComputeProfile,
    DataProfile,
    GovernanceProfile,
    IamProfile,
    MonitoringProfile,
    NetworkProfile,
)

CredentialFactory = Callable[[], Any]
SubscriptionClientFactory = Callable[[Any], Any]
NetworkClientFactory = Callable[[Any, str], Any]
ResourceClientFactory = Callable[[Any, str], Any]
StorageClientFactory = Callable[[Any, str], Any]
SqlClientFactory = Callable[[Any, str], Any]
ComputeClientFactory = Callable[[Any, str], Any]


@dataclass(slots=True)
class AzureCollectorSettings:
    """Configuration for the first-stage Azure-backed collector."""

    subscription_id: str | None = None
    organization_name: str = "Azure SME Tenant"
    sector: str = "SME"
    tenant_scope: str | None = None
    organization_id: str | None = None
    dataset_source_type: str = "live_real"
    authorization_basis: str = "authorized_tenant_access"
    dataset_use: str = "live_case_study"


class AzureCollector:
    """Collect Azure subscription context and normalize it into CRIS-SME cloud profiles."""

    def __init__(
        self,
        settings: AzureCollectorSettings | None = None,
        credential_factory: CredentialFactory | None = None,
        subscription_client_factory: SubscriptionClientFactory | None = None,
        network_client_factory: NetworkClientFactory | None = None,
        resource_client_factory: ResourceClientFactory | None = None,
        storage_client_factory: StorageClientFactory | None = None,
        sql_client_factory: SqlClientFactory | None = None,
        compute_client_factory: ComputeClientFactory | None = None,
    ) -> None:
        self.settings = settings or AzureCollectorSettings()
        self._credential_factory = credential_factory
        self._subscription_client_factory = subscription_client_factory
        self._network_client_factory = network_client_factory
        self._resource_client_factory = resource_client_factory
        self._storage_client_factory = storage_client_factory
        self._sql_client_factory = sql_client_factory
        self._compute_client_factory = compute_client_factory

    def collect_raw_profiles(self) -> list[dict[str, Any]]:
        """Return conservative raw Azure profiles built from authenticated subscription metadata."""
        subscription_records = self._collect_subscription_records()
        return [
            self._build_raw_profile_from_subscription(record)
            for record in subscription_records
        ]

    def collect_profiles(self) -> list[CloudProfile]:
        """Return provider-normalized Azure cloud profiles."""
        adapter = get_profile_adapter("azure")
        profiles = [
            adapter.normalize_profile(raw_profile)
            for raw_profile in self.collect_raw_profiles()
        ]

        if self.settings.subscription_id:
            filtered_profiles = [
                profile
                for profile in profiles
                if profile.metadata.get("subscription_id")
                == self.settings.subscription_id
            ]
            if not filtered_profiles:
                raise ValueError(
                    f"Azure subscription '{self.settings.subscription_id}' was not found "
                    "for the current credential context."
                )
            return filtered_profiles

        return profiles

    def _collect_subscription_records(self) -> list[dict[str, Any]]:
        """Enumerate enabled Azure subscriptions and return normalized metadata records."""
        # Prefer Azure CLI discovery because it is the most stable path in the
        # current project environment and avoids indefinite SDK subscription hangs.
        records = self._collect_subscription_records_from_cli()

        if not records:
            records = self._collect_subscription_records_from_sdk()

        if not records:
            raise ValueError(
                "No enabled Azure subscriptions were returned for the current credential context."
            )

        return records

    def _collect_subscription_records_from_sdk(self) -> list[dict[str, Any]]:
        """Return enabled Azure subscriptions from the Azure SDK as a fallback path."""
        try:
            credential = self._build_credential()
            client = self._build_subscription_client(credential)
            subscriptions = list(client.subscriptions.list())
        except Exception:
            return []

        records: list[dict[str, Any]] = []
        for subscription in subscriptions:
            raw_state = getattr(subscription, "state", "Unknown")
            state = str(raw_state)
            if state.lower() != "enabled":
                continue

            records.append(
                {
                    "subscription_id": getattr(subscription, "subscription_id", None),
                    "display_name": getattr(
                        subscription,
                        "display_name",
                        "Azure Subscription",
                    ),
                    "tenant_id": getattr(subscription, "tenant_id", None),
                    "state": state,
                }
            )

        return records

    def _collect_subscription_records_from_cli(self) -> list[dict[str, Any]]:
        """Return enabled Azure subscriptions from the Azure CLI as a fallback path."""
        completed = self._run_cli_command(
            ["az", "account", "list", "--output", "json"],
            timeout=20,
        )
        if completed is None:
            return []

        try:
            raw_subscriptions = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return []

        records: list[dict[str, Any]] = []
        for subscription in raw_subscriptions:
            state = str(subscription.get("state", "Unknown"))
            if state.lower() != "enabled":
                continue

            records.append(
                {
                    "subscription_id": subscription.get("id"),
                    "display_name": subscription.get("name", "Azure Subscription"),
                    "tenant_id": subscription.get("tenantId")
                    or subscription.get("homeTenantId"),
                    "state": state,
                }
            )

        return records

    def _build_raw_profile_from_subscription(
        self,
        subscription_record: dict[str, Any],
    ) -> dict[str, Any]:
        """Build a conservative raw Azure profile for adapter normalization."""
        subscription_id = str(
            subscription_record.get("subscription_id") or "unknown-subscription"
        )
        tenant_id = str(
            subscription_record.get("tenant_id")
            or self.settings.tenant_scope
            or "unknown-tenant"
        )
        display_name = str(
            subscription_record.get("display_name") or self.settings.organization_name
        )

        organization_id = self.settings.organization_id or f"azure-{subscription_id}"
        organization_name = self.settings.organization_name or display_name
        tenant_scope = self.settings.tenant_scope or tenant_id
        credential = self._build_credential()
        iam_profile, iam_metadata = self._collect_iam_profile(
            subscription_id=subscription_id,
        )
        network_profile, network_metadata = self._collect_network_profile(
            subscription_id=subscription_id,
            credential=credential,
        )
        data_profile, data_metadata = self._collect_data_profile(
            subscription_id=subscription_id,
            credential=credential,
        )
        monitoring_profile, monitoring_metadata = self._collect_monitoring_profile(
            subscription_id=subscription_id,
            credential=credential,
        )
        compute_profile, compute_metadata = self._collect_compute_profile(
            subscription_id=subscription_id,
            credential=credential,
        )
        governance_profile, governance_metadata = self._collect_governance_profile(
            subscription_id=subscription_id,
            credential=credential,
        )
        native_recommendations = self._collect_security_assessments_from_cli(
            subscription_id
        )

        return {
            "organization_id": organization_id,
            "organization_name": organization_name,
            "provider": "azure",
            "sector": self.settings.sector,
            "tenant_scope": tenant_scope,
            "iam": iam_profile.model_dump(),
            "network": network_profile.model_dump(),
            "data": data_profile.model_dump(),
            "monitoring": monitoring_profile.model_dump(),
            "compute": compute_profile.model_dump(),
            "governance": governance_profile.model_dump(),
            "metadata": {
                "collection_mode": "azure_sdk_subscription_inventory",
                "profile_source": "azure_live",
                "dataset_source_type": self.settings.dataset_source_type,
                "authorization_basis": self.settings.authorization_basis,
                "dataset_use": self.settings.dataset_use,
                "subscription_id": subscription_id,
                "subscription_display_name": display_name,
                "subscription_state": subscription_record.get("state", "Unknown"),
                "tenant_id": tenant_id,
                "iam_collection_mode": iam_metadata["iam_collection_mode"],
                "privileged_assignment_count": iam_metadata[
                    "privileged_assignment_count"
                ],
                "privileged_principal_count": iam_metadata[
                    "privileged_principal_count"
                ],
                "conditional_access_accessible": iam_metadata[
                    "conditional_access_accessible"
                ],
                "conditional_access_policy_count": iam_metadata[
                    "conditional_access_policy_count"
                ],
                "identity_observability": iam_metadata["identity_observability"],
                "service_principal_role_assignment_count": iam_metadata[
                    "service_principal_role_assignment_count"
                ],
                "privileged_user_assignment_count": iam_metadata[
                    "privileged_user_assignment_count"
                ],
                "privileged_service_principal_assignment_count": iam_metadata[
                    "privileged_service_principal_assignment_count"
                ],
                "disabled_service_principal_count": iam_metadata[
                    "disabled_service_principal_count"
                ],
                "signed_in_user_directory_role_count": iam_metadata[
                    "signed_in_user_directory_role_count"
                ],
                "signed_in_user_is_directory_admin": iam_metadata[
                    "signed_in_user_is_directory_admin"
                ],
                "signed_in_user_directory_roles_visible": iam_metadata[
                    "signed_in_user_directory_roles_visible"
                ],
                "visible_directory_role_catalog_count": iam_metadata[
                    "visible_directory_role_catalog_count"
                ],
                "directory_role_catalog_visible": iam_metadata[
                    "directory_role_catalog_visible"
                ],
                "collector_stage": "azure_live_enriched",
                "network_collection_mode": network_metadata["network_collection_mode"],
                "data_collection_mode": data_metadata["data_collection_mode"],
                "storage_account_count": data_metadata["storage_account_count"],
                "public_storage_asset_count": data_metadata[
                    "public_storage_asset_count"
                ],
                "unencrypted_data_store_count": data_metadata[
                    "unencrypted_data_store_count"
                ],
                "sql_server_count": data_metadata["sql_server_count"],
                "sql_database_count": data_metadata["sql_database_count"],
                "public_sql_server_count": data_metadata["public_sql_server_count"],
                "unencrypted_sql_database_count": data_metadata[
                    "unencrypted_sql_database_count"
                ],
                "monitoring_collection_mode": monitoring_metadata[
                    "monitoring_collection_mode"
                ],
                "activity_log_alert_count": monitoring_metadata[
                    "activity_log_alert_count"
                ],
                "logic_app_workflow_count": monitoring_metadata[
                    "logic_app_workflow_count"
                ],
                "defender_standard_plan_count": monitoring_metadata[
                    "defender_standard_plan_count"
                ],
                "compute_collection_mode": compute_metadata["compute_collection_mode"],
                "virtual_machine_count": compute_metadata["virtual_machine_count"],
                "vm_extension_covered_count": compute_metadata[
                    "vm_extension_covered_count"
                ],
                "vm_hardening_covered_count": compute_metadata[
                    "vm_hardening_covered_count"
                ],
                "vm_backup_protected_count": compute_metadata[
                    "vm_backup_protected_count"
                ],
                "vm_patch_compliant_count": compute_metadata[
                    "vm_patch_compliant_count"
                ],
                "linux_password_auth_enabled_vm_count": compute_metadata[
                    "linux_password_auth_enabled_vm_count"
                ],
                "governance_collection_mode": governance_metadata[
                    "governance_collection_mode"
                ],
                "governance_resource_count": governance_metadata[
                    "governance_resource_count"
                ],
                "policy_assignment_count": governance_metadata[
                    "policy_assignment_count"
                ],
                "orphaned_resource_count": governance_metadata[
                    "orphaned_resource_count"
                ],
                "native_recommendation_collection_mode": (
                    "azure_security_assessment_inventory"
                    if native_recommendations
                    else "default_no_native_recommendation_inventory"
                ),
                "native_security_recommendation_count": len(native_recommendations),
                "native_unhealthy_recommendation_count": sum(
                    1
                    for item in native_recommendations
                    if str(item.get("status_code", "")).lower() == "unhealthy"
                ),
                "native_security_recommendations": native_recommendations[:50],
                "note": (
                    "This profile was created from live Azure account context. "
                    "IAM, network, data, monitoring, compute, and governance posture "
                    "include live Azure evidence where available. Some identity controls, "
                    "especially conditional access validation, remain partially constrained "
                    "by tenant permissions and current collector scope."
                ),
            },
        }

    def _collect_iam_profile(
        self,
        subscription_id: str,
    ) -> tuple[IamProfile, dict[str, int | str | bool]]:
        """Collect IAM posture from Azure role assignments and accessible Graph signals."""
        role_assignments = self._collect_role_assignments_from_cli(subscription_id)
        privileged_role_names = {
            "owner",
            "user access administrator",
        }
        privileged_assignments = [
            assignment
            for assignment in role_assignments
            if str(assignment.get("roleDefinitionName", "")).strip().lower()
            in privileged_role_names
        ]

        privileged_principal_ids = {
            str(assignment.get("principalId"))
            for assignment in privileged_assignments
            if assignment.get("principalId")
        }
        privileged_principal_count = len(privileged_principal_ids)
        privileged_assignment_count = len(privileged_assignments)
        overprivileged_accounts = max(
            privileged_assignment_count - privileged_principal_count,
            0,
        )

        service_principal_assignment_ids = {
            str(assignment.get("principalId"))
            for assignment in role_assignments
            if str(assignment.get("principalType", "")).lower() == "serviceprincipal"
            and assignment.get("principalId")
        }
        (
            stale_service_principals,
            disabled_service_principals,
        ) = self._collect_service_principal_posture(
            principal_ids=service_principal_assignment_ids,
        )
        privileged_user_assignments = sum(
            1
            for assignment in privileged_assignments
            if str(assignment.get("principalType", "")).lower() == "user"
        )
        privileged_service_principal_assignments = sum(
            1
            for assignment in privileged_assignments
            if str(assignment.get("principalType", "")).lower() == "serviceprincipal"
        )

        (
            conditional_access_enforced_for_admins,
            conditional_access_accessible,
            conditional_access_policy_count,
        ) = self._collect_conditional_access_signal()
        (
            signed_in_user_directory_roles,
            signed_in_user_is_directory_admin,
            signed_in_user_directory_roles_visible,
        ) = self._collect_signed_in_user_directory_roles()
        (
            visible_directory_role_catalog_entries,
            directory_role_catalog_visible,
        ) = self._collect_directory_role_catalog_context()
        identity_observability = (
            "broad"
            if directory_role_catalog_visible
            else "expanded"
            if signed_in_user_directory_roles_visible and not conditional_access_accessible
            else "partial"
            if not conditional_access_accessible
            else "full"
        )

        return (
            IamProfile(
                privileged_accounts=privileged_principal_count,
                privileged_accounts_without_mfa=0,
                overprivileged_accounts=overprivileged_accounts,
                stale_service_principals=stale_service_principals,
                rbac_review_age_days=0,
                conditional_access_enforced_for_admins=(
                    conditional_access_enforced_for_admins
                    if conditional_access_accessible
                    else True
                ),
                privileged_user_assignments=privileged_user_assignments,
                privileged_service_principal_assignments=(
                    privileged_service_principal_assignments
                ),
                disabled_service_principals=disabled_service_principals,
                signed_in_user_directory_roles=signed_in_user_directory_roles,
                signed_in_user_is_directory_admin=signed_in_user_is_directory_admin,
                visible_directory_role_catalog_entries=(
                    visible_directory_role_catalog_entries
                ),
                directory_role_catalog_visible=directory_role_catalog_visible,
                identity_observability=identity_observability,
            ),
            {
                "iam_collection_mode": (
                    "azure_role_assignments_and_graph"
                    if role_assignments
                    else "default_no_iam_inventory"
                ),
                "privileged_assignment_count": privileged_assignment_count,
                "privileged_principal_count": privileged_principal_count,
                "conditional_access_accessible": conditional_access_accessible,
                "conditional_access_policy_count": conditional_access_policy_count,
                "service_principal_role_assignment_count": len(
                    service_principal_assignment_ids
                ),
                "privileged_user_assignment_count": privileged_user_assignments,
                "privileged_service_principal_assignment_count": (
                    privileged_service_principal_assignments
                ),
                "disabled_service_principal_count": disabled_service_principals,
                "signed_in_user_directory_role_count": signed_in_user_directory_roles,
                "signed_in_user_is_directory_admin": (
                    signed_in_user_is_directory_admin
                ),
                "signed_in_user_directory_roles_visible": (
                    signed_in_user_directory_roles_visible
                ),
                "visible_directory_role_catalog_count": (
                    visible_directory_role_catalog_entries
                ),
                "directory_role_catalog_visible": directory_role_catalog_visible,
                "identity_observability": identity_observability,
            },
        )

    def _collect_compute_profile(
        self,
        subscription_id: str,
        credential: Any,
    ) -> tuple[ComputeProfile, dict[str, int | str]]:
        """Collect compute posture from Azure VM inventory, VM settings, and backup signals."""
        if self._compute_client_factory is None and self._credential_factory is None:
            raw_virtual_machines = self._collect_virtual_machines_from_cli(
                subscription_id
            )
            if isinstance(raw_virtual_machines, list) and raw_virtual_machines:
                return self._build_compute_profile_from_cli_inventory(
                    subscription_id=subscription_id,
                    virtual_machines=raw_virtual_machines,
                )

        try:
            client = self._build_compute_client(credential, subscription_id)
            virtual_machines = list(client.virtual_machines.list_all())
        except Exception:
            return (
                ComputeProfile(
                    unpatched_critical_vms=0,
                    endpoint_protection_coverage_ratio=0.0,
                    hardened_baseline_coverage_ratio=0.0,
                    workload_backup_agent_coverage_ratio=0.0,
                ),
                {
                    "compute_collection_mode": "default_no_compute_inventory",
                    "virtual_machine_count": 0,
                    "vm_extension_covered_count": 0,
                    "vm_hardening_covered_count": 0,
                    "vm_backup_protected_count": 0,
                    "vm_patch_compliant_count": 0,
                    "linux_password_auth_enabled_vm_count": 0,
                },
            )

        vm_count = len(virtual_machines)
        if vm_count == 0:
            return (
                ComputeProfile(
                    unpatched_critical_vms=0,
                    endpoint_protection_coverage_ratio=0.0,
                    hardened_baseline_coverage_ratio=0.0,
                    workload_backup_agent_coverage_ratio=0.0,
                ),
                {
                    "compute_collection_mode": "azure_compute_inventory_no_vms",
                    "virtual_machine_count": 0,
                    "vm_extension_covered_count": 0,
                    "vm_hardening_covered_count": 0,
                    "vm_backup_protected_count": 0,
                    "vm_patch_compliant_count": 0,
                    "linux_password_auth_enabled_vm_count": 0,
                },
            )

        endpoint_covered_count = 0
        hardening_covered_count = 0
        patch_compliant_count = 0
        linux_password_auth_enabled_count = 0

        for vm in virtual_machines:
            resource_group_name = self._extract_resource_group_name(getattr(vm, "id", None))
            vm_name = getattr(vm, "name", None)

            if resource_group_name and vm_name:
                extensions = self._collect_vm_extensions(
                    client=client,
                    resource_group_name=resource_group_name,
                    vm_name=str(vm_name),
                )
            else:
                extensions = []

            if self._vm_has_endpoint_protection_signal(vm, extensions):
                endpoint_covered_count += 1

            if self._vm_meets_hardening_proxy(vm):
                hardening_covered_count += 1

            if self._vm_meets_patch_compliance_proxy(vm):
                patch_compliant_count += 1

            if self._vm_allows_password_authentication(vm):
                linux_password_auth_enabled_count += 1

        backup_protected_count = self._collect_backup_protected_vm_count_from_cli(
            subscription_id=subscription_id,
        )
        backup_protected_count = min(backup_protected_count, vm_count)

        endpoint_coverage_ratio = round(endpoint_covered_count / vm_count, 4)
        hardening_coverage_ratio = round(hardening_covered_count / vm_count, 4)
        backup_coverage_ratio = round(backup_protected_count / vm_count, 4)
        unpatched_critical_vms = max(vm_count - patch_compliant_count, 0)

        return (
            ComputeProfile(
                unpatched_critical_vms=unpatched_critical_vms,
                endpoint_protection_coverage_ratio=endpoint_coverage_ratio,
                hardened_baseline_coverage_ratio=hardening_coverage_ratio,
                workload_backup_agent_coverage_ratio=backup_coverage_ratio,
                linux_password_auth_enabled_vms=linux_password_auth_enabled_count,
            ),
            {
                "compute_collection_mode": "azure_compute_inventory",
                "virtual_machine_count": vm_count,
                "vm_extension_covered_count": endpoint_covered_count,
                "vm_hardening_covered_count": hardening_covered_count,
                "vm_backup_protected_count": backup_protected_count,
                "vm_patch_compliant_count": patch_compliant_count,
                "linux_password_auth_enabled_vm_count": (
                    linux_password_auth_enabled_count
                ),
            },
        )

    def _build_compute_profile_from_cli_inventory(
        self,
        subscription_id: str,
        virtual_machines: list[dict[str, Any]],
    ) -> tuple[ComputeProfile, dict[str, int | str]]:
        """Build compute posture from Azure CLI VM inventory."""
        vm_count = len(virtual_machines)
        endpoint_covered_count = 0
        hardening_covered_count = 0
        patch_compliant_count = 0
        linux_password_auth_enabled_count = 0

        for vm in virtual_machines:
            resource_group_name = vm.get("resourceGroup") or self._extract_resource_group_name(
                vm.get("id")
            )
            vm_name = vm.get("name")
            if resource_group_name and vm_name:
                extensions = self._collect_vm_extensions_from_cli(
                    subscription_id=subscription_id,
                    resource_group_name=str(resource_group_name),
                    vm_name=str(vm_name),
                )
            else:
                extensions = []

            if self._vm_has_endpoint_protection_signal(vm, extensions):
                endpoint_covered_count += 1

            if self._vm_meets_hardening_proxy(vm):
                hardening_covered_count += 1

            if self._vm_meets_patch_compliance_proxy(vm):
                patch_compliant_count += 1

            if self._vm_allows_password_authentication(vm):
                linux_password_auth_enabled_count += 1

        backup_protected_count = self._collect_backup_protected_vm_count_from_cli(
            subscription_id=subscription_id,
        )
        backup_protected_count = min(backup_protected_count, vm_count)

        endpoint_coverage_ratio = round(endpoint_covered_count / vm_count, 4)
        hardening_coverage_ratio = round(hardening_covered_count / vm_count, 4)
        backup_coverage_ratio = round(backup_protected_count / vm_count, 4)
        unpatched_critical_vms = max(vm_count - patch_compliant_count, 0)

        return (
            ComputeProfile(
                unpatched_critical_vms=unpatched_critical_vms,
                endpoint_protection_coverage_ratio=endpoint_coverage_ratio,
                hardened_baseline_coverage_ratio=hardening_coverage_ratio,
                workload_backup_agent_coverage_ratio=backup_coverage_ratio,
                linux_password_auth_enabled_vms=linux_password_auth_enabled_count,
            ),
            {
                "compute_collection_mode": "azure_compute_cli_inventory",
                "virtual_machine_count": vm_count,
                "vm_extension_covered_count": endpoint_covered_count,
                "vm_hardening_covered_count": hardening_covered_count,
                "vm_backup_protected_count": backup_protected_count,
                "vm_patch_compliant_count": patch_compliant_count,
                "linux_password_auth_enabled_vm_count": (
                    linux_password_auth_enabled_count
                ),
            },
        )

    def _collect_data_profile(
        self,
        subscription_id: str,
        credential: Any,
    ) -> tuple[DataProfile, dict[str, int | str]]:
        """Collect Azure storage posture for public access, encryption, and retention signals."""
        if (
            self._storage_client_factory is None
            and self._sql_client_factory is None
            and self._credential_factory is None
        ):
            cli_data_profile = self._collect_data_profile_from_cli(subscription_id)
            if cli_data_profile is not None:
                return cli_data_profile

        try:
            client = self._build_storage_client(credential, subscription_id)
            storage_accounts = list(client.storage_accounts.list())
        except Exception:
            client = None
            storage_accounts = []

        public_storage_assets = 0
        unencrypted_data_stores = 0
        retention_enabled_count = 0

        for account in storage_accounts:
            if self._storage_account_is_public(account):
                public_storage_assets += 1

            if not self._storage_account_is_encrypted(account):
                unencrypted_data_stores += 1

            blob_properties = self._get_blob_service_properties(client, account)
            if blob_properties is not None and self._blob_retention_enabled(blob_properties):
                retention_enabled_count += 1

        storage_account_count = len(storage_accounts)
        covered_data_store_count = retention_enabled_count
        total_data_store_count = storage_account_count
        sql_server_count = 0
        sql_database_count = 0
        public_sql_server_count = 0
        unencrypted_sql_database_count = 0

        try:
            sql_client = self._build_sql_client(credential, subscription_id)
            sql_servers = list(sql_client.servers.list())
        except Exception:
            sql_servers = []

        sql_server_count = len(sql_servers)

        for server in sql_servers:
            if self._sql_server_is_public(server):
                public_sql_server_count += 1

            resource_group_name = self._extract_resource_group_name(
                getattr(server, "id", None)
            )
            server_name = getattr(server, "name", None)
            if not resource_group_name or not server_name:
                continue

            try:
                databases = list(
                    sql_client.databases.list_by_server(
                        resource_group_name=resource_group_name,
                        server_name=server_name,
                    )
                )
            except Exception:
                continue

            for database in databases:
                database_name = str(getattr(database, "name", ""))
                if database_name.lower() == "master":
                    continue

                sql_database_count += 1
                total_data_store_count += 1

                if self._sql_database_is_encrypted(
                    sql_client=sql_client,
                    resource_group_name=resource_group_name,
                    server_name=str(server_name),
                    database_name=database_name,
                ):
                    covered_data_store_count += 1
                else:
                    unencrypted_data_stores += 1
                    unencrypted_sql_database_count += 1

        coverage_ratio = (
            round(covered_data_store_count / total_data_store_count, 4)
            if total_data_store_count
            else 0.0
        )

        return (
            DataProfile(
                public_storage_assets=public_storage_assets,
                unencrypted_data_stores=unencrypted_data_stores,
                backup_coverage_ratio=coverage_ratio,
                retention_policy_coverage_ratio=coverage_ratio,
                key_vault_mfa_enabled=False,
                key_vault_purge_protection_enabled=False,
            ),
            {
                "data_collection_mode": (
                    "azure_storage_and_sql_inventory"
                    if storage_account_count and sql_server_count
                    else "azure_storage_inventory"
                    if storage_account_count
                    else "azure_sql_inventory"
                    if sql_server_count
                    else "default_no_storage_inventory"
                ),
                "storage_account_count": storage_account_count,
                "public_storage_asset_count": public_storage_assets,
                "unencrypted_data_store_count": unencrypted_data_stores,
                "sql_server_count": sql_server_count,
                "sql_database_count": sql_database_count,
                "public_sql_server_count": public_sql_server_count,
                "unencrypted_sql_database_count": unencrypted_sql_database_count,
            },
        )

    def _collect_data_profile_from_cli(
        self,
        subscription_id: str,
    ) -> tuple[DataProfile, dict[str, int | str]] | None:
        """Collect Azure data posture from Azure CLI inventory."""
        storage_accounts = self._run_cli_json(
            [
                "az",
                "storage",
                "account",
                "list",
                "--subscription",
                subscription_id,
                "--output",
                "json",
            ]
        )
        sql_servers = self._run_cli_json(
            [
                "az",
                "sql",
                "server",
                "list",
                "--subscription",
                subscription_id,
                "--output",
                "json",
            ]
        )

        if not isinstance(storage_accounts, list) and not isinstance(sql_servers, list):
            return None

        public_storage_assets = 0
        unencrypted_data_stores = 0
        retention_enabled_count = 0
        storage_account_count = len(storage_accounts) if isinstance(storage_accounts, list) else 0

        for account in storage_accounts if isinstance(storage_accounts, list) else []:
            if self._storage_account_is_public_dict(account):
                public_storage_assets += 1
            if not self._storage_account_is_encrypted_dict(account):
                unencrypted_data_stores += 1

        covered_data_store_count = retention_enabled_count
        total_data_store_count = storage_account_count
        sql_server_count = 0
        sql_database_count = 0
        public_sql_server_count = 0
        unencrypted_sql_database_count = 0

        for server in sql_servers if isinstance(sql_servers, list) else []:
            sql_server_count += 1
            if self._sql_server_is_public_dict(server):
                public_sql_server_count += 1

            resource_group_name = server.get("resourceGroup")
            server_name = server.get("name")
            if not resource_group_name or not server_name:
                continue

            databases = self._run_cli_json(
                [
                    "az",
                    "sql",
                    "db",
                    "list",
                    "--subscription",
                    subscription_id,
                    "--resource-group",
                    str(resource_group_name),
                    "--server",
                    str(server_name),
                    "--output",
                    "json",
                ]
            )
            if not isinstance(databases, list):
                continue

            for database in databases:
                database_name = str(database.get("name", ""))
                if database_name.lower() == "master":
                    continue

                sql_database_count += 1
                total_data_store_count += 1
                if self._sql_database_is_encrypted_from_cli(
                    subscription_id=subscription_id,
                    resource_group_name=str(resource_group_name),
                    server_name=str(server_name),
                    database_name=database_name,
                ):
                    covered_data_store_count += 1
                else:
                    unencrypted_data_stores += 1
                    unencrypted_sql_database_count += 1

        coverage_ratio = (
            round(covered_data_store_count / total_data_store_count, 4)
            if total_data_store_count
            else 0.0
        )

        return (
            DataProfile(
                public_storage_assets=public_storage_assets,
                unencrypted_data_stores=unencrypted_data_stores,
                backup_coverage_ratio=coverage_ratio,
                retention_policy_coverage_ratio=coverage_ratio,
                key_vault_mfa_enabled=False,
                key_vault_purge_protection_enabled=False,
            ),
            {
                "data_collection_mode": (
                    "azure_storage_and_sql_cli_inventory"
                    if storage_account_count and sql_server_count
                    else "azure_storage_cli_inventory"
                    if storage_account_count
                    else "azure_sql_cli_inventory"
                    if sql_server_count
                    else "default_no_storage_inventory"
                ),
                "storage_account_count": storage_account_count,
                "public_storage_asset_count": public_storage_assets,
                "unencrypted_data_store_count": unencrypted_data_stores,
                "sql_server_count": sql_server_count,
                "sql_database_count": sql_database_count,
                "public_sql_server_count": public_sql_server_count,
                "unencrypted_sql_database_count": unencrypted_sql_database_count,
            },
        )

    def _collect_network_profile(
        self,
        subscription_id: str,
        credential: Any,
    ) -> tuple[NetworkProfile, dict[str, str]]:
        """Collect Azure network posture from NSGs and private endpoint inventory."""
        if self._network_client_factory is None and self._credential_factory is None:
            cli_network_profile = self._collect_network_profile_from_cli(subscription_id)
            if cli_network_profile is not None:
                return cli_network_profile

        try:
            client = self._build_network_client(credential, subscription_id)
            network_security_groups = list(client.network_security_groups.list_all())
            private_endpoint_operations = client.private_endpoints
            if hasattr(private_endpoint_operations, "list_by_subscription"):
                private_endpoints = list(
                    private_endpoint_operations.list_by_subscription()
                )
            else:
                private_endpoints = list(private_endpoint_operations.list())
        except Exception:
            return (
                NetworkProfile(
                    internet_exposed_rdp_assets=0,
                    internet_exposed_ssh_assets=0,
                    permissive_nsg_rules=0,
                    public_storage_endpoints=0,
                    private_endpoints_required=0,
                    private_endpoints_configured=0,
                ),
                {
                    "collector_stage": "bootstrap",
                    "network_collection_mode": "default_no_network_sdk",
                },
            )

        rdp_exposure_targets: set[str] = set()
        ssh_exposure_targets: set[str] = set()
        permissive_rule_count = 0

        for nsg in network_security_groups:
            nsg_identifier = self._resource_identifier(nsg, fallback_prefix="nsg")
            for rule in getattr(nsg, "security_rules", []) or []:
                if not self._is_public_inbound_allow_rule(rule):
                    continue

                if self._rule_exposes_port(rule, target_port=3389):
                    rdp_exposure_targets.add(nsg_identifier)
                    permissive_rule_count += 1
                    continue

                if self._rule_exposes_port(rule, target_port=22):
                    ssh_exposure_targets.add(nsg_identifier)
                    permissive_rule_count += 1
                    continue

                if self._rule_is_broadly_permissive(rule):
                    permissive_rule_count += 1

        return (
            NetworkProfile(
                internet_exposed_rdp_assets=len(rdp_exposure_targets),
                internet_exposed_ssh_assets=len(ssh_exposure_targets),
                permissive_nsg_rules=permissive_rule_count,
                public_storage_endpoints=0,
                private_endpoints_required=0,
                private_endpoints_configured=len(private_endpoints),
            ),
            {
                "collector_stage": "network_enriched",
                "network_collection_mode": "azure_network_management",
            },
        )

    def _collect_network_profile_from_cli(
        self,
        subscription_id: str,
    ) -> tuple[NetworkProfile, dict[str, str]] | None:
        """Collect Azure network posture from Azure CLI inventory."""
        network_security_groups = self._run_cli_json(
            [
                "az",
                "network",
                "nsg",
                "list",
                "--subscription",
                subscription_id,
                "--output",
                "json",
            ]
        )
        private_endpoints = self._run_cli_json(
            [
                "az",
                "network",
                "private-endpoint",
                "list",
                "--subscription",
                subscription_id,
                "--output",
                "json",
            ]
        )

        if not isinstance(network_security_groups, list) and not isinstance(
            private_endpoints, list
        ):
            return None

        rdp_exposure_targets: set[str] = set()
        ssh_exposure_targets: set[str] = set()
        permissive_rule_count = 0

        for nsg in network_security_groups if isinstance(network_security_groups, list) else []:
            nsg_identifier = str(nsg.get("id") or nsg.get("name") or "nsg-unknown")
            for rule in nsg.get("securityRules", []) or []:
                if not self._is_public_inbound_allow_rule_dict(rule):
                    continue

                if self._rule_exposes_port_dict(rule, target_port=3389):
                    rdp_exposure_targets.add(nsg_identifier)
                    permissive_rule_count += 1
                    continue

                if self._rule_exposes_port_dict(rule, target_port=22):
                    ssh_exposure_targets.add(nsg_identifier)
                    permissive_rule_count += 1
                    continue

                if self._rule_is_broadly_permissive_dict(rule):
                    permissive_rule_count += 1

        return (
            NetworkProfile(
                internet_exposed_rdp_assets=len(rdp_exposure_targets),
                internet_exposed_ssh_assets=len(ssh_exposure_targets),
                permissive_nsg_rules=permissive_rule_count,
                public_storage_endpoints=0,
                private_endpoints_required=0,
                private_endpoints_configured=len(private_endpoints)
                if isinstance(private_endpoints, list)
                else 0,
            ),
            {
                "collector_stage": "network_enriched",
                "network_collection_mode": "azure_network_cli_inventory",
            },
        )

    def _collect_monitoring_profile(
        self,
        subscription_id: str,
        credential: Any,
    ) -> tuple[MonitoringProfile, dict[str, int | str]]:
        """Collect monitoring posture from Azure Monitor, Security, and workflow signals."""
        _ = subscription_id
        log_profiles = self._collect_log_profiles_from_cli()
        activity_log_alerts = self._collect_activity_log_alerts_from_cli()
        security_pricings = self._collect_security_pricings_from_cli()

        if self._resource_client_factory is None and self._credential_factory is None:
            workflows = self._collect_logic_app_workflows_from_cli(subscription_id)
        else:
            try:
                resource_client = self._build_resource_client(credential, subscription_id)
                workflows = [
                    resource
                    for resource in resource_client.resources.list()
                    if str(getattr(resource, "type", "")).lower()
                    == "microsoft.logic/workflows"
                ]
            except Exception:
                workflows = []

        activity_log_retention_days = 0
        if log_profiles:
            activity_log_retention_days = max(
                int(profile.get("retentionPolicy", {}).get("days", 0))
                for profile in log_profiles
            )

        critical_alert_coverage_ratio = min(len(activity_log_alerts) / 3.0, 1.0)

        relevant_pricing_names = {"VirtualMachines", "SqlServers", "CloudPosture"}
        relevant_pricings = [
            pricing
            for pricing in security_pricings
            if str(pricing.get("name")) in relevant_pricing_names
        ]
        defender_standard_plan_count = sum(
            1
            for pricing in relevant_pricings
            if str(pricing.get("pricingTier", "")).lower() == "standard"
        )
        defender_coverage_ratio = (
            round(defender_standard_plan_count / len(relevant_pricings), 4)
            if relevant_pricings
            else 0.0
        )

        return (
            MonitoringProfile(
                activity_log_retention_days=activity_log_retention_days,
                critical_alert_coverage_ratio=critical_alert_coverage_ratio,
                defender_coverage_ratio=defender_coverage_ratio,
                centralized_logging_enabled=bool(log_profiles),
                incident_response_runbooks_enabled=bool(workflows),
            ),
            {
                "monitoring_collection_mode": "azure_monitor_cli_inventory",
                "activity_log_alert_count": len(activity_log_alerts),
                "logic_app_workflow_count": len(workflows),
                "defender_standard_plan_count": defender_standard_plan_count,
            },
        )

    def _collect_governance_profile(
        self,
        subscription_id: str,
        credential: Any,
    ) -> tuple[GovernanceProfile, dict[str, int | str]]:
        """Collect governance posture from Azure resource inventory and CLI policy context."""
        if self._resource_client_factory is None and self._credential_factory is None:
            resources = self._collect_resources_from_cli(subscription_id)
        else:
            try:
                resource_client = self._build_resource_client(credential, subscription_id)
                resources = list(resource_client.resources.list())
            except Exception:
                resources = []

        total_resources = len(resources)
        tagged_resources = 0

        for resource in resources:
            tags = (
                resource.get("tags", {})
                if isinstance(resource, dict)
                else getattr(resource, "tags", None) or {}
            )
            if isinstance(tags, dict) and tags:
                tagged_resources += 1

        tagging_coverage_ratio = (
            round(tagged_resources / total_resources, 4) if total_resources else 0.0
        )
        policy_assignment_count = self._collect_policy_assignment_count_from_cli(
            subscription_id
        )
        policy_assignment_coverage_ratio = min(policy_assignment_count / 5.0, 1.0)
        if self._network_client_factory is None and self._credential_factory is None:
            orphaned_resource_count = self._collect_orphaned_resource_count_from_cli(
                subscription_id
            )
        else:
            orphaned_resource_count = self._collect_orphaned_resource_count(
                subscription_id=subscription_id,
                credential=credential,
            )

        return (
            GovernanceProfile(
                tagging_coverage_ratio=tagging_coverage_ratio,
                budget_alerts_enabled=False,
                policy_assignment_coverage_ratio=policy_assignment_coverage_ratio,
                orphaned_resource_count=orphaned_resource_count,
            ),
            {
                "governance_collection_mode": (
                    "azure_resource_inventory"
                    if total_resources or policy_assignment_count or orphaned_resource_count
                    else "default_no_governance_inventory"
                ),
                "governance_resource_count": total_resources,
                "policy_assignment_count": policy_assignment_count,
                "orphaned_resource_count": orphaned_resource_count,
            },
        )

    def _build_credential(self) -> Any:
        """Build an Azure credential, using dependency injection when provided."""
        if self._credential_factory is not None:
            return self._credential_factory()

        try:
            from azure.identity import DefaultAzureCredential
        except ImportError as exc:
            raise RuntimeError(
                "Azure collection requires the optional dependency 'azure-identity'. "
                "Install the Azure extras before using AzureCollector."
            ) from exc

        return DefaultAzureCredential()

    def _build_subscription_client(self, credential: Any) -> Any:
        """Build the Azure subscription client, using dependency injection when provided."""
        if self._subscription_client_factory is not None:
            return self._subscription_client_factory(credential)

        try:
            from azure.mgmt.resource import SubscriptionClient
        except ImportError as exc:
            raise RuntimeError(
                "Azure collection requires the optional dependency "
                "'azure-mgmt-resource'. Install the Azure extras before using "
                "AzureCollector."
            ) from exc

        return SubscriptionClient(credential)

    def _build_network_client(self, credential: Any, subscription_id: str) -> Any:
        """Build the Azure network management client, using dependency injection when provided."""
        if self._network_client_factory is not None:
            return self._network_client_factory(credential, subscription_id)

        try:
            from azure.mgmt.network import NetworkManagementClient
        except ImportError as exc:
            raise RuntimeError(
                "Azure network enrichment requires the optional dependency "
                "'azure-mgmt-network'. Install the Azure extras before using "
                "network-backed Azure collection."
            ) from exc

        return NetworkManagementClient(credential, subscription_id)

    def _build_resource_client(self, credential: Any, subscription_id: str) -> Any:
        """Build the Azure resource management client for governance inventory."""
        if self._resource_client_factory is not None:
            return self._resource_client_factory(credential, subscription_id)

        try:
            from azure.mgmt.resource import ResourceManagementClient
        except ImportError as exc:
            raise RuntimeError(
                "Azure governance enrichment requires the optional dependency "
                "'azure-mgmt-resource'. Install the Azure extras before using "
                "governance-backed Azure collection."
            ) from exc

        return ResourceManagementClient(credential, subscription_id)

    def _build_storage_client(self, credential: Any, subscription_id: str) -> Any:
        """Build the Azure storage management client for data posture collection."""
        if self._storage_client_factory is not None:
            return self._storage_client_factory(credential, subscription_id)

        try:
            from azure.mgmt.storage import StorageManagementClient
        except ImportError as exc:
            raise RuntimeError(
                "Azure data enrichment requires the optional dependency "
                "'azure-mgmt-storage'. Install the Azure extras before using "
                "storage-backed Azure collection."
            ) from exc

        return StorageManagementClient(credential, subscription_id)

    def _build_sql_client(self, credential: Any, subscription_id: str) -> Any:
        """Build the Azure SQL management client for SQL-backed data collection."""
        if self._sql_client_factory is not None:
            return self._sql_client_factory(credential, subscription_id)

        try:
            from azure.mgmt.sql import SqlManagementClient
        except ImportError as exc:
            raise RuntimeError(
                "Azure SQL enrichment requires the optional dependency "
                "'azure-mgmt-sql'. Install the Azure extras before using "
                "SQL-backed Azure collection."
            ) from exc

        return SqlManagementClient(credential, subscription_id)

    def _build_compute_client(self, credential: Any, subscription_id: str) -> Any:
        """Build the Azure compute management client for VM-backed posture collection."""
        if self._compute_client_factory is not None:
            return self._compute_client_factory(credential, subscription_id)

        try:
            from azure.mgmt.compute import ComputeManagementClient
        except ImportError as exc:
            raise RuntimeError(
                "Azure compute enrichment requires the optional dependency "
                "'azure-mgmt-compute'. Install the Azure extras before using "
                "compute-backed Azure collection."
            ) from exc

        return ComputeManagementClient(credential, subscription_id)

    def _collect_policy_assignment_count_from_cli(self, subscription_id: str) -> int:
        """Return the number of policy assignments visible at the subscription scope."""
        completed = self._run_cli_command(
            [
                "az",
                "policy",
                "assignment",
                "list",
                "--scope",
                f"/subscriptions/{subscription_id}",
                "--output",
                "json",
            ],
            timeout=20,
        )
        if completed is None:
            return 0

        try:
            assignments = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return 0

        if not isinstance(assignments, list):
            return 0

        return len(assignments)

    def _collect_log_profiles_from_cli(self) -> list[dict[str, Any]]:
        """Return Azure Monitor log profile records from the Azure CLI."""
        payload = self._run_cli_json(
            ["az", "monitor", "log-profiles", "list", "--output", "json"]
        )
        return payload if isinstance(payload, list) else []

    def _collect_activity_log_alerts_from_cli(self) -> list[dict[str, Any]]:
        """Return Azure activity log alerts from the Azure CLI."""
        payload = self._run_cli_json(
            ["az", "monitor", "activity-log", "alert", "list", "--output", "json"]
        )
        return payload if isinstance(payload, list) else []

    def _collect_security_pricings_from_cli(self) -> list[dict[str, Any]]:
        """Return Microsoft Defender pricing records from the Azure CLI."""
        payload = self._run_cli_json(
            ["az", "security", "pricing", "list", "--output", "json"]
        )
        if isinstance(payload, dict):
            value = payload.get("value")
            return value if isinstance(value, list) else []
        return payload if isinstance(payload, list) else []

    def _collect_security_assessments_from_cli(
        self,
        subscription_id: str,
    ) -> list[dict[str, Any]]:
        """Return compact Defender assessment records from the Azure CLI."""
        payload = self._run_cli_json(
            [
                "az",
                "security",
                "assessment",
                "list",
                "--subscription",
                subscription_id,
                "--output",
                "json",
            ],
            timeout=40,
        )
        if not isinstance(payload, list):
            return []

        compact_records: list[dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            status = item.get("status", {})
            if not isinstance(status, dict):
                status = {}
            resource_details = item.get("resourceDetails", {})
            if not isinstance(resource_details, dict):
                resource_details = {}
            compact_records.append(
                {
                    "assessment_id": item.get("name"),
                    "display_name": item.get("displayName"),
                    "status_code": status.get("code"),
                    "status_cause": status.get("cause"),
                    "status_description": status.get("description"),
                    "resource_type": resource_details.get("ResourceType"),
                    "resource_name": resource_details.get("ResourceName"),
                    "resource_group": item.get("resourceGroup"),
                }
            )
        return compact_records

    def _collect_role_assignments_from_cli(
        self,
        subscription_id: str,
    ) -> list[dict[str, Any]]:
        """Return role assignments visible at the subscription scope."""
        payload = self._run_cli_json(
            [
                "az",
                "role",
                "assignment",
                "list",
                "--scope",
                f"/subscriptions/{subscription_id}",
                "--output",
                "json",
            ]
        )
        return payload if isinstance(payload, list) else []

    def _collect_conditional_access_signal(self) -> tuple[bool, bool, int]:
        """Return whether admin conditional access is observable and appears present."""
        # Conditional Access is tenant-wide Entra posture rather than subscription-scoped
        # Azure inventory. In the current assessment mode we treat it as not observable
        # unless a future Entra-focused collector is added with stable tenant permissions.
        return (False, False, 0)

    def _collect_signed_in_user_directory_roles(self) -> tuple[int, bool, bool]:
        """Return visible directory-role context for the signed-in assessment identity."""
        completed = self._run_cli_command_allow_failure(
            [
                "az",
                "rest",
                "--method",
                "get",
                "--url",
                (
                    "https://graph.microsoft.com/v1.0/me/transitiveMemberOf/"
                    "microsoft.graph.directoryRole?$select=id,displayName"
                ),
            ],
            timeout=20,
        )
        if completed is None or completed.returncode != 0:
            return (0, False, False)

        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return (0, False, False)

        roles = payload.get("value", []) if isinstance(payload, dict) else []
        if not isinstance(roles, list):
            return (0, False, False)

        role_names = {
            str(role.get("displayName", "")).strip().lower()
            for role in roles
            if isinstance(role, dict)
        }
        privileged_directory_roles = {
            "global administrator",
            "privileged role administrator",
            "security administrator",
            "conditional access administrator",
        }
        is_directory_admin = any(name in privileged_directory_roles for name in role_names)
        return (len(roles), is_directory_admin, True)

    def _collect_directory_role_catalog_context(self) -> tuple[int, bool]:
        """Return whether tenant directory-role catalog visibility is available."""
        completed = self._run_cli_command_allow_failure(
            [
                "az",
                "rest",
                "--method",
                "get",
                "--url",
                "https://graph.microsoft.com/v1.0/directoryRoles?$select=id,displayName",
            ],
            timeout=20,
        )
        if completed is None or completed.returncode != 0:
            return (0, False)

        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            return (0, False)

        roles = payload.get("value", []) if isinstance(payload, dict) else []
        if not isinstance(roles, list):
            return (0, False)
        return (len(roles), True)

    def _collect_service_principal_posture(
        self,
        principal_ids: set[str],
    ) -> tuple[int, int]:
        """Return counts for stale and disabled service principals."""
        if not principal_ids:
            return (0, 0)

        expired_count = 0
        disabled_count = 0
        for principal_id in principal_ids:
            completed = self._run_cli_command_allow_failure(
                [
                    "az",
                    "rest",
                    "--method",
                    "get",
                    "--url",
                    (
                        "https://graph.microsoft.com/v1.0/servicePrincipals/"
                        f"{principal_id}?$select=id,displayName,accountEnabled,"
                        "passwordCredentials,keyCredentials"
                    ),
                ],
                timeout=20,
            )
            if completed is None or completed.returncode != 0:
                continue

            try:
                payload = json.loads(completed.stdout)
            except json.JSONDecodeError:
                continue

            if self._service_principal_has_expired_credentials(payload):
                expired_count += 1
            if payload.get("accountEnabled") is False:
                disabled_count += 1

        return (expired_count, disabled_count)

    def _collect_virtual_machines_from_cli(
        self,
        subscription_id: str,
    ) -> list[dict[str, Any]]:
        """Return Azure virtual machine records from the Azure CLI."""
        payload = self._run_cli_json(
            [
                "az",
                "vm",
                "list",
                "--subscription",
                subscription_id,
                "--show-details",
                "--output",
                "json",
            ]
        )
        return payload if isinstance(payload, list) else []

    def _collect_vm_extensions_from_cli(
        self,
        subscription_id: str,
        resource_group_name: str,
        vm_name: str,
    ) -> list[dict[str, Any]]:
        """Return VM extension records for a given virtual machine from the Azure CLI."""
        payload = self._run_cli_json(
            [
                "az",
                "vm",
                "extension",
                "list",
                "--subscription",
                subscription_id,
                "--resource-group",
                resource_group_name,
                "--vm-name",
                vm_name,
                "--output",
                "json",
            ]
        )
        return payload if isinstance(payload, list) else []

    def _collect_backup_protected_vm_count_from_cli(self, subscription_id: str) -> int:
        """Return the count of Azure IaaS VMs protected by Recovery Services backup."""
        recovery_vaults = self._run_cli_json(
            [
                "az",
                "resource",
                "list",
                "--subscription",
                subscription_id,
                "--resource-type",
                "Microsoft.RecoveryServices/vaults",
                "--output",
                "json",
            ]
        )
        if not isinstance(recovery_vaults, list):
            return 0

        protected_vm_ids: set[str] = set()
        for vault in recovery_vaults:
            vault_name = vault.get("name")
            resource_group_name = vault.get("resourceGroup")
            if not vault_name or not resource_group_name:
                continue

            items = self._run_cli_json(
                [
                    "az",
                    "backup",
                    "item",
                    "list",
                    "--subscription",
                    subscription_id,
                    "--resource-group",
                    str(resource_group_name),
                    "--vault-name",
                    str(vault_name),
                    "--backup-management-type",
                    "AzureIaasVM",
                    "--output",
                    "json",
                ]
            )
            if isinstance(items, dict):
                items = items.get("value", [])
            if not isinstance(items, list):
                continue

            for item in items:
                source_resource_id = (
                    item.get("properties", {}).get("sourceResourceId")
                    if isinstance(item, dict)
                    else None
                )
                if source_resource_id:
                    protected_vm_ids.add(str(source_resource_id).lower())

        return len(protected_vm_ids)

    def _collect_resources_from_cli(self, subscription_id: str) -> list[dict[str, Any]]:
        """Return generic Azure resource inventory from the Azure CLI."""
        payload = self._run_cli_json(
            [
                "az",
                "resource",
                "list",
                "--subscription",
                subscription_id,
                "--output",
                "json",
            ]
        )
        return payload if isinstance(payload, list) else []

    def _collect_logic_app_workflows_from_cli(
        self,
        subscription_id: str,
    ) -> list[dict[str, Any]]:
        """Return Logic App workflow resources from the Azure CLI."""
        payload = self._run_cli_json(
            [
                "az",
                "resource",
                "list",
                "--subscription",
                subscription_id,
                "--resource-type",
                "Microsoft.Logic/workflows",
                "--output",
                "json",
            ]
        )
        return payload if isinstance(payload, list) else []

    def _run_cli_json(self, command: list[str], timeout: int = 20) -> Any:
        """Execute an Azure CLI command and parse its JSON output."""
        completed = self._run_cli_command(command, timeout=timeout)
        if completed is None:
            return []

        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError:
            return []

    @staticmethod
    def _run_cli_command_allow_failure(
        command: list[str],
        timeout: int,
    ) -> subprocess.CompletedProcess[str] | None:
        """Execute a CLI command and return output even when the command fails."""
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
        except FileNotFoundError:
            return None

        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

            try:
                stdout, stderr = process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                stdout, stderr = process.communicate()

        return subprocess.CompletedProcess(
            args=command,
            returncode=process.returncode if process.returncode is not None else 1,
            stdout=stdout,
            stderr=stderr,
        )

    @staticmethod
    def _run_cli_command(
        command: list[str],
        timeout: int,
    ) -> subprocess.CompletedProcess[str] | None:
        """Execute a CLI command with process-group cleanup on timeout."""
        completed = AzureCollector._run_cli_command_allow_failure(command, timeout)
        if completed is None or completed.returncode != 0:
            return None
        return completed

    @staticmethod
    def _service_principal_has_expired_credentials(service_principal: dict[str, Any]) -> bool:
        """Return whether a service principal has any expired key or password credentials."""
        now = datetime.now(UTC)
        credential_groups = [
            service_principal.get("passwordCredentials", []),
            service_principal.get("keyCredentials", []),
        ]

        for credentials in credential_groups:
            if not isinstance(credentials, list):
                continue
            for credential in credentials:
                end_date_time = credential.get("endDateTime")
                if not end_date_time:
                    continue
                parsed = AzureCollector._parse_graph_datetime(end_date_time)
                if parsed is not None and parsed < now:
                    return True

        return False

    @staticmethod
    def _parse_graph_datetime(value: str) -> datetime | None:
        """Parse a Graph API timestamp into an aware datetime."""
        try:
            normalized = value.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

    def _collect_orphaned_resource_count(
        self,
        subscription_id: str,
        credential: Any,
    ) -> int:
        """Return a conservative orphaned-resource count from common unattached network assets."""
        try:
            client = self._build_network_client(credential, subscription_id)
        except Exception:
            return 0

        try:
            network_interfaces = list(client.network_interfaces.list_all())
        except Exception:
            network_interfaces = []

        try:
            public_ip_addresses = list(client.public_ip_addresses.list_all())
        except Exception:
            public_ip_addresses = []

        orphaned_network_interfaces = sum(
            1
            for nic in network_interfaces
            if getattr(nic, "virtual_machine", None) is None
        )
        orphaned_public_ips = sum(
            1
            for public_ip in public_ip_addresses
            if getattr(public_ip, "ip_configuration", None) is None
        )

        return orphaned_network_interfaces + orphaned_public_ips

    def _collect_orphaned_resource_count_from_cli(self, subscription_id: str) -> int:
        """Return a conservative orphaned-resource count from CLI network asset inventory."""
        network_interfaces = self._run_cli_json(
            [
                "az",
                "network",
                "nic",
                "list",
                "--subscription",
                subscription_id,
                "--output",
                "json",
            ]
        )
        public_ip_addresses = self._run_cli_json(
            [
                "az",
                "network",
                "public-ip",
                "list",
                "--subscription",
                subscription_id,
                "--output",
                "json",
            ]
        )
        if not isinstance(network_interfaces, list):
            network_interfaces = []
        if not isinstance(public_ip_addresses, list):
            public_ip_addresses = []

        orphaned_network_interfaces = sum(
            1
            for nic in network_interfaces
            if not nic.get("virtualMachine")
        )
        orphaned_public_ips = sum(
            1
            for public_ip in public_ip_addresses
            if not public_ip.get("ipConfiguration")
        )
        return orphaned_network_interfaces + orphaned_public_ips

    @staticmethod
    def _storage_account_is_public(account: Any) -> bool:
        """Return whether a storage account appears publicly reachable."""
        public_network_access = str(
            getattr(account, "public_network_access", "Enabled")
        ).lower()
        allow_blob_public_access = getattr(account, "allow_blob_public_access", None)

        return (
            public_network_access == "enabled"
            or allow_blob_public_access is True
        )

    @staticmethod
    def _storage_account_is_public_dict(account: dict[str, Any]) -> bool:
        """Return whether a CLI-derived storage account appears publicly reachable."""
        public_network_access = str(account.get("publicNetworkAccess", "Enabled")).lower()
        allow_blob_public_access = account.get("allowBlobPublicAccess")
        return public_network_access == "enabled" or allow_blob_public_access is True

    @staticmethod
    def _storage_account_is_encrypted(account: Any) -> bool:
        """Return whether a storage account appears encrypted at rest."""
        encryption = getattr(account, "encryption", None)
        if encryption is None:
            return False

        services = getattr(encryption, "services", None)
        if services is None:
            return False

        for service_name in ("blob", "file", "table", "queue"):
            service = getattr(services, service_name, None)
            if service is not None:
                return bool(getattr(service, "enabled", False))

        return False

    @staticmethod
    def _storage_account_is_encrypted_dict(account: dict[str, Any]) -> bool:
        """Return whether a CLI-derived storage account appears encrypted at rest."""
        encryption = account.get("encryption", {})
        if not isinstance(encryption, dict):
            return False

        services = encryption.get("services", {})
        if not isinstance(services, dict):
            return False

        for service_name in ("blob", "file", "table", "queue"):
            service = services.get(service_name, {})
            if isinstance(service, dict) and service.get("enabled") is True:
                return True

        return False

    def _get_blob_service_properties(self, client: Any, account: Any) -> Any | None:
        """Return blob service properties for a storage account when retrievable."""
        account_name = getattr(account, "name", None)
        resource_group_name = self._extract_resource_group_name(getattr(account, "id", None))
        if not account_name or not resource_group_name:
            return None

        try:
            return client.blob_services.get_service_properties(
                resource_group_name=resource_group_name,
                account_name=account_name,
            )
        except Exception:
            return None

    @staticmethod
    def _blob_retention_enabled(blob_properties: Any) -> bool:
        """Return whether blob delete retention or container retention is enabled."""
        delete_retention_policy = getattr(blob_properties, "delete_retention_policy", None)
        container_delete_retention_policy = getattr(
            blob_properties,
            "container_delete_retention_policy",
            None,
        )

        return bool(
            getattr(delete_retention_policy, "enabled", False)
            or getattr(container_delete_retention_policy, "enabled", False)
        )

    @staticmethod
    def _sql_server_is_public(server: Any) -> bool:
        """Return whether an Azure SQL server allows public network access."""
        public_network_access = str(
            getattr(server, "public_network_access", "Enabled")
        ).lower()
        return public_network_access == "enabled"

    @staticmethod
    def _sql_server_is_public_dict(server: dict[str, Any]) -> bool:
        """Return whether a CLI-derived Azure SQL server allows public network access."""
        public_network_access = str(server.get("publicNetworkAccess", "Enabled")).lower()
        return public_network_access == "enabled"

    def _sql_database_is_encrypted(
        self,
        sql_client: Any,
        resource_group_name: str,
        server_name: str,
        database_name: str,
    ) -> bool:
        """Return whether transparent data encryption is enabled for a SQL database."""
        try:
            tde = sql_client.transparent_data_encryptions.get(
                resource_group_name=resource_group_name,
                server_name=server_name,
                database_name=database_name,
                transparent_data_encryption_name="current",
            )
        except Exception:
            return False

        return str(getattr(tde, "status", "")).lower() == "enabled"

    def _sql_database_is_encrypted_from_cli(
        self,
        *,
        subscription_id: str,
        resource_group_name: str,
        server_name: str,
        database_name: str,
    ) -> bool:
        """Return whether transparent data encryption is enabled for a SQL database via CLI."""
        payload = self._run_cli_json(
            [
                "az",
                "sql",
                "db",
                "tde",
                "show",
                "--subscription",
                subscription_id,
                "--resource-group",
                resource_group_name,
                "--server",
                server_name,
                "--database",
                database_name,
                "--output",
                "json",
            ]
        )
        if not isinstance(payload, dict):
            return False
        return str(payload.get("status", "")).lower() == "enabled"

    def _collect_vm_extensions(
        self,
        client: Any,
        resource_group_name: str,
        vm_name: str,
    ) -> list[Any]:
        """Return installed VM extensions for a given Azure virtual machine."""
        try:
            return list(
                client.virtual_machine_extensions.list(
                    resource_group_name=resource_group_name,
                    vm_name=vm_name,
                )
            )
        except Exception:
            return []

    @staticmethod
    def _vm_has_endpoint_protection_signal(vm: Any, extensions: list[Any]) -> bool:
        """Return whether a VM shows an endpoint protection or telemetry signal."""
        recognized_publishers = {
            "microsoft.azure.security",
            "microsoft.monitor",
            "microsoft.enterprisecloud.monitoring",
        }
        recognized_extension_types = {
            "iisaantimalware",
            "mde.windows",
            "mde.linux",
            "azuremonitorwindowsagent",
            "azuremonitorlinuxagent",
            "omsagentforlinux",
            "microsoftmonitoragent",
        }

        for extension in extensions:
            publisher = str(AzureCollector._value(extension, "publisher", "")).lower()
            extension_type = str(AzureCollector._value(extension, "type", "")).lower()
            if (
                publisher in recognized_publishers
                or extension_type in recognized_extension_types
            ):
                return True

        diagnostics_profile = AzureCollector._value(vm, "diagnostics_profile")
        if diagnostics_profile is None:
            diagnostics_profile = AzureCollector._value(vm, "diagnosticsProfile")
        boot_diagnostics = AzureCollector._value(diagnostics_profile, "boot_diagnostics")
        if boot_diagnostics is None:
            boot_diagnostics = AzureCollector._value(diagnostics_profile, "bootDiagnostics")
        return bool(AzureCollector._value(boot_diagnostics, "enabled", False))

    @staticmethod
    def _vm_meets_hardening_proxy(vm: Any) -> bool:
        """Return whether a VM exposes baseline hardening signals."""
        security_profile = AzureCollector._value(vm, "security_profile")
        if security_profile is None:
            security_profile = AzureCollector._value(vm, "securityProfile")

        security_type = str(
            AzureCollector._value(security_profile, "security_type")
            or AzureCollector._value(security_profile, "securityType", "")
        ).lower()
        encryption_at_host = AzureCollector._value(
            security_profile,
            "encryption_at_host",
        )
        if encryption_at_host is None:
            encryption_at_host = AzureCollector._value(
                security_profile,
                "encryptionAtHost",
                False,
            )
        encryption_at_host = bool(encryption_at_host)

        diagnostics_profile = AzureCollector._value(vm, "diagnostics_profile")
        if diagnostics_profile is None:
            diagnostics_profile = AzureCollector._value(vm, "diagnosticsProfile")
        boot_diagnostics = AzureCollector._value(diagnostics_profile, "boot_diagnostics")
        if boot_diagnostics is None:
            boot_diagnostics = AzureCollector._value(diagnostics_profile, "bootDiagnostics")
        boot_diagnostics_enabled = bool(AzureCollector._value(boot_diagnostics, "enabled", False))

        return (
            security_type in {"trustedlaunch", "confidentialvm"}
            or encryption_at_host
            or boot_diagnostics_enabled
            or AzureCollector._vm_disables_password_authentication(vm)
        )

    @staticmethod
    def _vm_meets_patch_compliance_proxy(vm: Any) -> bool:
        """Return whether a VM appears aligned to an automated patching baseline."""
        os_profile = AzureCollector._value(vm, "os_profile")
        if os_profile is None:
            os_profile = AzureCollector._value(vm, "osProfile")

        windows_configuration = AzureCollector._value(
            os_profile,
            "windows_configuration",
        )
        if windows_configuration is None:
            windows_configuration = AzureCollector._value(os_profile, "windowsConfiguration")
        linux_configuration = AzureCollector._value(
            os_profile,
            "linux_configuration",
        )
        if linux_configuration is None:
            linux_configuration = AzureCollector._value(os_profile, "linuxConfiguration")

        patch_settings = AzureCollector._value(windows_configuration, "patch_settings")
        if patch_settings is None:
            patch_settings = AzureCollector._value(windows_configuration, "patchSettings")
        if patch_settings is None:
            patch_settings = AzureCollector._value(linux_configuration, "patch_settings")
        if patch_settings is None:
            patch_settings = AzureCollector._value(linux_configuration, "patchSettings")

        patch_mode = str(
            AzureCollector._value(patch_settings, "patch_mode")
            or AzureCollector._value(patch_settings, "patchMode", "")
        ).lower()
        assessment_mode = str(
            AzureCollector._value(patch_settings, "assessment_mode")
            or AzureCollector._value(patch_settings, "assessmentMode", "")
        ).lower()
        enable_automatic_updates = (
            AzureCollector._value(windows_configuration, "enable_automatic_updates")
            if windows_configuration is not None
            else None
        )
        if enable_automatic_updates is None:
            enable_automatic_updates = AzureCollector._value(
                windows_configuration,
                "enableAutomaticUpdates",
            )

        return (
            patch_mode in {"automaticbyplatform", "automaticbyos", "imagedefault"}
            or assessment_mode in {"automaticbyplatform", "imagedefault"}
            or enable_automatic_updates is True
        )

    @staticmethod
    def _vm_allows_password_authentication(vm: Any) -> bool:
        """Return whether a Linux VM appears to allow password-based authentication."""
        disable_password_authentication = AzureCollector._linux_password_authentication_setting(vm)
        return disable_password_authentication is False

    @staticmethod
    def _vm_disables_password_authentication(vm: Any) -> bool:
        """Return whether a Linux VM explicitly disables password-based authentication."""
        disable_password_authentication = AzureCollector._linux_password_authentication_setting(vm)
        return disable_password_authentication is True

    @staticmethod
    def _linux_password_authentication_setting(vm: Any) -> bool | None:
        """Return the Linux password-authentication setting when present on a VM."""
        os_profile = AzureCollector._value(vm, "os_profile")
        if os_profile is None:
            os_profile = AzureCollector._value(vm, "osProfile")

        linux_configuration = AzureCollector._value(os_profile, "linux_configuration")
        if linux_configuration is None:
            linux_configuration = AzureCollector._value(os_profile, "linuxConfiguration")
        if linux_configuration is None:
            return False

        disable_password_authentication = AzureCollector._value(
            linux_configuration,
            "disablePasswordAuthentication",
        )
        if disable_password_authentication is None:
            disable_password_authentication = AzureCollector._value(
                linux_configuration,
                "disable_password_authentication",
            )

        if isinstance(disable_password_authentication, bool):
            return disable_password_authentication

        return None

    @staticmethod
    def _value(resource: Any, attr: str, default: Any = None) -> Any:
        """Read an attribute from either an SDK object or a CLI-style mapping."""
        if resource is None:
            return default
        if isinstance(resource, dict):
            return resource.get(attr, default)
        return getattr(resource, attr, default)

    @staticmethod
    def _extract_resource_group_name(resource_id: str | None) -> str | None:
        """Extract the resource group name from a full Azure resource ID."""
        if not resource_id:
            return None

        parts = [part for part in str(resource_id).split("/") if part]
        for index, part in enumerate(parts):
            if part.lower() == "resourcegroups" and index + 1 < len(parts):
                return parts[index + 1]

        return None

    @staticmethod
    def _resource_identifier(resource: Any, fallback_prefix: str) -> str:
        """Return a stable identifier for Azure resources during posture collection."""
        resource_id = getattr(resource, "id", None)
        if resource_id:
            return str(resource_id)

        resource_name = getattr(resource, "name", None)
        if resource_name:
            return str(resource_name)

        return f"{fallback_prefix}-unknown"

    @staticmethod
    def _is_public_inbound_allow_rule(rule: Any) -> bool:
        """Return whether a security rule allows inbound traffic from public sources."""
        direction = str(getattr(rule, "direction", "")).lower()
        access = str(getattr(rule, "access", "")).lower()
        if direction != "inbound" or access != "allow":
            return False

        source_prefixes = AzureCollector._collect_address_prefixes(
            rule,
            singular_attr="source_address_prefix",
            plural_attr="source_address_prefixes",
        )
        if not source_prefixes:
            return False

        return any(
            prefix.lower() in {"*", "0.0.0.0/0", "internet", "any"}
            for prefix in source_prefixes
        )

    @staticmethod
    def _rule_exposes_port(rule: Any, target_port: int) -> bool:
        """Return whether a security rule exposes a target administrative port."""
        ports = AzureCollector._collect_port_ranges(rule)
        return any(
            AzureCollector._port_expression_matches_target(port, target_port)
            for port in ports
        )

    @staticmethod
    def _rule_is_broadly_permissive(rule: Any) -> bool:
        """Return whether a rule is permissive beyond the specific admin-port checks."""
        ports = AzureCollector._collect_port_ranges(rule)
        return any(port in {"*", "0-65535"} for port in ports)

    @staticmethod
    def _collect_port_ranges(rule: Any) -> list[str]:
        """Collect normalized destination port expressions from a security rule."""
        return AzureCollector._collect_scalar_or_list_values(
            rule,
            singular_attr="destination_port_range",
            plural_attr="destination_port_ranges",
        )

    @staticmethod
    def _collect_address_prefixes(rule: Any, singular_attr: str, plural_attr: str) -> list[str]:
        """Collect normalized address prefixes from a security rule."""
        return AzureCollector._collect_scalar_or_list_values(
            rule,
            singular_attr=singular_attr,
            plural_attr=plural_attr,
        )

    @staticmethod
    def _collect_scalar_or_list_values(
        resource: Any,
        singular_attr: str,
        plural_attr: str,
    ) -> list[str]:
        """Collect one-or-many scalar values from Azure SDK objects."""
        values: list[str] = []
        singular_value = getattr(resource, singular_attr, None)
        if singular_value not in (None, ""):
            values.append(str(singular_value))

        plural_value = getattr(resource, plural_attr, None) or []
        for item in plural_value:
            if item not in (None, ""):
                values.append(str(item))

        return values

    @staticmethod
    def _is_public_inbound_allow_rule_dict(rule: dict[str, Any]) -> bool:
        """Return whether a CLI-derived security rule allows inbound traffic from public sources."""
        direction = str(rule.get("direction", "")).lower()
        access = str(rule.get("access", "")).lower()
        if direction != "inbound" or access != "allow":
            return False

        prefixes = AzureCollector._normalize_scalar_or_list(
            rule.get("sourceAddressPrefix") or rule.get("sourceAddressPrefixes")
        )
        return any(
            prefix.lower() in {"*", "0.0.0.0/0", "internet", "any"}
            for prefix in prefixes
        )

    @staticmethod
    def _rule_exposes_port_dict(rule: dict[str, Any], target_port: int) -> bool:
        """Return whether a CLI-derived rule exposes a target administrative port."""
        ports = AzureCollector._normalize_scalar_or_list(
            rule.get("destinationPortRange") or rule.get("destinationPortRanges")
        )
        return any(
            AzureCollector._port_expression_matches_target(port, target_port)
            for port in ports
        )

    @staticmethod
    def _rule_is_broadly_permissive_dict(rule: dict[str, Any]) -> bool:
        """Return whether a CLI-derived rule is broadly permissive."""
        ports = AzureCollector._normalize_scalar_or_list(
            rule.get("destinationPortRange") or rule.get("destinationPortRanges")
        )
        return any(port in {"*", "0-65535"} for port in ports)

    @staticmethod
    def _normalize_scalar_or_list(value: Any) -> list[str]:
        """Normalize one-or-many scalar values from Azure CLI payloads."""
        if value in (None, ""):
            return []
        if isinstance(value, list):
            return [str(item) for item in value if item not in (None, "")]
        return [str(value)]

    @staticmethod
    def _port_expression_matches_target(port_expression: str, target_port: int) -> bool:
        """Return whether an Azure NSG port expression includes a target port."""
        normalized = port_expression.strip()
        if normalized == "*":
            return True

        if normalized.isdigit():
            return int(normalized) == target_port

        if "-" in normalized:
            start_text, _, end_text = normalized.partition("-")
            if start_text.isdigit() and end_text.isdigit():
                start_port = int(start_text)
                end_port = int(end_text)
                return start_port <= target_port <= end_port

        return False
