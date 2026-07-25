# Tests for AWS least-privilege setup artifacts.
import json
from pathlib import Path

from cris_sme.engine.provider_contracts import build_provider_evidence_contract_catalog


POLICY_PATH = Path("infra/aws/iam-policies/cris-sme-assessment-reader.json")


def test_aws_assessment_reader_policy_is_valid_iam_policy_shape() -> None:
    policy = _load_policy_document()

    assert policy["Version"] == "2012-10-17"
    assert policy["Statement"]
    for statement in policy["Statement"]:
        assert statement["Effect"] == "Allow"
        assert statement["Action"]
        assert statement["Resource"] == "*"


def test_aws_assessment_reader_policy_covers_contract_required_permissions() -> None:
    policy_actions = _policy_actions()
    required_permissions = _aws_contract_permissions(required_only=True)

    assert required_permissions.issubset(policy_actions)


def test_aws_assessment_reader_policy_includes_optional_budget_and_org_reads() -> None:
    policy_actions = _policy_actions()
    optional_permissions = _aws_contract_permissions(required_only=False) - _aws_contract_permissions(
        required_only=True
    )

    assert "budgets:ViewBudget" in optional_permissions
    assert "organizations:ListPolicies" in optional_permissions
    assert optional_permissions.issubset(policy_actions)


def _load_policy_document() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _policy_actions() -> set[str]:
    policy = _load_policy_document()
    actions: set[str] = set()
    for statement in policy["Statement"]:
        actions.update(statement["Action"])
    return actions


def _aws_contract_permissions(*, required_only: bool) -> set[str]:
    permissions: set[str] = set()
    for contract in _aws_research_preview_contracts():
        permissions.update(contract.permissions.required_permissions)
        if not required_only:
            permissions.update(contract.permissions.optional_permissions)
    return permissions


def _aws_research_preview_contracts() -> list:
    catalog = build_provider_evidence_contract_catalog()
    return [
        contract
        for contract in catalog.contracts
        if contract.provider == "aws"
        and contract.support_status in {"active", "supported", "research_preview"}
    ]
