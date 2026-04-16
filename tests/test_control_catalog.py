# Unit tests for the central CRIS-SME control catalog and shared finding builder behavior.
from cris_sme.controls.catalog import get_control_entry, load_control_catalog
from cris_sme.engine.compliance import load_compliance_mappings


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
