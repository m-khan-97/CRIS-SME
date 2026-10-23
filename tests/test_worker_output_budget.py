"""A noisy native cloud worker must not publish its partial report."""
from pathlib import Path
import sys
import time
from urllib.parse import quote

import pytest

from cris_sme.api.local_runner import LocalAssessmentRunner, create_handler
from cris_sme.api.managed_worker import run_managed
from tests.test_local_api_runner import _request_raw


@pytest.mark.parametrize("provider", ["azure", "aws"])
def test_noisy_scan_fails_privately_and_returns_capacity(tmp_path, monkeypatch, provider):
    script = """
import json, os
from pathlib import Path
output = Path(os.environ['CRIS_SME_OUTPUT_DIR'])
(output/'cris_sme_report.json').write_text(json.dumps({'run_metadata':{'run_id':output.parent.name}}))
os.write(1,b'PRIVATE_WORKER_DIAGNOSTIC'*1024)
"""
    def command(command, **kwargs):
        return run_managed([sys.executable, "-c", script], output_limit=1024, **kwargs)
    monkeypatch.setattr("cris_sme.api.local_runner.run_managed", command)
    monkeypatch.setattr("cris_sme.api.local_runner._aws_login_environment", lambda *args: {})
    runner = LocalAssessmentRunner(output_dir=tmp_path / "reports")
    run = getattr(runner, f"start_{provider}_assessment")({"authorization_confirmed": True})
    try:
        deadline = time.monotonic() + 7
        while run.status in {"queued", "running"} or run.run_id in runner._workers:
            assert time.monotonic() < deadline
            time.sleep(0.01)
        assert run.status == "failed"
        assert "captured-output budget" in run.error
        assert "PRIVATE_WORKER_DIAGNOSTIC" not in str(run.to_dict())
        assert run.stdout_tail == run.stderr_tail == ""
        assert Path(run.output_dir, "cris_sme_report.json").exists()
        assert runner.assessment_history() == []
        assert runner.completed_output_dirs() == []
        artifact = str(Path(run.output_dir, "cris_sme_report.json"))
        _request_raw(create_handler(runner), "GET",
                     f"/api/report-artifact?path={quote(artifact, safe='')}", expected_status=404)
        assert runner._scan_slot.acquire(blocking=False)
        runner._scan_slot.release()
        restored = LocalAssessmentRunner(output_dir=tmp_path / "reports").get_run(run.run_id)
        assert restored is not None and restored.status == "failed"
    finally:
        runner.stop_workers()
