"""One local assessment owns the shared report output until completion."""
from threading import Barrier, Thread

import pytest

from cris_sme.api.local_runner import AssessmentBusyError, LocalAssessmentRunner, create_handler
from tests.test_local_api_runner import _request_json


REQUEST = {"authorization_confirmed": True, "targets": ["example.com"]}


@pytest.fixture
def held_runner(tmp_path, monkeypatch):
    workers = []

    class Worker:
        def __init__(self, *, target, args, daemon):
            self.target, self.args = target, args
            workers.append(self)

        def start(self):
            pass

        def finish(self):
            self.target(*self.args)

    runner = LocalAssessmentRunner(output_dir=tmp_path)
    monkeypatch.setattr("cris_sme.api.local_runner.threading.Thread", Worker)
    for provider in ("aws", "azure"):
        monkeypatch.setattr(runner, f"_execute_{provider}_run",
                            lambda run_id: runner._update_run(run_id, status="completed"))
    return runner, workers


def start(runner, provider):
    if provider == "public":
        return runner.assess_public_exposure(REQUEST)
    return getattr(runner, f"start_{provider}_assessment")(REQUEST)


@pytest.mark.parametrize("first", ["aws", "azure"])
@pytest.mark.parametrize("second", ["aws", "azure", "public"])
def test_active_scan_rejects_competitors_without_run_or_worker(held_runner, first, second):
    runner, workers = held_runner
    start(runner, first)
    with pytest.raises(AssessmentBusyError):
        start(runner, second)
    assert len(workers) == 1
    assert len(runner.assessment_runs()) == 1
    workers[0].finish()
    start(runner, "azure")
    assert len(workers) == 2
    workers[1].finish()


def test_simultaneous_requests_admit_exactly_one_scan(held_runner):
    runner, workers = held_runner
    barrier = Barrier(8)
    outcomes = []

    def request():
        barrier.wait(timeout=3)
        try:
            runner.start_azure_assessment(REQUEST)
            outcomes.append("accepted")
        except AssessmentBusyError:
            outcomes.append("busy")

    callers = [Thread(target=request) for _ in range(8)]
    for caller in callers:
        caller.start()
    for caller in callers:
        caller.join(timeout=5)
        assert not caller.is_alive()
    assert outcomes.count("accepted") == 1
    assert outcomes.count("busy") == 7
    assert len(workers) == 1
    workers[0].finish()


def test_public_scan_holds_slot_through_report_publication(held_runner, monkeypatch):
    runner, workers = held_runner
    stages = []

    def check_busy(stage):
        for provider in ("aws", "azure", "public"):
            with pytest.raises(AssessmentBusyError):
                start(runner, provider)
        stages.append(stage)

    def scan(*args, **kwargs):
        check_busy("scan")
        return {}

    def publish(*args):
        check_busy("publish")
        return {}

    monkeypatch.setattr("cris_sme.api.local_runner.PublicExposureScanner.assess", scan)
    monkeypatch.setattr("cris_sme.api.local_runner.write_public_exposure_outputs", publish)
    assert start(runner, "public")["status"] == "completed"
    assert stages == ["scan", "publish"]
    start(runner, "aws")
    workers[0].finish()


@pytest.mark.parametrize("stage", ["scan", "publish"])
def test_public_failure_returns_capacity(held_runner, monkeypatch, stage):
    runner, workers = held_runner
    def fail(*args, **kwargs):
        raise RuntimeError("fixture failure")

    monkeypatch.setattr("cris_sme.api.local_runner.PublicExposureScanner.assess",
                        fail if stage == "scan" else lambda *args, **kwargs: {})
    monkeypatch.setattr("cris_sme.api.local_runner.write_public_exposure_outputs", fail)
    with pytest.raises(RuntimeError):
        start(runner, "public")
    start(runner, "azure")
    workers[0].finish()


def test_worker_exception_is_terminal_and_returns_capacity(held_runner, monkeypatch):
    runner, workers = held_runner
    def fail(run_id):
        raise RuntimeError("sensitive internal error")

    monkeypatch.setattr(runner, "_execute_aws_run", fail)
    run = start(runner, "aws")
    workers[0].finish()
    assert runner.get_run(run.run_id).status == "failed"
    assert "sensitive" not in runner.get_run(run.run_id).error
    start(runner, "azure")
    workers[1].finish()


def test_thread_start_failure_marks_failed_and_returns_capacity(held_runner, monkeypatch):
    runner, workers = held_runner
    def fail(self):
        raise RuntimeError("thread start failed")

    import cris_sme.api.local_runner as module
    worker_type = module.threading.Thread
    monkeypatch.setattr(worker_type, "start", fail)
    with pytest.raises(RuntimeError):
        start(runner, "aws")
    assert runner.assessment_runs()[0]["status"] == "failed"
    monkeypatch.setattr(worker_type, "start", lambda self: None)
    start(runner, "azure")
    workers[1].finish()


def test_persistence_failure_returns_capacity_without_worker(held_runner, monkeypatch):
    runner, workers = held_runner
    original = runner._repository.save
    def fail(values):
        raise OSError("disk failure")

    monkeypatch.setattr(runner._repository, "save", fail)
    with pytest.raises(OSError):
        start(runner, "aws")
    assert workers == []
    monkeypatch.setattr(runner._repository, "save", original)
    start(runner, "azure")
    workers[0].finish()


@pytest.mark.parametrize("route", ["aws", "azure", "public-exposure"])
def test_busy_http_request_returns_409(held_runner, route):
    runner, workers = held_runner
    start(runner, "aws")
    handler = create_handler(runner)
    path = f"/api/assessments/{route}" if route != "public-exposure" else "/api/public-exposure"
    body = _request_json(handler, "POST", path, REQUEST, expected_status=409)
    assert "already active" in body["message"]
    workers[0].finish()
