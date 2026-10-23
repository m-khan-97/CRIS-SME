"""SQLite persistence for local assessment-run lifecycle state."""
from __future__ import annotations

import sqlite3
import builtins
import time
from contextlib import closing
from pathlib import Path
from typing import Any, Callable, TypeVar


SQLITE_BUSY_TIMEOUT = 0.2
WRITE_RETRY_DELAYS = (0.05, 0.1)
_T = TypeVar("_T")


RUN_COLUMNS = (
    "run_id",
    "collector",
    "status",
    "requested_at",
    "started_at",
    "completed_at",
    "authorization_confirmed",
    "subscription_id",
    "tenant_id",
    "account_id",
    "organization_name",
    "role_arn",
    "output_dir",
    "figure_dir",
    "events_path",
    "returncode",
    "stdout_tail",
    "stderr_tail",
    "error",
)


class SqliteAssessmentRunRepository:
    """Persist assessment process state without adding a database dependency."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def save(self, run: dict[str, Any]) -> None:
        """Insert or update one run atomically."""
        self._ensure_schema()
        values = [_database_value(column, run.get(column)) for column in RUN_COLUMNS]
        placeholders = ", ".join("?" for _ in RUN_COLUMNS)
        columns = ", ".join(RUN_COLUMNS)
        updates = ", ".join(
            f"{column}=excluded.{column}" for column in RUN_COLUMNS if column != "run_id"
        )
        def write(connection: sqlite3.Connection) -> None:
            connection.execute(
                f"""
                INSERT INTO assessment_runs ({columns})
                VALUES ({placeholders})
                ON CONFLICT(run_id) DO UPDATE SET {updates}
                """,
                values,
            )
        self._write(write)

    def get(self, run_id: str) -> dict[str, Any] | None:
        """Return one persisted run, if present."""
        if not self.database_path.is_file():
            return None
        self._ensure_schema()
        with closing(self._connect()) as connection:
            row = connection.execute(
                f"SELECT {', '.join(RUN_COLUMNS)} FROM assessment_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
        return _row_to_dict(row) if row is not None else None

    def list(self, *, limit: int = 100) -> list[dict[str, Any]]:
        """Return newest runs first."""
        if not self.database_path.is_file():
            return []
        self._ensure_schema()
        safe_limit = max(1, min(int(limit), 1000))
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"""
                SELECT {', '.join(RUN_COLUMNS)}
                FROM assessment_runs
                ORDER BY requested_at DESC, run_id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [_row_to_dict(row) for row in rows]

    def completed_outputs(self, *, collector: str | None = None) -> builtins.list[dict[str, Any]]:
        """Index completed output locations without the UI list's row limit."""
        if not self.database_path.is_file():
            return []
        self._ensure_schema()
        collectors = (collector,) if collector is not None else ("aws", "azure")
        placeholders = ", ".join("?" for _ in collectors)
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT run_id, output_dir FROM assessment_runs "
                f"WHERE status = 'completed' AND collector IN ({placeholders}) "
                "ORDER BY requested_at DESC, run_id DESC",
                collectors,
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_interrupted(self, *, completed_at: str) -> int:
        """Fail runs that cannot still be executing after a runner restart."""
        if not self.database_path.is_file():
            return 0
        self._ensure_schema()
        def write(connection: sqlite3.Connection) -> int:
            cursor = connection.execute(
                """
                UPDATE assessment_runs
                SET status = 'failed',
                    completed_at = ?,
                    returncode = -1,
                    error = 'Local runner restarted before the assessment completed.'
                WHERE status IN ('queued', 'running', 'cancelling')
                """,
                (completed_at,),
            )
            return int(cursor.rowcount)
        return self._write(write)

    def _ensure_schema(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        def write(connection: sqlite3.Connection) -> None:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS assessment_runs (
                    run_id TEXT PRIMARY KEY,
                    collector TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requested_at TEXT NOT NULL,
                    started_at TEXT NOT NULL DEFAULT '',
                    completed_at TEXT NOT NULL DEFAULT '',
                    authorization_confirmed INTEGER NOT NULL DEFAULT 0,
                    subscription_id TEXT NOT NULL DEFAULT '',
                    tenant_id TEXT NOT NULL DEFAULT '',
                    account_id TEXT NOT NULL DEFAULT '',
                    organization_name TEXT NOT NULL DEFAULT '',
                    role_arn TEXT NOT NULL DEFAULT '',
                    output_dir TEXT NOT NULL,
                    figure_dir TEXT NOT NULL,
                    events_path TEXT NOT NULL DEFAULT '',
                    returncode INTEGER,
                    stdout_tail TEXT NOT NULL DEFAULT '',
                    stderr_tail TEXT NOT NULL DEFAULT '',
                    error TEXT NOT NULL DEFAULT ''
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_assessment_runs_requested_at
                ON assessment_runs(requested_at DESC)
                """
            )
        self._write(write)

    def _write(self, operation: Callable[[sqlite3.Connection], _T]) -> _T:
        """Retry only lock contention, rolling back and closing each attempt."""
        for attempt in range(len(WRITE_RETRY_DELAYS) + 1):
            try:
                with closing(self._connect()) as connection, connection:
                    connection.execute("BEGIN")
                    return operation(connection)
            except sqlite3.OperationalError as exc:
                code = getattr(exc, "sqlite_errorcode", 0)
                if not isinstance(code, int) or code & 0xFF not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED) or attempt == len(WRITE_RETRY_DELAYS):
                    raise
                time.sleep(WRITE_RETRY_DELAYS[attempt])
        raise AssertionError("Unreachable retry state")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=SQLITE_BUSY_TIMEOUT)
        connection.row_factory = sqlite3.Row
        return connection


def _database_value(column: str, value: Any) -> Any:
    if column == "authorization_confirmed":
        return 1 if bool(value) else 0
    return value


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    result = {column: row[column] for column in RUN_COLUMNS}
    result["authorization_confirmed"] = bool(result["authorization_confirmed"])
    return result
