import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from cris_sme.controls.catalog import load_control_catalog
from cris_sme.controls.definitions import ControlDefinition, load_control_definitions
from cris_sme.controls.registry import ControlRegistry, load_control_registry
from cris_sme.controls.validation import validate_control_pack
from cris_sme.engine.assessment_runner import AssessmentRunner
from scripts.validate_control_metadata import validate


def definitions():
    return {key: value.model_copy(deep=True) for key, value in load_control_definitions().items()}


def test_complete_pack_schema_and_evaluators_match() -> None:
    assert validate(Path(__file__).resolve().parents[1]) == 36


def test_missing_definition_fails_parity() -> None:
    entries = definitions()
    del entries["CMP-005"]
    with pytest.raises(ValueError, match="CMP-005"):
        validate_control_pack(entries)


def test_extra_definition_fails_parity() -> None:
    entries = definitions()
    entries["CMP-999"] = entries["CMP-005"].model_copy(update={"control_id": "CMP-999"})
    with pytest.raises(ValueError, match="extra=.*CMP-999"):
        validate_control_pack(entries)


@pytest.mark.parametrize("field,value", [
    ("title", "Different control title"),
    ("provider_support", {"azure": "active", "aws": "active", "gcp": "planned"}),
])
def test_catalog_and_provider_drift_fails(field, value) -> None:
    entries = definitions()
    setattr(entries["IAM-001"], field, value)
    with pytest.raises(ValueError, match="differs from catalog/spec"):
        validate_control_pack(entries)


@pytest.mark.parametrize("relation", ["dependencies", "related_controls"])
def test_dangling_links_are_not_silently_ignored(relation) -> None:
    entries = definitions()
    setattr(entries["IAM-001"], relation, ["NOPE-999"])
    with pytest.raises(ValueError, match="invalid"):
        ControlRegistry(entries)


def test_dependency_cycles_fail() -> None:
    entries = definitions()
    entries["IAM-001"].dependencies = ["IAM-002"]
    entries["IAM-002"].dependencies = ["IAM-001"]
    with pytest.raises(ValueError, match="cycle"):
        ControlRegistry(entries)


def test_valid_dependency_expansion_is_stable() -> None:
    entries = definitions()
    entries["IAM-001"].dependencies = ["IAM-002"]
    entries["IAM-002"].dependencies = ["IAM-003"]
    selected = ControlRegistry(entries).filter(control_ids=["IAM-001"], include_dependencies=True)
    assert [entry.control_id for entry in selected] == ["IAM-001", "IAM-002", "IAM-003"]


@pytest.mark.parametrize("field", ["evidence_requirements", "assurance_claims"])
def test_blank_required_lists_fail(field) -> None:
    raw = definitions()["IAM-001"].model_dump()
    raw[field] = ["   "]
    with pytest.raises(ValidationError):
        ControlDefinition.model_validate(raw)


def test_blank_manual_instructions_fail() -> None:
    raw = definitions()["IAM-001"].model_dump()
    raw["remediation"]["manual_steps"] = [" "]
    with pytest.raises(ValidationError):
        ControlDefinition.model_validate(raw)


def test_normalized_provider_collisions_fail() -> None:
    raw = definitions()["IAM-001"].model_dump()
    raw["provider_support"] = {"azure": "active", " Azure ": "planned"}
    with pytest.raises(ValidationError):
        ControlDefinition.model_validate(raw)


def test_duplicate_mapping_fails() -> None:
    raw = definitions()["IAM-001"].model_dump()
    raw["compliance_mappings"].append(raw["compliance_mappings"][0])
    with pytest.raises(ValidationError):
        ControlDefinition.model_validate(raw)


@pytest.mark.parametrize("loader", [load_control_definitions, load_control_catalog])
def test_duplicate_control_ids_fail(loader, tmp_path) -> None:
    source = "control_metadata_v2.json" if loader == load_control_definitions else "control_catalog.json"
    raw = json.loads((Path(__file__).resolve().parents[1] / "data" / source).read_text())
    raw.append(raw[0])
    path = tmp_path / source
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="Duplicate"):
        loader(path)


def test_iomt_status_is_not_promoted_by_metadata_completion() -> None:
    controls = load_control_registry().filter(domains=["Healthcare IoT"])
    assert len(controls) == 10
    assert all(control.provider_support == {
        "azure": "research_preview", "aws": "research_preview", "gcp": "planned"
    } for control in controls)


def test_newly_registered_compute_control_can_be_selected() -> None:
    selected = AssessmentRunner(control_ids=["CMP-002"]).run()
    assert selected.control_selection.selected_control_ids == ["CMP-002"]
    assert selected.findings
    baseline = AssessmentRunner().run()
    expected = [finding.model_dump() for finding in baseline.findings if finding.control_id == "CMP-002"]
    assert [finding.model_dump() for finding in selected.findings] == expected
