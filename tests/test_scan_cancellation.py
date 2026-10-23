from pathlib import Path
import os
import signal
import subprocess
import sys

import pytest

from cris_sme.api.local_runner import AssessmentBusyError, LocalAssessmentRunner, create_handler
from cris_sme.api.managed_worker import run_managed
from cris_sme.api.state_ownership import own_state
from tests.test_local_api_runner import _request_json
from tests.test_managed_worker import alive, wait_for_file


REQUEST = {"authorization_confirmed": True}


@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
def test_server_signal_stops_worker_before_unlocking(tmp_path, signum):
    script = '''
import os, sys
from pathlib import Path
from cris_sme.api import local_runner
from cris_sme.api.managed_worker import run_managed
root = Path(sys.argv[1])
worker_script = "import os,signal,time; from pathlib import Path; signal.signal(signal.SIGTERM,signal.SIG_IGN); Path(" + repr(str(root/'ready')) + ").write_text(str(os.getpid())); time.sleep(60)"
def command(command, **kwargs):
    return run_managed([sys.executable, '-c', worker_script], **kwargs)
local_runner.run_managed = command
original = local_runner.LocalAssessmentRunner
class Runner(original):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.start_azure_assessment({'authorization_confirmed':True})
class Server:
    def __init__(self, *args, **kwargs): pass
    def serve_forever(self):
        (root/'serving').touch()
        import time
        time.sleep(60)
    def server_close(self): pass
local_runner.LocalAssessmentRunner = Runner
local_runner.BoundedHTTPServer = Server
local_runner.run_server(output_dir=root/'reports', figure_dir=root/'figures', database_path=root/'state.sqlite3')
'''
    ready = tmp_path / "ready"
    from cris_sme.api import local_runner
    process = subprocess.Popen([sys.executable, "-c", script, str(tmp_path)],
                               start_new_session=True,
                               env={**os.environ,
                                    "PYTHONPATH": str(Path(local_runner.__file__).parents[2])},
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_for_file(ready)
        # The fake listener marks signal-handler installation without cloud access.
        import time
        deadline = time.monotonic() + 5
        while not (tmp_path / "serving").exists():
            assert time.monotonic() < deadline
            time.sleep(0.01)
        process.send_signal(signum)
        process.wait(timeout=10)
        assert not alive(int(ready.read_text()))
        with own_state(tmp_path/'reports', tmp_path/'figures', tmp_path/'state.sqlite3'):
            runner = LocalAssessmentRunner(output_dir=tmp_path/'reports', database_path=tmp_path/'state.sqlite3')
            assert next(iter(runner._runs.values())).status == "cancelled"
    finally:
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        if ready.exists() and ready.read_text() and alive(int(ready.read_text())):
            try:
                os.killpg(int(ready.read_text()), signal.SIGKILL)
            except ProcessLookupError:
                pass


@pytest.mark.parametrize("provider", ["azure", "aws"])
def test_queued_cancel_skips_worker_and_is_idempotent(tmp_path, monkeypatch, provider):
    workers = []
    class HeldWorker:
        def __init__(self, *, target, args, daemon):
            self.target, self.args = target, args
            workers.append(self)
        def start(self):
            pass
    monkeypatch.setattr("cris_sme.api.local_runner.threading.Thread", HeldWorker)
    runner = LocalAssessmentRunner(output_dir=tmp_path, command_runner=lambda *args, **kwargs: pytest.fail("cancelled scan executed"))
    run = getattr(runner, f"start_{provider}_assessment")(REQUEST)
    response = _request_json(create_handler(runner), "POST", f"/api/assessments/{run.run_id}/cancel", {}, expected_status=202)
    assert response["status"] == "cancelling"
    with pytest.raises(AssessmentBusyError):
        runner.start_azure_assessment(REQUEST)
    workers[0].target(*workers[0].args)
    assert run.status == "cancelled"
    assert runner.cancel_assessment(run.run_id).status == "cancelled"
    assert LocalAssessmentRunner(output_dir=tmp_path).get_run(run.run_id).status == "cancelled"
    assert runner._scan_slot.acquire(blocking=False)
    runner._scan_slot.release()


@pytest.mark.parametrize("provider", ["azure", "aws"])
@pytest.mark.parametrize("operation", ["cancel", "shutdown"])
def test_active_native_worker_stops_before_releasing_slot(tmp_path, monkeypatch, provider, operation):
    ready = tmp_path / "ready"
    script = """
import json, os, signal, sys, time
from pathlib import Path
signal.signal(signal.SIGTERM, signal.SIG_IGN)
output = Path(os.environ['CRIS_SME_OUTPUT_DIR'])
(output/'cris_sme_report.json').write_text(json.dumps({'run_metadata':{'run_id':output.parent.name}}))
Path(sys.argv[1]).write_text(str(os.getpid()))
time.sleep(60)
"""
    def command(command, **kwargs):
        return run_managed([sys.executable, "-c", script, str(ready)], **kwargs)
    monkeypatch.setattr("cris_sme.api.local_runner.run_managed", command)
    monkeypatch.setattr("cris_sme.api.local_runner._aws_login_environment", lambda *args: {})
    runner = LocalAssessmentRunner(output_dir=tmp_path / "reports")
    run = getattr(runner, f"start_{provider}_assessment")(REQUEST)
    try:
        wait_for_file(ready)
        if operation == "cancel":
            assert runner.cancel_assessment(run.run_id).status == "cancelling"
            with pytest.raises(AssessmentBusyError):
                runner.start_azure_assessment(REQUEST)
            worker = runner._workers[run.run_id]
            worker.join(timeout=7)
            assert not worker.is_alive()
            assert not runner._stopping
        else:
            runner.stop_workers()
        assert run.status == "cancelled"
        assert not alive(int(ready.read_text()))
        assert Path(run.output_dir, "cris_sme_report.json").exists()
        assert runner.assessment_history() == []
        assert runner.completed_output_dirs() == []
        assert runner._scan_slot.acquire(blocking=False)
        runner._scan_slot.release()
    finally:
        runner.stop_workers()


def test_unknown_run_cancel_is_not_found(tmp_path):
    runner = LocalAssessmentRunner(output_dir=tmp_path)
    _request_json(create_handler(runner), "POST", "/api/assessments/unknown/cancel", {}, expected_status=404)


@pytest.mark.parametrize("provider", ["aws", "azure"])
def test_shutdown_rejects_new_cloud_workers(tmp_path, provider):
    runner = LocalAssessmentRunner(output_dir=tmp_path)
    runner.stop_workers()
    with pytest.raises(AssessmentBusyError, match="shutting down"):
        getattr(runner, f"start_{provider}_assessment")(REQUEST)
    assert runner._scan_slot.acquire(blocking=False)
    runner._scan_slot.release()


def test_completed_run_cannot_be_cancelled(tmp_path):
    from cris_sme.api.local_runner import AssessmentRun
    runner = LocalAssessmentRunner(output_dir=tmp_path)
    run = AssessmentRun(run_id="run_1111111111111111", collector="aws", status="completed")
    runner._repository.save(run.to_persisted())
    _request_json(create_handler(runner), "POST", f"/api/assessments/{run.run_id}/cancel", {}, expected_status=409)
    assert runner.get_run(run.run_id).status == "completed"


def test_cancelling_state_is_failed_on_restart(tmp_path):
    from cris_sme.api.local_runner import AssessmentRun
    runner = LocalAssessmentRunner(output_dir=tmp_path)
    run = AssessmentRun(run_id="run_1111111111111111", collector="aws", status="cancelling")
    runner._repository.save(run.to_persisted())
    restarted = LocalAssessmentRunner(output_dir=tmp_path)
    assert restarted.get_run(run.run_id).status == "failed"
