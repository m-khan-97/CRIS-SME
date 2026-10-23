"""Cached lifecycle state must not advance before its database commit."""
import json
from pathlib import Path
import subprocess
from urllib.parse import quote

import pytest

from cris_sme.api.local_runner import AssessmentRun, LocalAssessmentRunner, create_handler
from tests.test_local_api_runner import _request_json, _request_raw


def registered_run(tmp_path, collector):
    runner = LocalAssessmentRunner(output_dir=tmp_path / "reports")
    root = runner.output_dir / "assessments" / "run_atomic"
    run = AssessmentRun(run_id="run_atomic", collector=collector, status="queued",
                        authorization_confirmed=True, external_id="private-external-id",
                        output_dir=str(root / "reports"), figure_dir=str(root / "figures"))
    runner._register_run(run)
    return runner, run


@pytest.mark.parametrize("collector", ["aws", "azure", "public_exposure"])
@pytest.mark.parametrize("status", ["running", "completed", "failed", "cancelled"])
def test_failed_commit_does_not_mutate_cached_or_persisted_run(tmp_path, monkeypatch, collector, status):
    runner, run = registered_run(tmp_path, collector)
    before = vars(run).copy()
    persisted = runner._repository.get(run.run_id)
    def fail(values):
        assert values["status"] == status
        assert vars(run) == before
        raise OSError("fixture database unavailable")
    monkeypatch.setattr(runner._repository, "save", fail)
    with pytest.raises(OSError):
        runner._update_run(run.run_id, status=status, completed_at="2026-10-05T12:00:00Z",
                           returncode=0, stdout_tail="new private diagnostics")
    assert runner.get_run(run.run_id) is run
    assert vars(run) == before
    assert runner._repository.get(run.run_id) == persisted
    assert runner.completed_output_dirs(collector=collector) == []


@pytest.mark.parametrize("collector", ["aws", "azure", "public_exposure"])
def test_successful_commit_precedes_mutation_and_preserves_run_identity(tmp_path, monkeypatch, collector):
    runner, run = registered_run(tmp_path, collector)
    save = runner._repository.save
    def observe(values):
        assert run.status == "queued"
        assert values["status"] == "completed"
        assert "external_id" not in values
        save(values)
        assert run.status == "queued"
    monkeypatch.setattr(runner._repository, "save", observe)
    runner._update_run(run.run_id, status="completed", returncode=0)
    assert runner.get_run(run.run_id) is run
    assert run.status == "completed"
    assert run.external_id == "private-external-id"
    assert runner._repository.get(run.run_id)["status"] == "completed"


def test_failed_cancellation_commit_does_not_signal_worker(tmp_path, monkeypatch):
    runner, run = registered_run(tmp_path, "aws")
    def fail(values):
        raise OSError("fixture database unavailable")
    monkeypatch.setattr(runner._repository, "save", fail)
    with pytest.raises(OSError):
        runner.cancel_assessment(run.run_id)
    assert run.status == "queued"
    assert not runner._cancel_events[run.run_id].is_set()
    assert runner._repository.get(run.run_id)["status"] == "queued"


@pytest.mark.parametrize("collector", ["aws", "azure"])
def test_cloud_completion_commit_failure_excludes_partial_report(tmp_path, monkeypatch, collector):
    class InlineWorker:
        def __init__(self, *, target, args, daemon):
            self.target, self.args = target, args
        def start(self):
            self.target(*self.args)
    monkeypatch.setattr("cris_sme.api.local_runner.threading.Thread", InlineWorker)
    monkeypatch.setattr("cris_sme.api.local_runner._aws_login_environment", lambda *args: {})
    def command(command, **kwargs):
        output = Path(kwargs["env"]["CRIS_SME_OUTPUT_DIR"])
        (output / "cris_sme_report.json").write_text(json.dumps({"run_metadata": {"run_id": output.parent.name}}))
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
    runner = LocalAssessmentRunner(output_dir=tmp_path / "reports", command_runner=command)
    save = runner._repository.save
    def fail_completion(values):
        if values["status"] == "completed":
            assert runner.get_run(values["run_id"]).status == "running"
            raise OSError("fixture completion commit failure")
        save(values)
    monkeypatch.setattr(runner._repository, "save", fail_completion)
    run = getattr(runner, f"start_{collector}_assessment")({"authorization_confirmed": True})
    assert run.status == "failed"
    assert runner._repository.get(run.run_id)["status"] == "failed"
    assert runner.assessment_history() == []
    assert runner.completed_output_dirs() == []
    artifact = str(Path(run.output_dir, "cris_sme_report.json"))
    _request_raw(create_handler(runner), "GET", f"/api/report-artifact?path={quote(artifact, safe='')}", expected_status=404)
    assert runner._scan_slot.acquire(blocking=False)
    runner._scan_slot.release()


def test_public_completion_commit_failure_does_not_return_success(tmp_path, monkeypatch):
    monkeypatch.setattr("cris_sme.api.local_runner.PublicExposureScanner.assess",
                        lambda *args, **kwargs: {"targets": [], "findings": []})
    runner = LocalAssessmentRunner(output_dir=tmp_path / "reports")
    save = runner._repository.save
    def fail_completion(values):
        if values["status"] == "completed":
            assert runner.get_run(values["run_id"]).status == "running"
            raise OSError("fixture completion commit failure")
        save(values)
    monkeypatch.setattr(runner._repository, "save", fail_completion)
    response = _request_json(create_handler(runner), "POST", "/api/public-exposure",
                             {"authorization_confirmed": True, "targets": ["example.com"]}, expected_status=500)
    assert "fixture completion commit failure" not in str(response)
    assert runner.assessment_runs()[0]["status"] == "failed"
    assert runner.completed_output_dirs(collector="public_exposure") == []
    assert runner._scan_slot.acquire(blocking=False)
    runner._scan_slot.release()
