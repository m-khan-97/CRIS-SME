"""Standalone public scan results remain identifiable and recoverable."""
import json
from pathlib import Path
from urllib.parse import quote

import pytest

from cris_sme.api.local_runner import AssessmentRun, LocalAssessmentRunner, create_handler
from tests.test_local_api_runner import _request_raw


REQUEST = {"authorization_confirmed": True, "targets": ["example.com"]}


@pytest.fixture
def runner(tmp_path, monkeypatch):
    def assess(self, targets, **kwargs):
        return {"assessment_type": "public_exposure", "generated_at": "2026-10-02T12:00:00Z",
                "summary": {"target_count": len(targets), "finding_count": 0},
                "targets": targets, "findings": []}

    monkeypatch.setattr("cris_sme.api.local_runner.PublicExposureScanner.assess", assess)
    return LocalAssessmentRunner(output_dir=tmp_path / "outputs" / "reports")


def scan(runner):
    return runner.assess_public_exposure(REQUEST)


def download(runner, path, status=200):
    return _request_raw(create_handler(runner), "GET",
                        f"/api/report-artifact?path={quote(str(path))}", expected_status=status)


def test_two_scans_keep_distinct_files_and_durable_status(runner):
    first, second = scan(runner), scan(runner)
    assert first["run_id"] != second["run_id"]
    assert first["artifacts"]["json"] != second["artifacts"]["json"]
    for report in (first, second):
        saved = json.loads(download(runner, report["artifacts"]["json"]))
        assert saved["run_id"] == report["run_id"]
        assert download(runner, report["artifacts"]["markdown"]).startswith(b"# CRIS-SME")
        status = json.loads(_request_raw(create_handler(runner), "GET", f"/api/assessments/{report['run_id']}"))
        assert status["status"] == "completed"
        assert status["collector"] == "public_exposure"
        assert status["artifacts"]["public_exposure"]["path"] == report["artifacts"]["json"]
    assert not (runner.output_dir / "cris_sme_public_exposure.json").exists()


def test_restart_keeps_prior_artifacts_and_latest(runner):
    first, second = scan(runner), scan(runner)
    restarted = LocalAssessmentRunner(output_dir=runner.output_dir)
    assert {run["run_id"] for run in restarted.assessment_runs()} == {first["run_id"], second["run_id"]}
    for report in (first, second):
        assert json.loads(download(restarted, report["artifacts"]["json"]))["run_id"] == report["run_id"]
    latest = json.loads(_request_raw(create_handler(restarted), "GET", "/outputs/cris_sme_public_exposure.json"))
    assert latest["run_id"] == second["run_id"]
    assert restarted.latest_artifact_listing()["public_exposure"]["path"] == second["artifacts"]["json"]


@pytest.mark.parametrize("status", ["queued", "running", "failed"])
def test_unpublished_scans_cannot_replace_latest_or_be_downloaded(runner, status):
    first, second = scan(runner), scan(runner)
    runner._update_run(second["run_id"], status=status)
    assert runner.latest_artifact_listing()["public_exposure"]["path"] == first["artifacts"]["json"]
    download(runner, second["artifacts"]["json"], 404)
    download(runner, second["artifacts"]["markdown"], 404)


@pytest.mark.parametrize("stage", ["scan", "write"])
def test_failed_scan_persists_failure_without_publishing_partial_files(runner, monkeypatch, stage):
    first = scan(runner)

    def fail(*args, **kwargs):
        if stage == "write":
            report, output = args
            (output / "cris_sme_public_exposure.json").write_text(json.dumps(report))
        raise RuntimeError("private provider diagnostic")

    method = "PublicExposureScanner.assess" if stage == "scan" else "write_public_exposure_outputs"
    with monkeypatch.context() as patch:
        patch.setattr(f"cris_sme.api.local_runner.{method}", fail)
        with pytest.raises(RuntimeError):
            scan(runner)
    failed = next(run for run in runner.assessment_runs() if run["status"] == "failed")
    assert "private provider diagnostic" not in json.dumps(failed)
    assert runner.latest_artifact_listing()["public_exposure"]["path"] == first["artifacts"]["json"]
    download(runner, Path(failed["output_dir"]) / "cris_sme_public_exposure.json", 404)
    assert scan(runner)["status"] == "completed"


@pytest.mark.parametrize("damage", ["missing", "invalid", "array", "mismatch", "symlink"])
def test_invalid_latest_falls_back_to_previous(runner, damage):
    first, second = scan(runner), scan(runner)
    target = Path(second["artifacts"]["json"])
    target.unlink()
    if damage == "symlink":
        target.symlink_to(first["artifacts"]["json"])
    elif damage != "missing":
        target.write_text({"invalid": "not json", "array": "[]", "mismatch": '{"run_id":"wrong"}'}[damage])
    assert runner.latest_artifact_listing()["public_exposure"]["path"] == first["artifacts"]["json"]
    download(runner, target, 404)


def test_legacy_result_is_unchanged_and_available(runner):
    runner.output_dir.mkdir(parents=True)
    target = runner.output_dir / "cris_sme_public_exposure.json"
    target.write_text('{"findings": []}')
    assert runner.latest_public_output_dir() == runner.output_dir
    scan(runner)
    assert target.read_text() == '{"findings": []}'
    assert download(runner, target) == target.read_bytes()


def test_public_and_cloud_latest_remain_independent(runner):
    first = scan(runner)
    run_id = "run_1111111111111111"
    cloud = AssessmentRun(run_id=run_id, collector="aws",
                          output_dir=str(runner.output_dir / "assessments" / run_id / "reports"),
                          figure_dir=str(runner.output_dir / "assessments" / run_id / "figures"))
    runner._register_run(cloud)
    (Path(cloud.output_dir) / "cris_sme_report.json").write_text('{"run_metadata":{"run_id":"cloud-report"}}')
    runner._update_run(run_id, status="completed")
    second = scan(runner)
    assert runner.latest_output_dir() == Path(cloud.output_dir)
    assert runner.latest_artifact_listing()["public_exposure"]["path"] == second["artifacts"]["json"]
    assert [item["report_id"] for item in runner.assessment_history()] == ["cloud-report"]
    assert json.loads(download(runner, first["artifacts"]["json"]))["run_id"] == first["run_id"]


def test_namespace_collision_cannot_change_existing_run(runner, monkeypatch):
    first = scan(runner)
    class Collision:
        hex = first["run_id"].removeprefix("run_")

    with monkeypatch.context() as patch:
        patch.setattr("cris_sme.api.local_runner.uuid.uuid4", Collision)
        with pytest.raises(FileExistsError):
            scan(runner)
    assert runner.get_run(first["run_id"]).status == "completed"
    assert scan(runner)["status"] == "completed"


def test_interrupted_public_scan_is_failed_after_restart(runner):
    report = scan(runner)
    runner._update_run(report["run_id"], status="running")
    restarted = LocalAssessmentRunner(output_dir=runner.output_dir)
    assert restarted.get_run(report["run_id"]).status == "failed"
    assert restarted.public_output_dirs() == []
    download(restarted, report["artifacts"]["json"], 404)


def test_untracked_or_extra_exports_are_denied(runner):
    report = scan(runner)
    extra = Path(report["artifacts"]["json"]).parent / "cris_sme_report.json"
    extra.write_text("{}")
    download(runner, extra, 404)
    runner._update_run(report["run_id"], output_dir="/tmp/unrelated")
    download(runner, report["artifacts"]["json"], 404)


@pytest.mark.parametrize("stage", ["save", "running"])
def test_state_write_failure_releases_admission_and_does_not_publish(runner, monkeypatch, stage):
    def fail(*args, **kwargs):
        raise RuntimeError("state unavailable")

    with monkeypatch.context() as patch:
        if stage == "save":
            patch.setattr(runner._repository, "save", fail)
        else:
            original = runner._update_run
            def update(run_id, **kwargs):
                if kwargs.get("status") == "running":
                    fail()
                return original(run_id, **kwargs)
            patch.setattr(runner, "_update_run", update)
        with pytest.raises(RuntimeError, match="state unavailable"):
            scan(runner)
    assert runner.public_output_dirs() == []
    if stage == "running":
        assert runner.assessment_runs()[0]["status"] == "failed"
    else:
        assert runner.assessment_runs() == []
    assert scan(runner)["status"] == "completed"
