# Tests for OCSF-aligned finding export.
import json

from cris_sme.reporting import build_ocsf_findings, write_ocsf_findings
from tests.test_sarif_export import _build_report


def test_build_ocsf_findings_maps_prioritized_risks_to_detection_events() -> None:
    report = _build_report()

    events = build_ocsf_findings(report)
    first_event = events[0]
    first_risk = report["prioritized_risks"][0]

    assert len(events) == len(report["prioritized_risks"])
    assert first_event["category_name"] == "Findings"
    assert first_event["category_uid"] == 2
    assert first_event["class_name"] == "Detection Finding"
    assert first_event["class_uid"] == 2004
    assert first_event["metadata"]["version"] == "1.1.0"
    assert first_event["metadata"]["event_code"] == "finding"
    assert first_event["finding_info"]["uid"] == first_risk["finding_id"]
    assert first_event["finding_info"]["product_uid"] == first_risk["control_id"]
    assert first_event["severity_id"] >= 1
    assert first_event["cloud"]["provider"] == first_risk["provider"]


def test_ocsf_findings_preserve_cris_resource_evidence_and_remediation_context() -> None:
    report = _build_report()

    event = build_ocsf_findings(report)[0]
    risk = report["prioritized_risks"][0]

    assert event["resources"]
    assert event["evidences"]
    assert event["resources"][0]["uid"] == risk["asset_ids"][0]
    assert event["evidences"][0]["uid"] == risk["evidence_ids"][0]
    assert event["remediation"]["desc"] == risk["remediation_summary"]
    assert event["unmapped"]["cris_sme"]["score"] == risk["score"]
    assert event["unmapped"]["cris_sme"]["asset_ids"] == risk["asset_ids"]
    assert event["unmapped"]["cris_sme"]["evidence_ids"] == risk["evidence_ids"]


def test_write_ocsf_findings_persists_json_array(tmp_path) -> None:
    report = _build_report()

    output_path = write_ocsf_findings(
        report,
        tmp_path / "cris_sme_findings_ocsf.json",
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert payload
    assert payload[0]["metadata"]["product"]["name"] == "CRIS-SME"
