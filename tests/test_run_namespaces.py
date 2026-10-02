"""Cloud API runs retain their own artifacts across scans and API restarts."""
import json
from pathlib import Path
import subprocess
from urllib.parse import quote

import pytest

from cris_sme.api.local_runner import LocalAssessmentRunner, create_handler
from cris_sme.api import local_runner
from tests.test_local_api_runner import _request_raw


@pytest.fixture
def runner(tmp_path, monkeypatch):
    class InlineWorker:
        def __init__(self, *, target, args, daemon):
            self.target, self.args = target, args

        def start(self):
            self.target(*self.args)

    monkeypatch.setattr("cris_sme.api.local_runner.threading.Thread", InlineWorker)
    monkeypatch.setattr("cris_sme.api.local_runner._aws_login_environment", lambda *args: {})

    def command(cmd, **kwargs):
        env = kwargs["env"]
        output = Path(env["CRIS_SME_OUTPUT_DIR"])
        run_id = output.parent.name
        report = {"run_metadata": {"run_id": run_id},
                  "organizations": [{"organization_name": "Same label"}],
                  "report_artifacts": {"summary": str(output / "cris_sme_summary.txt")}}
        (output / "cris_sme_report.json").write_text(json.dumps(report))
        (output / "cris_sme_summary.txt").write_text(run_id)
        (Path(env["CRIS_SME_FIGURE_DIR"]) / "risk_trend.png").write_bytes(run_id.encode())
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    return LocalAssessmentRunner(output_dir=tmp_path / "outputs" / "reports", command_runner=command)


def start(runner, provider="azure"):
    return getattr(runner, f"start_{provider}_assessment")(
        {"authorization_confirmed": True, "organization_name": "Same label"})


@pytest.mark.parametrize("provider", ["azure", "aws"])
def test_same_labels_never_overwrite_reports_or_figures(runner, provider):
    first = start(runner, provider)
    second = start(runner, provider)
    assert first.status == second.status == "completed"
    assert first.output_dir != second.output_dir
    assert first.figure_dir != second.figure_dir
    for run in (first, second):
        assert (Path(run.output_dir) / "cris_sme_summary.txt").read_text() == run.run_id
        assert (Path(run.figure_dir) / "risk_trend.png").read_bytes() == run.run_id.encode()
        assert run.to_dict()["artifacts"]["report"]["path"] == str(Path(run.output_dir) / "cris_sme_report.json")
    assert not (runner.output_dir / "cris_sme_report.json").exists()


def test_history_selection_and_downloads_survive_restart(runner):
    runs = [start(runner), start(runner, "aws")]
    restarted = LocalAssessmentRunner(output_dir=runner.output_dir)
    assert {entry["run_id"] for entry in restarted.assessment_history()} == {run.run_id for run in runs}
    handler = create_handler(restarted)
    for run in runs:
        assert restarted.get_run(run.run_id).output_dir == run.output_dir
        assert restarted.assessment_report(run.run_id)["run_metadata"]["run_id"] == run.run_id
        for path in (Path(run.output_dir) / "cris_sme_summary.txt", Path(run.figure_dir) / "risk_trend.png"):
            assert _request_raw(handler, "GET", f"/api/report-artifact?path={quote(str(path))}") == run.run_id.encode()
    assert _request_raw(handler, "GET", "/outputs/cris_sme_summary.txt") == runs[-1].run_id.encode()
    response = json.loads(_request_raw(handler, "GET", "/api/artifacts/latest"))
    assert response["artifacts"]["report"]["path"] == str(Path(runs[-1].output_dir) / "cris_sme_report.json")


@pytest.mark.parametrize("status", ["queued", "running", "failed"])
def test_unpublished_run_cannot_replace_latest_or_enter_history(runner, status):
    first, second = start(runner), start(runner)
    runner._update_run(second.run_id, status=status)
    assert runner.latest_output_dir() == Path(first.output_dir)
    assert [entry["run_id"] for entry in runner.assessment_history()] == [first.run_id]
    target = Path(second.output_dir) / "cris_sme_report.json"
    _request_raw(create_handler(runner), "GET", f"/api/report-artifact?path={quote(str(target))}", expected_status=404)


def test_failed_child_does_not_publish_partial_report(runner):
    first = start(runner)
    successful = runner.command_runner

    def failing(cmd, **kwargs):
        successful(cmd, **kwargs)
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="failed")

    runner.command_runner = failing
    failed = start(runner)
    assert failed.status == "failed"
    assert (Path(failed.output_dir) / "cris_sme_report.json").exists()
    assert runner.assessment_report(failed.run_id) is None
    assert runner.latest_output_dir() == Path(first.output_dir)


def test_namespace_collision_leaves_original_unchanged_and_releases_slot(runner, monkeypatch):
    first = start(runner)

    class Collision:
        hex = first.run_id.removeprefix("run_")

    with monkeypatch.context() as patch:
        patch.setattr("cris_sme.api.local_runner.uuid.uuid4", Collision)
        with pytest.raises(FileExistsError):
            start(runner)
    assert runner.get_run(first.run_id).status == "completed"
    assert (Path(first.output_dir) / "cris_sme_summary.txt").read_text() == first.run_id
    assert start(runner).status == "completed"


def test_legacy_reports_remain_unchanged_and_selectable(runner):
    runner.output_dir.mkdir(parents=True)
    legacy = runner.output_dir / "cris_sme_report.json"
    content = '{"run_metadata": {"run_id": "legacy"}}'
    legacy.write_text(content)
    assert runner.latest_output_dir() == runner.output_dir
    start(runner)
    assert legacy.read_text() == content
    assert runner.assessment_report("legacy")["run_metadata"]["run_id"] == "legacy"


def test_nondefault_output_root_indexes_completed_runs(runner, tmp_path):
    runner.output_dir = tmp_path / "custom"
    run = start(runner)
    assert runner.assessment_report(run.run_id) is not None


@pytest.mark.parametrize("damage", ["missing", "invalid", "symlink"])
def test_invalid_latest_report_falls_back_to_previous(runner, tmp_path, damage):
    first, second = start(runner), start(runner)
    report = Path(second.output_dir) / "cris_sme_report.json"
    report.unlink()
    if damage == "invalid":
        report.write_text("not json")
    elif damage == "symlink":
        report.symlink_to(Path(first.output_dir) / "cris_sme_report.json")
    assert runner.latest_output_dir() == Path(first.output_dir)


def test_persisted_path_cannot_redirect_publication_outside_namespace(runner):
    run = start(runner)
    runner._update_run(run.run_id, output_dir="/tmp/unrelated")
    assert runner.completed_output_dirs() == []
    assert runner.assessment_report(run.run_id) is None


def test_standalone_public_exposure_stays_accessible_after_cloud_scan(runner):
    start(runner)
    path = runner.output_dir / "cris_sme_public_exposure.json"
    path.write_text('{"findings": []}')
    assert runner.latest_artifact_listing()["public_exposure"]["path"] == str(path)
    assert _request_raw(create_handler(runner), "GET", "/outputs/cris_sme_public_exposure.json") == path.read_bytes()


def test_legacy_discovery_does_not_publish_untracked_sibling_namespace(runner):
    start(runner)
    directory = runner.output_dir.parent / "other" / "assessments" / "run_1111111111111111" / "reports"
    directory.mkdir(parents=True)
    (directory / "cris_sme_report.json").write_text('{"run_metadata": {"run_id": "untracked"}}')
    assert runner.assessment_report("untracked") is None


def test_real_mock_assessment_generates_and_serves_namespaced_artifacts(runner):
    def mock_command(cmd, **kwargs):
        env = kwargs["env"]
        env["CRIS_SME_COLLECTOR"] = "mock"
        env["CRIS_SME_ENABLE_NARRATOR"] = "false"
        env["PYTHONPATH"] = str(Path(local_runner.__file__).parents[2])
        return subprocess.run(cmd, **{**kwargs, "timeout": 60})

    runner.command_runner = mock_command
    run = start(runner)
    assert run.status == "completed", run.error
    report_path = Path(run.output_dir) / "cris_sme_report.json"
    report = json.loads(report_path.read_text())
    assert report["collector_mode"] == "mock"
    assert report["report_artifacts"]["json_report"] == str(report_path)
    report_id = report["run_metadata"]["run_id"]
    assert runner.assessment_report(report_id) == report
    handler = create_handler(runner)
    assert json.loads(_request_raw(handler, "GET", "/outputs/cris_sme_report.json")) == report
    for path in report["report_artifacts"]["figures"].values():
        assert Path(path).parent == Path(run.figure_dir)
        body = _request_raw(handler, "GET", f"/api/report-artifact?path={quote(path)}")
        assert body == Path(path).read_bytes()
        assert body.startswith(b"\x89PNG") if Path(path).suffix == ".png" else b"<svg" in body
