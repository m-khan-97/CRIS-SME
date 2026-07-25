# Tests for Azure least-privilege setup artifacts.
import json
from pathlib import Path

from cris_sme.engine.provider_contracts import build_provider_evidence_contract_catalog


ROLE_DEFINITION_PATH = Path(
    "infra/azure/role-definitions/cris-sme-assessment-reader.json"
)
GRAPH_PERMISSION_PREFIX = "Microsoft.Graph/"


def test_azure_assessment_reader_role_is_valid_custom_role_shape() -> None:
    role = _load_role_definition()

    assert role["Name"] == "CRIS-SME Assessment Reader"
    assert role["IsCustom"] is True
    assert role["Actions"]
    assert role["NotActions"] == []
    assert role["DataActions"] == []
    assert role["NotDataActions"] == []
    assert role["AssignableScopes"] == ["/subscriptions/<subscription-id>"]


def test_azure_assessment_reader_role_covers_contract_arm_permissions() -> None:
    role_actions = set(_load_role_definition()["Actions"])
    required_arm_permissions = _azure_contract_arm_permissions(required_only=True)

    assert required_arm_permissions.issubset(role_actions)


def test_azure_assessment_reader_role_keeps_graph_permissions_out_of_rbac() -> None:
    role_actions = set(_load_role_definition()["Actions"])
    graph_permissions = _azure_contract_graph_permissions()

    assert graph_permissions == {
        "Microsoft.Graph/directoryRoles/read",
        "Microsoft.Graph/conditionalAccessPolicies/read",
        "Microsoft.Graph/accessReviews/read",
        "Microsoft.Graph/credentialUserRegistrationDetails/read",
        "Microsoft.Graph/roleEligibilityScheduleInstances/read",
    }
    assert all(
        not action.startswith(GRAPH_PERMISSION_PREFIX)
        for action in role_actions
    )


def test_azure_assessment_reader_role_includes_optional_budget_read() -> None:
    role_actions = set(_load_role_definition()["Actions"])
    optional_arm_permissions = _azure_contract_arm_permissions(required_only=False)

    assert "Microsoft.Consumption/budgets/read" in optional_arm_permissions
    assert "Microsoft.Consumption/budgets/read" in role_actions


def _load_role_definition() -> dict:
    return json.loads(ROLE_DEFINITION_PATH.read_text(encoding="utf-8"))


def _azure_contract_arm_permissions(*, required_only: bool) -> set[str]:
    permissions: set[str] = set()
    for contract in _azure_active_contracts():
        permissions.update(
            permission
            for permission in contract.permissions.required_permissions
            if not permission.startswith(GRAPH_PERMISSION_PREFIX)
        )
        if not required_only:
            permissions.update(
                permission
                for permission in contract.permissions.optional_permissions
                if not permission.startswith(GRAPH_PERMISSION_PREFIX)
            )
    return permissions


def _azure_contract_graph_permissions() -> set[str]:
    permissions: set[str] = set()
    for contract in _azure_active_contracts():
        permissions.update(
            permission
            for permission in contract.permissions.required_permissions
            if permission.startswith(GRAPH_PERMISSION_PREFIX)
        )
        permissions.update(
            permission
            for permission in contract.permissions.optional_permissions
            if permission.startswith(GRAPH_PERMISSION_PREFIX)
        )
    return permissions


def _azure_active_contracts() -> list:
    catalog = build_provider_evidence_contract_catalog()
    return [
        contract
        for contract in catalog.contracts
        if contract.provider == "azure"
        and contract.support_status in {"active", "supported", "research_preview"}
    ]
