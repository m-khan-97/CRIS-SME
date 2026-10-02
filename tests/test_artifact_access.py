"""Only recognized exports may leave the local artifact API."""
import json
import os
from pathlib import Path
from urllib.parse import quote

import pytest

from cris_sme.api.artifact_access import is_report_export, read_regular_file
from cris_sme.api.local_runner import LocalAssessmentRunner, create_handler
from tests.test_local_api_runner import _request_raw


@pytest.mark.parametrize("name", [
    ".runs/assessment_runs.sqlite3", ".env", "secret.json", "credentials.txt",
    "cris_sme_ce_review_ledger.json", "../cris_sme_report.json",
    "nested/cris_sme_report.json", "history/secret.json",
])
@pytest.mark.parametrize("route", ["outputs", "artifact"])
def test_internal_and_unregistered_files_are_not_downloadable(tmp_path, name, route):
    output = tmp_path / "reports"
    output.mkdir()
    handler = create_handler(LocalAssessmentRunner(output_dir=output))
    target = output / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text("private")
    url = f"/outputs/{name}" if route == "outputs" else f"/api/report-artifact?path={quote(str(target))}"
    _request_raw(handler, "GET", url, expected_status=404)


@pytest.mark.parametrize("name", [
    "cris_sme_report.json", "cris_sme_summary.txt", "cris_sme_findings.csv",
    "history/cris_sme_report_20260927T120000Z.json",
    "remediation_scripts/cris_sme_remediation_aws_cli.sh", "figures/risk_trend.png",
])
def test_expected_exports_are_downloadable(tmp_path, name):
    target = tmp_path / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{}")
    handler = create_handler(LocalAssessmentRunner(output_dir=tmp_path))
    assert _request_raw(handler, "GET", f"/outputs/{name}") == b"{}"
    assert _request_raw(handler, "GET", f"/api/report-artifact?path={quote(str(target))}") == b"{}"


@pytest.mark.parametrize("directory_link", [False, True])
def test_symlinks_cannot_publish_files_even_with_allowed_names(tmp_path, directory_link):
    output = tmp_path / "reports"
    output.mkdir()
    secret = tmp_path / "secret"
    secret.mkdir()
    (secret / "cris_sme_report_20260927T120000Z.json").write_text("private")
    if directory_link:
        (output / "history").symlink_to(secret, target_is_directory=True)
        relative = Path("history/cris_sme_report_20260927T120000Z.json")
    else:
        relative = Path("cris_sme_report.json")
        (output / relative).symlink_to(secret / "cris_sme_report_20260927T120000Z.json")
    handler = create_handler(LocalAssessmentRunner(output_dir=output))
    _request_raw(handler, "GET", f"/outputs/{relative}", expected_status=404)
    _request_raw(handler, "GET", f"/api/report-artifact?path={quote(str(output / relative))}", expected_status=404)
    assert LocalAssessmentRunner(output_dir=output).assessment_history() == []


def test_sibling_exports_require_an_indexed_report(tmp_path):
    output = tmp_path / "outputs" / "reports"
    output.mkdir(parents=True)
    sibling = output.parent / "customer" / "reports"
    sibling.mkdir(parents=True)
    target = sibling / "cris_sme_summary.txt"
    target.write_text("summary")
    handler = create_handler(LocalAssessmentRunner(output_dir=output))
    url = f"/api/report-artifact?path={quote(str(target))}"
    _request_raw(handler, "GET", url, expected_status=404)
    (sibling / "cris_sme_report.json").write_text(json.dumps({"run_metadata": {"run_id": "customer"}}))
    assert _request_raw(handler, "GET", url) == b"summary"
    figure = sibling.parent / "figures" / "risk_trend.png"
    figure.parent.mkdir()
    figure.write_bytes(b"image")
    assert _request_raw(handler, "GET", f"/api/report-artifact?path={quote(str(figure))}") == b"image"


def test_fifo_is_rejected_without_blocking(tmp_path):
    os.mkfifo(tmp_path / "cris_sme_report.json")
    with pytest.raises(ValueError, match="regular"):
        read_regular_file(tmp_path, Path("cris_sme_report.json"))


def test_replacement_with_symlink_during_open_is_rejected(tmp_path, monkeypatch):
    target = tmp_path / "cris_sme_report.json"
    target.write_text("report")
    secret = tmp_path / "secret"
    secret.write_text("private")
    original = os.open

    def replacing_open(path, flags, **kwargs):
        if path == target.name:
            target.unlink()
            target.symlink_to(secret)
        return original(path, flags, **kwargs)

    monkeypatch.setattr(os, "open", replacing_open)
    monkeypatch.setattr(os, "supports_dir_fd", {*os.supports_dir_fd, replacing_open})
    with pytest.raises(OSError):
        read_regular_file(tmp_path, Path(target.name))


def test_allowlist_does_not_accept_arbitrary_prefixed_files():
    assert not is_report_export(Path("cris_sme_secrets.json"))
    assert not is_report_export(Path("history/cris_sme_report_secrets.json"))
