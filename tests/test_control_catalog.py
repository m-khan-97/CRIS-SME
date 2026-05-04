# Unit tests for the central CRIS-SME control catalog and shared finding builder behavior.
from cris_sme.controls.catalog import get_control_entry, load_control_catalog
from cris_sme.engine.compliance import load_compliance_mappings
from cris_sme.engine.provider_contracts import build_provider_evidence_contract_catalog


def test_control_catalog_contains_all_compliance_mapping_controls() -> None:
    catalog = load_control_catalog()
    compliance_mappings = load_compliance_mappings()

    assert set(compliance_mappings).issubset(set(catalog))


def test_control_catalog_entry_exposes_remediation_metadata() -> None:
    entry = get_control_entry("NET-001")

    assert entry.title == "Administrative services are exposed to the public internet"
    assert entry.remediation_summary
    assert entry.remediation_cost_tier.value in {"free", "low", "medium", "high"}
    assert "Cyber Essentials Firewalls" in entry.mapping


def test_provider_evidence_contract_catalog_reflects_active_and_planned_support() -> None:
    catalog = build_provider_evidence_contract_catalog()

    assert catalog.provider_count == 3
    assert catalog.control_count == 26
    assert catalog.contract_count == 78
    assert catalog.support_status_counts["active"] == 26
    assert catalog.support_status_counts["planned"] == 52

    azure_net = next(
        contract
        for contract in catalog.contracts
        if contract.provider == "azure" and contract.control_id == "NET-001"
    )
    aws_net = next(
        contract
        for contract in catalog.contracts
        if contract.provider == "aws" and contract.control_id == "NET-001"
    )

    assert azure_net.support_status == "active"
    assert azure_net.evidence_requirements
    assert azure_net.freshness_hours == 24
    assert "directly observed" in azure_net.sufficiency_policy
    assert aws_net.support_status == "planned"
    assert "collector evidence" in aws_net.activation_gate
