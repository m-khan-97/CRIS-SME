# Tests for SARIF interoperability export.
import json

from cris_sme.controls.compute_controls import evaluate_compute_controls
from cris_sme.controls.data_controls import evaluate_data_controls
from cris_sme.controls.governance_controls import evaluate_governance_controls
from cris_sme.controls.iam_controls import evaluate_iam_controls
from cris_sme.controls.monitoring_controls import evaluate_monitoring_controls
from cris_sme.controls.network_controls import evaluate_network_controls
from cris_sme.engine.compliance import assess_compliance_mappings, load_compliance_mappings
from cris_sme.engine.scoring import score_findings
from cris_sme.reporting import (
    build_json_report,
    build_sarif_report,
    write_sarif_report,
)
from tests.test_reporting import make_profile


def test_build_sarif_report_maps_prioritized_risks_to_results() -> None:
    report = _build_report()

    sarif = build_sarif_report(report)
    run = sarif["runs"][0]
    rules = run["tool"]["driver"]["rules"]
    results = run["results"]

    assert sarif["version"] == "2.1.0"
    assert sarif["$schema"].endswith("sarif-2.1.0.json")
    assert run["tool"]["driver"]["name"] == "CRIS-SME"
    assert run["properties"]["overall_risk_score"] == report["overall_risk_score"]
    assert (
        run["properties"]["resource_context_model"]
        == "cris_sme_resource_evidence_context_v1"
    )
    assert len(results) == len(report["prioritized_risks"])
    assert {rule["id"] for rule in rules} == {
        risk["control_id"] for risk in report["prioritized_risks"]
    }

    first_result = results[0]
    first_risk = report["prioritized_risks"][0]
    assert first_result["ruleId"] == first_risk["control_id"]
    assert first_result["level"] in {"error", "warning", "note"}
    assert (
        first_result["partialFingerprints"]["crisSmeFindingId"]
        == first_risk["finding_id"]
    )
    first_uri = first_result["locations"][0]["physicalLocation"][
        "artifactLocation"
    ]["uri"]
    assert first_uri.startswith("cris-sme://")
    assert first_result["properties"]["asset_ids"] == first_risk["asset_ids"]
    assert first_result["properties"]["evidence_ids"] == first_risk["evidence_ids"]
    assert first_result["relatedLocations"]


def test_write_sarif_report_persists_valid_json(tmp_path) -> None:
    report = _build_report()

    sarif_path = write_sarif_report(report, tmp_path / "cris_sme_report.sarif")

    payload = json.loads(sarif_path.read_text(encoding="utf-8"))
    assert payload["version"] == "2.1.0"
    assert payload["runs"][0]["results"]


def _build_report() -> dict:
    profiles = [make_profile()]
    findings = [
        *evaluate_iam_controls(profiles),
        *evaluate_network_controls(profiles),
        *evaluate_data_controls(profiles),
        *evaluate_monitoring_controls(profiles),
        *evaluate_compute_controls(profiles),
        *evaluate_governance_controls(profiles),
    ]
    scoring_result = score_findings(findings)
    compliance_result = assess_compliance_mappings(findings, load_compliance_mappings())
    report = build_json_report(
        profiles=profiles,
        findings=findings,
        scoring_result=scoring_result,
        compliance_result=compliance_result,
    )
    report["generated_at"] = "2026-06-15T00:00:00Z"
    report["collector_mode"] = "mock"
    return report
