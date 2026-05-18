# Tests for the CRIS-IoMT healthcare control mapping artifact.
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAPPING_PATH = ROOT / "data" / "iomt_healthcare_control_mapping.json"
RESEARCH_DIR = ROOT / "docs" / "research" / "cris-iomt"

VALID_EVIDENCE_CLASSES = {
    "direct_cloud",
    "inferred_cloud",
    "unavailable_cloud",
    "device_required",
    "clinical_operational_required",
    "not_applicable",
}


def test_iomt_mapping_has_research_grade_control_set() -> None:
    mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
    controls = mapping["controls"]

    assert mapping["certification_boundary"]
    assert len(controls) == 10
    assert {control["control_id"] for control in controls} == {
        f"IOT-{index:03d}" for index in range(1, 11)
    }

    for control in controls:
        assert control["evidence_class"] in VALID_EVIDENCE_CLASSES
        assert control["title"]
        assert control["azure_evidence"]
        assert control["manual_or_external_evidence"]
        assert control["nhs_dspt_themes"]
        assert control["ncsc_caf_objectives"]


def test_iomt_research_pack_contains_core_documents() -> None:
    expected = {
        "README.md",
        "paper-plan.md",
        "control-model.md",
        "evaluation-protocol.md",
        "collaboration-brief.md",
    }

    assert expected <= {path.name for path in RESEARCH_DIR.iterdir()}

    paper_plan = (RESEARCH_DIR / "paper-plan.md").read_text(encoding="utf-8")
    assert "patient data" in paper_plan
    assert "NHS DSPT" in paper_plan
    assert "NCSC CAF" in paper_plan
    assert "CRIS-IoMT" in paper_plan

