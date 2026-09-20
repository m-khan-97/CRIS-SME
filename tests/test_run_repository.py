"""Tests for SQLite-backed local assessment-run persistence."""
from __future__ import annotations

import sqlite3

from cris_sme.api.run_repository import SqliteAssessmentRunRepository


def sample_run(**overrides):
    run = {
        "run_id": "run_persisted",
        "collector": "azure",
        "status": "completed",
        "requested_at": "2026-09-20T10:00:00Z",
        "started_at": "2026-09-20T10:00:01Z",
        "completed_at": "2026-09-20T10:00:05Z",
        "authorization_confirmed": True,
        "subscription_id": "sub-123",
        "tenant_id": "tenant-456",
        "account_id": "",
        "organization_name": "Example Ltd",
        "role_arn": "",
        "output_dir": "outputs/reports",
        "figure_dir": "outputs/figures",
        "events_path": "outputs/reports/.runs/run_persisted.events.jsonl",
        "returncode": 0,
        "stdout_tail": "ok",
        "stderr_tail": "",
        "error": "",
    }
    run.update(overrides)
    return run


def test_repository_round_trips_and_updates_run_state(tmp_path) -> None:
    repository = SqliteAssessmentRunRepository(tmp_path / "runs.sqlite3")
    repository.save(sample_run(status="queued", completed_at="", returncode=None))
    repository.save(sample_run(status="completed"))

    restored = repository.get("run_persisted")

    assert restored is not None
    assert restored["status"] == "completed"
    assert restored["authorization_confirmed"] is True
    assert restored["returncode"] == 0
    assert repository.list()[0]["organization_name"] == "Example Ltd"


def test_repository_marks_interrupted_runs_failed(tmp_path) -> None:
    repository = SqliteAssessmentRunRepository(tmp_path / "runs.sqlite3")
    repository.save(sample_run(status="running", completed_at="", returncode=None))

    changed = repository.mark_interrupted(completed_at="2026-09-20T11:00:00Z")
    restored = repository.get("run_persisted")

    assert changed == 1
    assert restored is not None
    assert restored["status"] == "failed"
    assert restored["returncode"] == -1
    assert "restarted" in restored["error"]


def test_repository_schema_does_not_store_external_id(tmp_path) -> None:
    database_path = tmp_path / "runs.sqlite3"
    repository = SqliteAssessmentRunRepository(database_path)
    repository.save(sample_run(external_id="must-not-be-stored"))

    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(assessment_runs)")
        }

    assert "external_id" not in columns
