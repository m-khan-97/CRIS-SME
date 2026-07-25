# Tests for SME/MSP CSV export bundle.
import csv

from cris_sme.reporting import write_csv_export_bundle
from tests.test_sarif_export import _build_report


def test_write_csv_export_bundle_persists_spreadsheet_outputs(tmp_path) -> None:
    report = _build_report()

    paths = write_csv_export_bundle(report, tmp_path)

    assert set(paths) == {
        "findings_csv",
        "assets_csv",
        "evidence_csv",
        "actions_csv",
    }
    assert all(path.exists() for path in paths.values())

    findings = _read_csv(paths["findings_csv"])
    assets = _read_csv(paths["assets_csv"])
    evidence = _read_csv(paths["evidence_csv"])
    actions = _read_csv(paths["actions_csv"])

    assert len(findings) == len(report["prioritized_risks"])
    assert len(assets) == len(report["resource_context"]["assets"])
    assert len(evidence) == len(report["resource_context"]["evidence_records"])
    assert actions


def test_findings_csv_includes_traceability_and_remediation_columns(tmp_path) -> None:
    report = _build_report()

    paths = write_csv_export_bundle(report, tmp_path)
    first_row = _read_csv(paths["findings_csv"])[0]
    first_risk = report["prioritized_risks"][0]

    assert first_row["finding_id"] == first_risk["finding_id"]
    assert first_row["control_id"] == first_risk["control_id"]
    assert first_row["asset_ids"]
    assert first_row["evidence_ids"]
    assert first_row["evidence_sufficiency"]
    assert first_row["remediation_summary"] == first_risk["remediation_summary"]


def test_actions_csv_flattens_30_day_plan_phases(tmp_path) -> None:
    report = _build_report()

    paths = write_csv_export_bundle(report, tmp_path)
    actions = _read_csv(paths["actions_csv"])

    assert {row["phase_id"] for row in actions}.issubset(
        {"days_1_7", "days_8_30", "carry_forward"}
    )
    assert all(row["control_id"] for row in actions)
    assert all(row["action_rationale"] for row in actions)


def _read_csv(path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))
