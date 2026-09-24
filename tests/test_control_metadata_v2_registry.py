# Unit tests for CRIS-SME control metadata v2 loading and registry filtering.
import json

from cris_sme.controls.catalog import get_control_entry, load_control_catalog
from cris_sme.controls.definitions import (
    DEFAULT_CONTROL_METADATA_V2_PATH,
    get_control_definition,
    load_control_definitions,
)
from cris_sme.controls.registry import load_control_registry
from cris_sme.models.finding import FindingSeverity
from cris_sme.policies import get_control_spec


def test_control_metadata_v2_loads_all_catalog_controls() -> None:
    definitions = load_control_definitions()

    assert set(definitions) == set(load_control_catalog())
    assert len(definitions) == 36

    iam = get_control_definition("IAM-001")
    assert iam.severity == FindingSeverity.CRITICAL
    assert iam.provider_support["azure"] == "active"
    assert iam.supports_provider("aws")
    assert iam.supports_provider("azure", statuses={"active"})
    assert not iam.supports_provider("azure", statuses={"planned"})
    assert "Cyber Essentials" in iam.frameworks
    assert iam.remediation.code[0].kind == "azure_cli"


def test_control_metadata_v2_stays_aligned_with_existing_catalog_and_specs() -> None:
    definitions = load_control_definitions()

    for control_id, definition in definitions.items():
        catalog_entry = get_control_entry(control_id)
        control_spec = get_control_spec(control_id)

        assert definition.title == catalog_entry.title
        assert definition.domain == catalog_entry.category
        assert definition.remediation.summary == catalog_entry.remediation_summary
        assert definition.remediation.cost_tier == catalog_entry.remediation_cost_tier
        assert definition.provider_support == control_spec.provider_support
        assert definition.evidence_requirements
        assert definition.freshness_hours > 0
        assert definition.assurance_claims


def test_control_metadata_v2_schema_file_matches_full_catalog() -> None:
    schema = json.loads(
        DEFAULT_CONTROL_METADATA_V2_PATH.with_suffix(".schema.json").read_text(
            encoding="utf-8"
        )
    )
    raw_metadata = json.loads(
        DEFAULT_CONTROL_METADATA_V2_PATH.read_text(encoding="utf-8")
    )

    assert schema["title"] == "CRIS-SME Control Metadata v2"
    assert schema["type"] == "array"
    assert {item["control_id"] for item in raw_metadata} == set(load_control_catalog())


def test_control_registry_filters_by_provider_framework_and_domain() -> None:
    registry = load_control_registry()

    controls = registry.filter(
        providers=["azure"],
        provider_statuses=["active"],
        frameworks=["Cyber Essentials"],
        domains=["Network"],
    )

    assert [control.control_id for control in controls] == ["NET-001", "NET-002"]


def test_control_registry_filters_by_resource_evidence_and_claims() -> None:
    registry = load_control_registry()

    assert [
        control.control_id
        for control in registry.filter(resource_groups=["data-exposure"])
    ] == ["DATA-001"]
    assert [
        control.control_id
        for control in registry.filter(
            evidence_requirements=["activity log retention setting"]
        )
    ] == ["MON-001"]
    assert [
        control.control_id
        for control in registry.filter(
            assurance_claims=["assets-have-accountable-owners"]
        )
    ] == ["GOV-001"]


def test_control_registry_filters_by_control_id_and_research_preview_provider() -> None:
    registry = load_control_registry()

    controls = registry.filter(
        control_ids=["IAM-001", "NET-001"],
        providers=["aws"],
        provider_statuses=["research_preview"],
    )

    assert [control.control_id for control in controls] == ["IAM-001", "NET-001"]
