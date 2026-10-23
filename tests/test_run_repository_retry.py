"""Retry lock contention without retaining connections or partial transactions."""
from contextlib import closing
import sqlite3

import pytest

from cris_sme.api import run_repository
from cris_sme.api.run_repository import SqliteAssessmentRunRepository
from tests.test_run_repository import sample_run


def sqlite_error(code):
    error = sqlite3.OperationalError("fixture locked database")
    if code is not None:
        error.sqlite_errorcode = code
    return error


@pytest.fixture
def repository(tmp_path):
    repo = SqliteAssessmentRunRepository(tmp_path / "runs.sqlite3")
    with closing(repo._connect()) as connection:
        connection.execute("CREATE TABLE markers (id INTEGER PRIMARY KEY)")
    return repo


@pytest.mark.parametrize("code", [sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED, sqlite3.SQLITE_BUSY_SNAPSHOT])
def test_retries_with_backoff_rollback_and_fresh_closed_connections(repository, monkeypatch, code):
    connections, sleeps = [], []
    monkeypatch.setattr(run_repository.time, "sleep", sleeps.append)
    def operation(connection):
        connections.append(connection)
        connection.execute("INSERT INTO markers VALUES (1)")
        if len(connections) < 3:
            raise sqlite_error(code)
        return "committed"
    assert repository._write(operation) == "committed"
    assert sleeps == [0.05, 0.1]
    assert len({id(connection) for connection in connections}) == 3
    for connection in connections:
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            connection.execute("SELECT 1")
    with closing(repository._connect()) as connection:
        assert connection.execute("SELECT COUNT(*) FROM markers").fetchone()[0] == 1


@pytest.mark.parametrize("code", [sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED])
def test_retry_exhaustion_rolls_back_and_reraises_last_error(repository, monkeypatch, code):
    errors, sleeps = [], []
    monkeypatch.setattr(run_repository.time, "sleep", sleeps.append)
    def operation(connection):
        connection.execute("INSERT INTO markers VALUES (1)")
        error = sqlite_error(code)
        errors.append(error)
        raise error
    with pytest.raises(sqlite3.OperationalError) as raised:
        repository._write(operation)
    assert raised.value is errors[-1]
    assert len(errors) == 3
    assert sleeps == [0.05, 0.1]
    with closing(repository._connect()) as connection:
        assert connection.execute("SELECT COUNT(*) FROM markers").fetchone()[0] == 0


@pytest.mark.parametrize("code", [None, sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_READONLY,
                                  sqlite3.SQLITE_FULL, sqlite3.SQLITE_IOERR, sqlite3.SQLITE_CANTOPEN])
def test_non_contention_errors_are_not_retried(repository, monkeypatch, code):
    calls = []
    monkeypatch.setattr(run_repository.time, "sleep", lambda _: pytest.fail("non-contention error retried"))
    error = sqlite_error(code)
    def operation(connection):
        calls.append(connection)
        raise error
    with pytest.raises(sqlite3.OperationalError) as raised:
        repository._write(operation)
    assert raised.value is error
    assert len(calls) == 1


def test_connection_lock_failure_is_retried(repository, monkeypatch):
    connect = repository._connect
    attempts = []
    def transient_connect():
        attempts.append(1)
        if len(attempts) < 3:
            raise sqlite_error(sqlite3.SQLITE_BUSY)
        return connect()
    monkeypatch.setattr(repository, "_connect", transient_connect)
    monkeypatch.setattr(run_repository.time, "sleep", lambda _: None)
    assert repository._write(lambda connection: connection.execute("SELECT 1").fetchone()[0]) == 1
    assert len(attempts) == 3


def test_real_writer_lock_released_between_attempts(repository, monkeypatch):
    repository.save(sample_run(status="running"))
    with closing(repository._connect()) as blocker:
        blocker.execute("BEGIN IMMEDIATE")
        delays = []
        def release(delay):
            delays.append(delay)
            blocker.rollback()
        monkeypatch.setattr(run_repository.time, "sleep", release)
        repository.save(sample_run(status="completed"))
    assert delays == [0.05]
    assert repository.get("run_persisted")["status"] == "completed"


def test_real_commit_lock_failure_rolls_back_before_retry(repository, monkeypatch):
    repository.save(sample_run(status="running"))
    with closing(repository._connect()) as reader:
        reader.execute("BEGIN")
        reader.execute("SELECT * FROM assessment_runs").fetchall()
        delays = []
        def release(delay):
            delays.append(delay)
            reader.rollback()
        monkeypatch.setattr(run_repository.time, "sleep", release)
        repository.save(sample_run(status="completed"))
    assert delays == [0.05]
    assert repository.get("run_persisted")["status"] == "completed"


def test_real_persistent_lock_preserves_last_saved_state(repository, monkeypatch):
    repository.save(sample_run(status="running"))
    with closing(repository._connect()) as blocker:
        blocker.execute("BEGIN IMMEDIATE")
        delays = []
        monkeypatch.setattr(run_repository.time, "sleep", delays.append)
        with pytest.raises(sqlite3.OperationalError) as raised:
            repository.save(sample_run(status="completed"))
        assert raised.value.sqlite_errorcode == sqlite3.SQLITE_BUSY
        assert delays == [0.05, 0.1]
        blocker.rollback()
    assert repository.get("run_persisted")["status"] == "running"
