"""Local readiness is separate from liveness and never probes cloud accounts."""
from contextlib import closing
import json
import sqlite3

import pytest

from cris_sme.api.local_runner import LocalAssessmentRunner, create_handler
from cris_sme.api.run_repository import SqliteAssessmentRunRepository
from tests.test_local_api_runner import _request_raw
from tests.test_run_repository import sample_run
from tests.test_browser_policy import request


def test_fresh_repository_readiness_initializes_schema_without_runs(tmp_path):
    repository = SqliteAssessmentRunRepository(tmp_path / "state.sqlite3")
    repository.check_writable()
    assert repository.list() == []
    repository.save(sample_run())
    assert repository.get("run_persisted")["status"] == "completed"


def test_readiness_preserves_rows_and_releases_write_lock(tmp_path):
    repository = SqliteAssessmentRunRepository(tmp_path / "state.sqlite3")
    repository.save(sample_run(status="running"))
    before = repository.get("run_persisted")
    repository.check_writable()
    assert repository.get("run_persisted") == before
    with closing(repository._connect()) as connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.rollback()


def test_real_database_lock_reports_not_ready_but_alive(tmp_path):
    runner = LocalAssessmentRunner(output_dir=tmp_path / "reports")
    runner._repository.check_writable()
    with closing(runner._repository._connect()) as blocker:
        blocker.execute("BEGIN IMMEDIATE")
        response = json.loads(_request_raw(create_handler(runner), "GET", "/ready", expected_status=503))
        assert response["checks"]["database"] == "unavailable"
        assert json.loads(_request_raw(create_handler(runner), "GET", "/health"))["status"] == "ok"
        blocker.rollback()
    assert json.loads(_request_raw(create_handler(runner), "GET", "/ready"))["status"] == "ready"


@pytest.mark.parametrize("error", [sqlite3.OperationalError("private connection path and token"),
                                  OSError("private filesystem path"), RuntimeError("private diagnostics")])
def test_probe_errors_are_sanitized_and_cloud_checks_are_not_called(tmp_path, monkeypatch, error):
    runner = LocalAssessmentRunner(output_dir=tmp_path)
    def fail():
        raise error
    monkeypatch.setattr(runner._repository, "check_writable", fail)
    monkeypatch.setattr(runner, "azure_environment", lambda: pytest.fail("readiness checked Azure"))
    monkeypatch.setattr(runner, "aws_environment", lambda: pytest.fail("readiness checked AWS"))
    response = _request_raw(create_handler(runner), "GET", "/ready", expected_status=503)
    assert b"private" not in response
    assert json.loads(response) == {"status": "not_ready", "checks": {"lifecycle": "accepting", "database": "unavailable"}}


def test_ready_endpoint_before_first_scan(tmp_path):
    runner = LocalAssessmentRunner(output_dir=tmp_path)
    assert json.loads(_request_raw(create_handler(runner), "GET", "/ready")) == {
        "status": "ready", "checks": {"lifecycle": "accepting", "database": "available"}}
    assert runner.assessment_runs() == []


def test_stopping_runner_skips_database_probe(tmp_path, monkeypatch):
    runner = LocalAssessmentRunner(output_dir=tmp_path)
    runner.stop_workers()
    monkeypatch.setattr(runner._repository, "check_writable", lambda: pytest.fail("shutdown probed database"))
    response = json.loads(_request_raw(create_handler(runner), "GET", "/ready", expected_status=503))
    assert response["checks"] == {"lifecycle": "stopping", "database": "not_checked"}


def test_shutdown_during_probe_does_not_report_ready(tmp_path, monkeypatch):
    runner = LocalAssessmentRunner(output_dir=tmp_path)
    monkeypatch.setattr(runner._repository, "check_writable", runner.stop_workers)
    response = json.loads(_request_raw(create_handler(runner), "GET", "/ready", expected_status=503))
    assert response["status"] == "not_ready"
    assert response["checks"]["lifecycle"] == "stopping"


def test_read_only_database_is_not_ready(tmp_path, monkeypatch):
    runner = LocalAssessmentRunner(output_dir=tmp_path)
    runner._repository.check_writable()
    uri = runner.database_path.resolve().as_uri() + "?mode=ro"
    monkeypatch.setattr(runner._repository, "_connect", lambda: sqlite3.connect(uri, uri=True, timeout=0.2))
    assert runner.readiness()["status"] == "not_ready"


def test_unapproved_origin_is_rejected_before_probe(tmp_path, monkeypatch):
    runner = LocalAssessmentRunner(output_dir=tmp_path)
    monkeypatch.setattr(runner, "readiness", lambda: pytest.fail("unapproved browser probed readiness"))
    response = request(runner, "GET", "/ready", "Origin: https://evil.test\r\n")
    assert b" 403 " in response[0]
