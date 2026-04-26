# Unit tests for the first-stage Azure-backed collector in CRIS-SME.
from __future__ import annotations

import subprocess
from types import SimpleNamespace
from unittest.mock import patch

from cris_sme.collectors.azure_collector import AzureCollector, AzureCollectorSettings


class FakeSubscriptionOperations:
    """Minimal Azure subscription operations stub for collector testing."""

    def __init__(self, subscriptions: list[SimpleNamespace]) -> None:
        self._subscriptions = subscriptions

    def list(self) -> list[SimpleNamespace]:
        return self._subscriptions


class FakeSubscriptionClient:
    """Minimal Azure subscription client stub for collector testing."""

    def __init__(self, subscriptions: list[SimpleNamespace]) -> None:
        self.subscriptions = FakeSubscriptionOperations(subscriptions)


class FakeListOperations:
    """Minimal list-based Azure operation group stub for collector testing."""

    def __init__(self, resources: list[SimpleNamespace]) -> None:
        self._resources = resources

    def list_all(self) -> list[SimpleNamespace]:
        return self._resources

    def list(self) -> list[SimpleNamespace]:
        return self._resources

    def list_by_subscription(self) -> list[SimpleNamespace]:
        return self._resources


class FakeNetworkClient:
    """Minimal Azure network client stub for collector testing."""

    def __init__(
        self,
        network_security_groups: list[SimpleNamespace],
        private_endpoints: list[SimpleNamespace],
        network_interfaces: list[SimpleNamespace] | None = None,
        public_ip_addresses: list[SimpleNamespace] | None = None,
    ) -> None:
        self.network_security_groups = FakeListOperations(network_security_groups)
        self.private_endpoints = FakeListOperations(private_endpoints)
        self.network_interfaces = FakeListOperations(network_interfaces or [])
        self.public_ip_addresses = FakeListOperations(public_ip_addresses or [])


class FakeResourcesClient:
    """Minimal Azure resources operation group stub for governance testing."""

    def __init__(self, resources: list[SimpleNamespace]) -> None:
        self._resources = resources

    def list(self) -> list[SimpleNamespace]:
        return self._resources


class FakeResourceManagementClient:
    """Minimal Azure resource client stub for governance collector testing."""

    def __init__(self, resources: list[SimpleNamespace]) -> None:
        self.resources = FakeResourcesClient(resources)


class FakeStorageAccountsClient:
    """Minimal Azure storage accounts operation group stub for data testing."""

    def __init__(self, storage_accounts: list[SimpleNamespace]) -> None:
        self._storage_accounts = storage_accounts

    def list(self) -> list[SimpleNamespace]:
        return self._storage_accounts


class FakeBlobServicesClient:
    """Minimal Azure blob services operation group stub for data testing."""

    def __init__(self, properties_by_account: dict[str, SimpleNamespace]) -> None:
        self._properties_by_account = properties_by_account

    def get_service_properties(
        self,
        resource_group_name: str,
        account_name: str,
    ) -> SimpleNamespace:
        _ = resource_group_name
        return self._properties_by_account[account_name]


class FakeStorageManagementClient:
    """Minimal Azure storage client stub for data collector testing."""

    def __init__(
        self,
        storage_accounts: list[SimpleNamespace],
        properties_by_account: dict[str, SimpleNamespace],
    ) -> None:
        self.storage_accounts = FakeStorageAccountsClient(storage_accounts)
        self.blob_services = FakeBlobServicesClient(properties_by_account)


class FakeSqlServersClient:
    """Minimal Azure SQL servers operation group stub for data testing."""

    def __init__(self, servers: list[SimpleNamespace]) -> None:
        self._servers = servers

    def list(self) -> list[SimpleNamespace]:
        return self._servers


class FakeSqlDatabasesClient:
    """Minimal Azure SQL databases operation group stub for data testing."""

    def __init__(self, databases_by_server: dict[str, list[SimpleNamespace]]) -> None:
        self._databases_by_server = databases_by_server

    def list_by_server(
        self,
        resource_group_name: str,
        server_name: str,
    ) -> list[SimpleNamespace]:
        _ = resource_group_name
        return self._databases_by_server.get(server_name, [])


class FakeSqlTdeClient:
    """Minimal Azure SQL transparent data encryption operation group stub."""

    def __init__(self, statuses: dict[tuple[str, str], str]) -> None:
        self._statuses = statuses

    def get(
        self,
        resource_group_name: str,
        server_name: str,
        database_name: str,
        transparent_data_encryption_name: str,
    ) -> SimpleNamespace:
        _ = resource_group_name
        _ = transparent_data_encryption_name
        return SimpleNamespace(status=self._statuses[(server_name, database_name)])


class FakeSqlManagementClient:
    """Minimal Azure SQL client stub for SQL-backed data testing."""

    def __init__(
        self,
        servers: list[SimpleNamespace],
        databases_by_server: dict[str, list[SimpleNamespace]],
        tde_statuses: dict[tuple[str, str], str],
    ) -> None:
        self.servers = FakeSqlServersClient(servers)
        self.databases = FakeSqlDatabasesClient(databases_by_server)
        self.transparent_data_encryptions = FakeSqlTdeClient(tde_statuses)


class FakeVirtualMachinesClient:
    """Minimal Azure VM operations stub for compute collector testing."""

    def __init__(self, virtual_machines: list[SimpleNamespace]) -> None:
        self._virtual_machines = virtual_machines

    def list_all(self) -> list[SimpleNamespace]:
        return self._virtual_machines


class FakeVirtualMachineExtensionsClient:
    """Minimal Azure VM extension operations stub for compute collector testing."""

    def __init__(
        self,
        extensions_by_vm: dict[tuple[str, str], list[SimpleNamespace]],
    ) -> None:
        self._extensions_by_vm = extensions_by_vm

    def list(
        self,
        resource_group_name: str,
        vm_name: str,
    ) -> list[SimpleNamespace]:
        return self._extensions_by_vm.get((resource_group_name, vm_name), [])


class FakeComputeManagementClient:
    """Minimal Azure compute client stub for compute collector testing."""

    def __init__(
        self,
        virtual_machines: list[SimpleNamespace],
        extensions_by_vm: dict[tuple[str, str], list[SimpleNamespace]] | None = None,
    ) -> None:
        self.virtual_machines = FakeVirtualMachinesClient(virtual_machines)
        self.virtual_machine_extensions = FakeVirtualMachineExtensionsClient(
            extensions_by_vm or {}
        )


def test_azure_collector_builds_profile_from_enabled_subscription() -> None:
    subscriptions = [
        SimpleNamespace(
            subscription_id="sub-123",
            display_name="CRIS Research Subscription",
            tenant_id="tenant-001",
            state="Enabled",
        )
    ]

    collector = AzureCollector(
        settings=AzureCollectorSettings(
            organization_name="CRIS SME Research",
            sector="Professional Services",
        ),
        credential_factory=lambda: object(),
        subscription_client_factory=lambda _credential: FakeSubscriptionClient(
            subscriptions
        ),
    )

    with patch("subprocess.Popen", side_effect=FileNotFoundError):
        profiles = collector.collect_profiles()

    assert len(profiles) == 1
    profile = profiles[0]
    assert profile.provider == "azure"
    assert profile.organization_name == "CRIS SME Research"
    assert profile.metadata["subscription_id"] == "sub-123"
    assert profile.metadata["collector_stage"] == "azure_live_enriched"
    assert profile.metadata["dataset_source_type"] == "live_real"
    assert profile.metadata["authorization_basis"] == "authorized_tenant_access"
    assert profile.metadata["dataset_use"] == "live_case_study"
    assert profile.iam.privileged_accounts == 0


def test_azure_collector_supports_lab_dataset_metadata_overrides() -> None:
    subscriptions = [
        SimpleNamespace(
            subscription_id="sub-lab-001",
            display_name="AzureGoat Lab Subscription",
            tenant_id="tenant-lab-001",
            state="Enabled",
        )
    ]

    collector = AzureCollector(
        settings=AzureCollectorSettings(
            organization_name="AzureGoat Lab",
            sector="Training Lab",
            dataset_source_type="vulnerable_lab",
            authorization_basis="intentionally_vulnerable_lab",
            dataset_use="control_stress_test",
        ),
        credential_factory=lambda: object(),
        subscription_client_factory=lambda _credential: FakeSubscriptionClient(
            subscriptions
        ),
    )

    profiles = collector.collect_profiles()

    assert len(profiles) == 1
    profile = profiles[0]
    assert profile.metadata["dataset_source_type"] == "vulnerable_lab"
    assert profile.metadata["authorization_basis"] == "intentionally_vulnerable_lab"
    assert profile.metadata["dataset_use"] == "control_stress_test"


def test_azure_collector_filters_non_enabled_subscriptions() -> None:
    subscriptions = [
        SimpleNamespace(
            subscription_id="sub-disabled",
            display_name="Disabled Subscription",
            tenant_id="tenant-001",
            state="Disabled",
        )
    ]

    collector = AzureCollector(
        credential_factory=lambda: object(),
        subscription_client_factory=lambda _credential: FakeSubscriptionClient(
            subscriptions
        ),
    )

    with patch("subprocess.Popen", side_effect=FileNotFoundError):
        try:
            collector.collect_profiles()
        except ValueError as exc:
            assert "No enabled Azure subscriptions" in str(exc)
        else:
            raise AssertionError(
                "Expected ValueError when no enabled subscriptions are returned"
            )


def test_azure_collector_filters_to_requested_subscription_id() -> None:
    subscriptions = [
        SimpleNamespace(
            subscription_id="sub-123",
            display_name="Primary Subscription",
            tenant_id="tenant-001",
            state="Enabled",
        ),
        SimpleNamespace(
            subscription_id="sub-456",
            display_name="Secondary Subscription",
            tenant_id="tenant-002",
            state="Enabled",
        ),
    ]

    collector = AzureCollector(
        settings=AzureCollectorSettings(subscription_id="sub-456"),
        credential_factory=lambda: object(),
        subscription_client_factory=lambda _credential: FakeSubscriptionClient(
            subscriptions
        ),
    )

    with patch("subprocess.Popen", side_effect=FileNotFoundError):
        profiles = collector.collect_profiles()

    assert len(profiles) == 1
    assert profiles[0].metadata["subscription_id"] == "sub-456"


def test_azure_collector_enriches_network_profile_from_nsg_inventory() -> None:
    subscriptions = [
        SimpleNamespace(
            subscription_id="sub-123",
            display_name="Primary Subscription",
            tenant_id="tenant-001",
            state="Enabled",
        )
    ]
    nsgs = [
        SimpleNamespace(
            id="/subscriptions/sub-123/resourceGroups/demo/providers/Microsoft.Network/networkSecurityGroups/nsg-1",
            security_rules=[
                SimpleNamespace(
                    direction="Inbound",
                    access="Allow",
                    source_address_prefix="*",
                    destination_port_range="3389",
                ),
                SimpleNamespace(
                    direction="Inbound",
                    access="Allow",
                    source_address_prefix="Internet",
                    destination_port_ranges=["22"],
                ),
                SimpleNamespace(
                    direction="Inbound",
                    access="Allow",
                    source_address_prefix="0.0.0.0/0",
                    destination_port_range="443",
                ),
            ],
        )
    ]
    private_endpoints = [
        SimpleNamespace(id="pe-1"),
        SimpleNamespace(id="pe-2"),
    ]

    collector = AzureCollector(
        credential_factory=lambda: object(),
        subscription_client_factory=lambda _credential: FakeSubscriptionClient(
            subscriptions
        ),
        network_client_factory=lambda _credential, _subscription_id: FakeNetworkClient(
            nsgs,
            private_endpoints,
        ),
    )

    profiles = collector.collect_profiles()

    assert len(profiles) == 1
    profile = profiles[0]
    assert profile.network.internet_exposed_rdp_assets == 1
    assert profile.network.internet_exposed_ssh_assets == 1
    assert profile.network.permissive_nsg_rules == 2
    assert profile.network.private_endpoints_configured == 2
    assert profile.metadata["collector_stage"] == "azure_live_enriched"
    assert profile.metadata["network_collection_mode"] == "azure_network_management"


def test_azure_collector_falls_back_to_azure_cli_subscription_context(monkeypatch) -> None:
    subscriptions = [
        SimpleNamespace(
            subscription_id="sub-123",
            display_name="SDK Subscription",
            tenant_id="tenant-001",
            state="Disabled",
        )
    ]

    class FakeCompletedProcess:
        def __init__(self, stdout: str) -> None:
            self.stdout = stdout

    def fake_run_cli_command(*_args, **_kwargs) -> FakeCompletedProcess:
        return FakeCompletedProcess(
            '[{"id":"cli-sub-001","name":"Azure CLI Subscription","tenantId":"tenant-cli","state":"Enabled"}]'
        )

    monkeypatch.setattr(
        AzureCollector,
        "_run_cli_command",
        staticmethod(fake_run_cli_command),
    )

    collector = AzureCollector(
        credential_factory=lambda: object(),
        subscription_client_factory=lambda _credential: FakeSubscriptionClient(
            subscriptions
        ),
    )

    profiles = collector.collect_profiles()

    assert len(profiles) == 1
    assert profiles[0].metadata["subscription_id"] == "cli-sub-001"
    assert profiles[0].metadata["subscription_state"] == "Enabled"


def test_azure_collector_enriches_iam_profile_from_role_assignments_and_graph(
    monkeypatch,
) -> None:
    subscriptions = [
        SimpleNamespace(
            subscription_id="sub-123",
            display_name="IAM Subscription",
            tenant_id="tenant-001",
            state="Enabled",
        )
    ]

    class FakeCompletedProcess:
        def __init__(
            self,
            stdout: str,
            returncode: int = 0,
            stderr: str = "",
        ) -> None:
            self.stdout = stdout
            self.returncode = returncode
            self.stderr = stderr

    def fake_run_cli_command_allow_failure(
        command: list[str],
        timeout: int,
    ) -> FakeCompletedProcess:
        _ = timeout
        if command[:4] == ["az", "account", "list", "--output"]:
            return FakeCompletedProcess("[]")
        if command[:4] == ["az", "role", "assignment", "list"]:
            return FakeCompletedProcess(
                (
                    '[{"principalId":"user-1","principalType":"User","roleDefinitionName":"Owner"},'
                    '{"principalId":"user-1","principalType":"User","roleDefinitionName":"Owner"},'
                    '{"principalId":"sp-1","principalType":"ServicePrincipal","roleDefinitionName":"User Access Administrator"}]'
                )
            )
        if command[:6] == [
            "az",
            "rest",
            "--method",
            "get",
            "--url",
            "https://graph.microsoft.com/v1.0/policies/conditionalAccessPolicies",
        ]:
            return FakeCompletedProcess(
                '{"error":{"code":"AccessDenied"}}',
                returncode=1,
                stderr="AccessDenied",
            )
        if command[:5] == [
            "az",
            "rest",
            "--method",
            "get",
            "--url",
        ] and "servicePrincipals/sp-1" in command[5]:
            return FakeCompletedProcess(
                (
                    '{"accountEnabled":true,"passwordCredentials":[{"endDateTime":"2024-01-01T00:00:00Z"}],'
                    '"keyCredentials":[]}'
                )
            )
        if command[:5] == [
            "az",
            "rest",
            "--method",
            "get",
            "--url",
        ] and "me/transitiveMemberOf" in command[5]:
            return FakeCompletedProcess(
                '{"value":[{"displayName":"Global Administrator"}]}'
            )
        if command[:5] == [
            "az",
            "rest",
            "--method",
            "get",
            "--url",
        ] and "directoryRoles?$select=id,displayName" in command[5]:
            return FakeCompletedProcess(
                '{"value":[{"displayName":"Global Administrator"},{"displayName":"Security Administrator"}]}'
            )
        if command[:4] == ["az", "monitor", "log-profiles", "list"]:
            return FakeCompletedProcess("[]")
        if command[:5] == ["az", "monitor", "activity-log", "alert", "list"]:
            return FakeCompletedProcess("[]")
        if command[:4] == ["az", "security", "pricing", "list"]:
            return FakeCompletedProcess('{"value":[]}')
        if command[:4] == ["az", "security", "assessment", "list"]:
            return FakeCompletedProcess("[]")
        if command[:3] == ["az", "resource", "list"]:
            return FakeCompletedProcess("[]")
        if command[:4] == ["az", "backup", "item", "list"]:
            return FakeCompletedProcess("[]")
        if command[:4] == ["az", "policy", "assignment", "list"]:
            return FakeCompletedProcess("[]")
        raise AssertionError(f"Unexpected CLI command: {command}")

    monkeypatch.setattr(
        AzureCollector,
        "_run_cli_command_allow_failure",
        staticmethod(fake_run_cli_command_allow_failure),
    )

    collector = AzureCollector(
        credential_factory=lambda: object(),
        subscription_client_factory=lambda _credential: FakeSubscriptionClient(
            subscriptions
        ),
    )

    profiles = collector.collect_profiles()

    assert len(profiles) == 1
    profile = profiles[0]
    assert profile.iam.privileged_accounts == 2
    assert profile.iam.overprivileged_accounts == 1
    assert profile.iam.stale_service_principals == 1
    assert profile.iam.disabled_service_principals == 0
    assert profile.iam.privileged_user_assignments == 2
    assert profile.iam.privileged_service_principal_assignments == 1
    assert profile.iam.signed_in_user_directory_roles == 1
    assert profile.iam.signed_in_user_is_directory_admin is True
    assert profile.iam.visible_directory_role_catalog_entries == 2
    assert profile.iam.directory_role_catalog_visible is True
    assert profile.iam.identity_observability == "broad"
    assert profile.iam.conditional_access_enforced_for_admins is True
    assert profile.metadata["iam_collection_mode"] == "azure_role_assignments_and_graph"
    assert profile.metadata["conditional_access_accessible"] is False
    assert profile.metadata["privileged_assignment_count"] == 3
    assert profile.metadata["privileged_principal_count"] == 2
    assert profile.metadata["privileged_user_assignment_count"] == 2
    assert profile.metadata["privileged_service_principal_assignment_count"] == 1
    assert profile.metadata["signed_in_user_directory_role_count"] == 1
    assert profile.metadata["signed_in_user_is_directory_admin"] is True
    assert profile.metadata["signed_in_user_directory_roles_visible"] is True
    assert profile.metadata["visible_directory_role_catalog_count"] == 2
    assert profile.metadata["directory_role_catalog_visible"] is True
    assert profile.metadata["identity_observability"] == "broad"


def test_azure_collector_enriches_governance_profile_from_resource_inventory(
    monkeypatch,
) -> None:
    subscriptions = [
        SimpleNamespace(
            subscription_id="sub-123",
            display_name="Governance Subscription",
            tenant_id="tenant-001",
            state="Enabled",
        )
    ]
    resources = [
        SimpleNamespace(tags={"owner": "team-a"}),
        SimpleNamespace(tags={"costCentre": "finops"}),
        SimpleNamespace(tags={}),
        SimpleNamespace(tags=None),
    ]
    network_interfaces = [
        SimpleNamespace(virtual_machine=None),
        SimpleNamespace(virtual_machine=SimpleNamespace(id="vm-1")),
    ]
    public_ip_addresses = [
        SimpleNamespace(ip_configuration=None),
        SimpleNamespace(ip_configuration=SimpleNamespace(id="cfg-1")),
    ]

    class FakeCompletedProcess:
        def __init__(self, stdout: str) -> None:
            self.stdout = stdout

    def fake_run_cli_command(command: list[str], *_args, **_kwargs) -> FakeCompletedProcess:
        if command[:3] == ["az", "account", "list"]:
            return FakeCompletedProcess(
                '[{"id":"sub-123","name":"Governance Subscription","tenantId":"tenant-001","state":"Enabled"}]'
            )
        if command[:4] == ["az", "role", "assignment", "list"]:
            return FakeCompletedProcess("[]")
        if command[:4] == ["az", "policy", "assignment", "list"]:
            return FakeCompletedProcess('[{"name":"baseline-1"},{"name":"baseline-2"}]')
        if command[:4] == ["az", "monitor", "log-profiles", "list"]:
            return FakeCompletedProcess("[]")
        if command[:5] == ["az", "monitor", "activity-log", "alert", "list"]:
            return FakeCompletedProcess("[]")
        if command[:4] == ["az", "security", "pricing", "list"]:
            return FakeCompletedProcess('{"value":[]}')
        if command[:4] == ["az", "security", "assessment", "list"]:
            return FakeCompletedProcess("[]")
        raise AssertionError(f"Unexpected CLI command: {command}")

    monkeypatch.setattr(
        AzureCollector,
        "_run_cli_command",
        staticmethod(fake_run_cli_command),
    )

    collector = AzureCollector(
        credential_factory=lambda: object(),
        subscription_client_factory=lambda _credential: FakeSubscriptionClient(
            subscriptions
        ),
        network_client_factory=lambda _credential, _subscription_id: FakeNetworkClient(
            [],
            [],
            network_interfaces=network_interfaces,
            public_ip_addresses=public_ip_addresses,
        ),
        resource_client_factory=lambda _credential, _subscription_id: FakeResourceManagementClient(
            resources
        ),
    )

    profiles = collector.collect_profiles()

    assert len(profiles) == 1
    profile = profiles[0]
    assert profile.governance.tagging_coverage_ratio == 0.5
    assert profile.governance.policy_assignment_coverage_ratio == 0.4
    assert profile.governance.orphaned_resource_count == 2
    assert profile.metadata["governance_collection_mode"] == "azure_resource_inventory"
    assert profile.metadata["governance_resource_count"] == 4
    assert profile.metadata["policy_assignment_count"] == 2


def test_azure_collector_enriches_monitoring_profile_from_cli_and_workflows(
    monkeypatch,
) -> None:
    subscriptions = [
        SimpleNamespace(
            subscription_id="sub-123",
            display_name="Monitoring Subscription",
            tenant_id="tenant-001",
            state="Enabled",
        )
    ]
    resources = [
        SimpleNamespace(type="Microsoft.Logic/workflows"),
        SimpleNamespace(type="Microsoft.Logic/workflows"),
    ]

    class FakeCompletedProcess:
        def __init__(self, stdout: str) -> None:
            self.stdout = stdout

    def fake_run_cli_command(command: list[str], *_args, **_kwargs) -> FakeCompletedProcess:
        if command[:3] == ["az", "account", "list"]:
            return FakeCompletedProcess(
                '[{"id":"sub-123","name":"Monitoring Subscription","tenantId":"tenant-001","state":"Enabled"}]'
            )
        if command[:4] == ["az", "role", "assignment", "list"]:
            return FakeCompletedProcess("[]")
        if command[:4] == ["az", "monitor", "log-profiles", "list"]:
            return FakeCompletedProcess(
                '[{"retentionPolicy":{"days":30}},{"retentionPolicy":{"days":90}}]'
            )
        if command[:5] == ["az", "monitor", "activity-log", "alert", "list"]:
            return FakeCompletedProcess('[{"name":"alert-1"},{"name":"alert-2"}]')
        if command[:4] == ["az", "security", "pricing", "list"]:
            return FakeCompletedProcess(
                '{"value":[{"name":"VirtualMachines","pricingTier":"Standard"},{"name":"SqlServers","pricingTier":"Free"},{"name":"CloudPosture","pricingTier":"Standard"}]}'
            )
        if command[:4] == ["az", "security", "assessment", "list"]:
            return FakeCompletedProcess("[]")
        if command[:4] == ["az", "policy", "assignment", "list"]:
            return FakeCompletedProcess("[]")
        raise AssertionError(f"Unexpected CLI command: {command}")

    monkeypatch.setattr(
        AzureCollector,
        "_run_cli_command",
        staticmethod(fake_run_cli_command),
    )

    collector = AzureCollector(
        credential_factory=lambda: object(),
        subscription_client_factory=lambda _credential: FakeSubscriptionClient(
            subscriptions
        ),
        resource_client_factory=lambda _credential, _subscription_id: FakeResourceManagementClient(
            resources
        ),
    )

    profiles = collector.collect_profiles()

    assert len(profiles) == 1
    profile = profiles[0]
    assert profile.monitoring.activity_log_retention_days == 90
    assert profile.monitoring.critical_alert_coverage_ratio == 2 / 3
    assert profile.monitoring.defender_coverage_ratio == 0.6667
    assert profile.monitoring.centralized_logging_enabled is True
    assert profile.monitoring.incident_response_runbooks_enabled is True
    assert profile.metadata["monitoring_collection_mode"] == "azure_monitor_cli_inventory"
    assert profile.metadata["activity_log_alert_count"] == 2
    assert profile.metadata["logic_app_workflow_count"] == 2


def test_azure_collector_collects_native_security_recommendations(
    monkeypatch,
) -> None:
    subscriptions = [
        SimpleNamespace(
            subscription_id="sub-123",
            display_name="Validation Subscription",
            tenant_id="tenant-001",
            state="Enabled",
        )
    ]

    class FakeCompletedProcess:
        def __init__(self, stdout: str) -> None:
            self.stdout = stdout

    def fake_run_cli_command(command: list[str], *_args, **_kwargs) -> FakeCompletedProcess:
        if command[:3] == ["az", "account", "list"]:
            return FakeCompletedProcess(
                '[{"id":"sub-123","name":"Validation Subscription","tenantId":"tenant-001","state":"Enabled"}]'
            )
        if command[:4] == ["az", "role", "assignment", "list"]:
            return FakeCompletedProcess("[]")
        if command[:4] == ["az", "monitor", "log-profiles", "list"]:
            return FakeCompletedProcess("[]")
        if command[:5] == ["az", "monitor", "activity-log", "alert", "list"]:
            return FakeCompletedProcess("[]")
        if command[:4] == ["az", "security", "pricing", "list"]:
            return FakeCompletedProcess('{"value":[]}')
        if command[:4] == ["az", "security", "assessment", "list"]:
            return FakeCompletedProcess(
                '[{"name":"net-open-001","displayName":"All network ports should be restricted on network security groups associated to your virtual machine","status":{"code":"Unhealthy","cause":"NetworkPortsAreOpenToAllSources","description":"Network ports are open to all sources."},"resourceDetails":{"ResourceType":"microsoft.compute/virtualmachines","ResourceName":"vm-01"},"resourceGroup":"rg-demo"}]'
            )
        if command[:4] == ["az", "policy", "assignment", "list"]:
            return FakeCompletedProcess("[]")
        raise AssertionError(f"Unexpected CLI command: {command}")

    monkeypatch.setattr(
        AzureCollector,
        "_run_cli_command",
        staticmethod(fake_run_cli_command),
    )

    collector = AzureCollector(
        credential_factory=lambda: object(),
        subscription_client_factory=lambda _credential: FakeSubscriptionClient(
            subscriptions
        ),
    )

    profiles = collector.collect_profiles()

    profile = profiles[0]
    assert profile.metadata["native_recommendation_collection_mode"] == "azure_security_assessment_inventory"
    assert profile.metadata["native_security_recommendation_count"] == 1
    assert profile.metadata["native_unhealthy_recommendation_count"] == 1
    assert profile.metadata["native_security_recommendations"][0]["resource_name"] == "vm-01"


def test_azure_collector_enriches_data_profile_from_storage_inventory() -> None:
    subscriptions = [
        SimpleNamespace(
            subscription_id="sub-123",
            display_name="Data Subscription",
            tenant_id="tenant-001",
            state="Enabled",
        )
    ]
    storage_accounts = [
        SimpleNamespace(
            id="/subscriptions/sub-123/resourceGroups/rg-a/providers/Microsoft.Storage/storageAccounts/storea",
            name="storea",
            public_network_access="Enabled",
            allow_blob_public_access=True,
            encryption=SimpleNamespace(
                services=SimpleNamespace(blob=SimpleNamespace(enabled=True))
            ),
        ),
        SimpleNamespace(
            id="/subscriptions/sub-123/resourceGroups/rg-b/providers/Microsoft.Storage/storageAccounts/storeb",
            name="storeb",
            public_network_access="Disabled",
            allow_blob_public_access=False,
            encryption=SimpleNamespace(
                services=SimpleNamespace(blob=SimpleNamespace(enabled=False))
            ),
        ),
    ]
    properties_by_account = {
        "storea": SimpleNamespace(
            delete_retention_policy=SimpleNamespace(enabled=True),
            container_delete_retention_policy=SimpleNamespace(enabled=False),
        ),
        "storeb": SimpleNamespace(
            delete_retention_policy=SimpleNamespace(enabled=False),
            container_delete_retention_policy=SimpleNamespace(enabled=False),
        ),
    }

    collector = AzureCollector(
        credential_factory=lambda: object(),
        subscription_client_factory=lambda _credential: FakeSubscriptionClient(
            subscriptions
        ),
        storage_client_factory=lambda _credential, _subscription_id: FakeStorageManagementClient(
            storage_accounts,
            properties_by_account,
        ),
    )

    profiles = collector.collect_profiles()

    assert len(profiles) == 1
    profile = profiles[0]
    assert profile.data.public_storage_assets == 1
    assert profile.data.unencrypted_data_stores == 1
    assert profile.data.backup_coverage_ratio == 0.5
    assert profile.data.retention_policy_coverage_ratio == 0.5
    assert profile.metadata["data_collection_mode"] == "azure_storage_inventory"
    assert profile.metadata["storage_account_count"] == 2


def test_azure_collector_enriches_data_profile_from_sql_inventory() -> None:
    subscriptions = [
        SimpleNamespace(
            subscription_id="sub-123",
            display_name="SQL Subscription",
            tenant_id="tenant-001",
            state="Enabled",
        )
    ]
    sql_servers = [
        SimpleNamespace(
            id="/subscriptions/sub-123/resourceGroups/sql-rg/providers/Microsoft.Sql/servers/server-a",
            name="server-a",
            public_network_access="Enabled",
        ),
        SimpleNamespace(
            id="/subscriptions/sub-123/resourceGroups/sql-rg/providers/Microsoft.Sql/servers/server-b",
            name="server-b",
            public_network_access="Disabled",
        ),
    ]
    databases_by_server = {
        "server-a": [
            SimpleNamespace(name="master"),
            SimpleNamespace(name="appdb1"),
        ],
        "server-b": [
            SimpleNamespace(name="appdb2"),
        ],
    }
    tde_statuses = {
        ("server-a", "appdb1"): "Enabled",
        ("server-b", "appdb2"): "Disabled",
    }

    collector = AzureCollector(
        credential_factory=lambda: object(),
        subscription_client_factory=lambda _credential: FakeSubscriptionClient(
            subscriptions
        ),
        sql_client_factory=lambda _credential, _subscription_id: FakeSqlManagementClient(
            sql_servers,
            databases_by_server,
            tde_statuses,
        ),
    )

    profiles = collector.collect_profiles()

    assert len(profiles) == 1
    profile = profiles[0]
    assert profile.data.unencrypted_data_stores == 1
    assert profile.data.backup_coverage_ratio == 0.5
    assert profile.data.retention_policy_coverage_ratio == 0.5
    assert profile.metadata["data_collection_mode"] == "azure_sql_inventory"
    assert profile.metadata["sql_server_count"] == 2
    assert profile.metadata["sql_database_count"] == 2
    assert profile.metadata["public_sql_server_count"] == 1
    assert profile.metadata["unencrypted_sql_database_count"] == 1


def test_azure_collector_enriches_compute_profile_from_vm_inventory(
    monkeypatch,
) -> None:
    class FakeCompletedProcess:
        def __init__(self, stdout: str) -> None:
            self.stdout = stdout

    def fake_run_cli_command(command: list[str], *_args, **_kwargs) -> FakeCompletedProcess:
        if command[:3] == ["az", "resource", "list"]:
            return FakeCompletedProcess(
                '[{"name":"vault-a","resourceGroup":"rg-backup"}]'
            )
        if command[:4] == ["az", "backup", "item", "list"]:
            return FakeCompletedProcess(
                '{"value":[{"properties":{"sourceResourceId":"/subscriptions/sub-123/resourceGroups/rg-a/providers/Microsoft.Compute/virtualMachines/vm-a"}}]}'
            )
        if command[:4] == ["az", "monitor", "log-profiles", "list"]:
            return FakeCompletedProcess("[]")
        if command[:5] == ["az", "monitor", "activity-log", "alert", "list"]:
            return FakeCompletedProcess("[]")
        if command[:4] == ["az", "security", "pricing", "list"]:
            return FakeCompletedProcess('{"value":[]}')
        if command[:4] == ["az", "policy", "assignment", "list"]:
            return FakeCompletedProcess("[]")
        raise AssertionError(f"Unexpected CLI command: {command}")

    monkeypatch.setattr(
        AzureCollector,
        "_run_cli_command",
        staticmethod(fake_run_cli_command),
    )


def test_azure_collector_run_cli_command_returns_none_on_timeout(monkeypatch) -> None:
    class FakeProcess:
        pid = 12345
        returncode = None
        call_count = 0

        def communicate(self, timeout: int | None = None) -> tuple[str, str]:
            self.call_count += 1
            if self.call_count <= 2:
                raise subprocess.TimeoutExpired(cmd=["az"], timeout=timeout or 0)
            self.returncode = -9
            return ("", "")

    monkeypatch.setattr(
        "cris_sme.collectors.azure_collector.subprocess.Popen",
        lambda *_args, **_kwargs: FakeProcess(),
    )
    monkeypatch.setattr(
        "cris_sme.collectors.azure_collector.os.killpg",
        lambda *_args, **_kwargs: None,
    )

    completed = AzureCollector._run_cli_command(["az", "vm", "list"], timeout=1)

    assert completed is None
