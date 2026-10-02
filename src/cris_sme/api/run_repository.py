"""SQLite persistence for local assessment-run lifecycle state."""
from __future__ import annotations

import sqlite3
import builtins
from pathlib import Path
from typing import Any


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
        with self._connect() as connection:
            connection.execute(
                f"""
                INSERT INTO assessment_runs ({columns})
                VALUES ({placeholders})
                ON CONFLICT(run_id) DO UPDATE SET {updates}
                """,
                values,
            )

    def get(self, run_id: str) -> dict[str, Any] | None:
        """Return one persisted run, if present."""
        if not self.database_path.is_file():
            return None
        self._ensure_schema()
        with self._connect() as connection:
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
        with self._connect() as connection:
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
        with self._connect() as connection:
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
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE assessment_runs
                SET status = 'failed',
                    completed_at = ?,
                    returncode = -1,
                    error = 'Local runner restarted before the assessment completed.'
                WHERE status IN ('queued', 'running')
                """,
                (completed_at,),
            )
            return int(cursor.rowcount)

    def _ensure_schema(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
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

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
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
