# Local HTTP API runner for frontend-driven CRIS-SME assessments.
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from cris_sme.engine.public_exposure import (
    PublicExposureScanner,
    write_public_exposure_outputs,
)


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
DEFAULT_OUTPUT_DIR = Path("outputs/reports")
DEFAULT_FIGURE_DIR = Path("outputs/figures")

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass
class AssessmentRun:
    """Runtime status for one local assessment run."""

    run_id: str
    collector: str
    status: str = "queued"
    requested_at: str = field(default_factory=lambda: _utc_now())
    started_at: str = ""
    completed_at: str = ""
    authorization_confirmed: bool = False
    subscription_id: str = ""
    tenant_id: str = ""
    output_dir: str = str(DEFAULT_OUTPUT_DIR)
    figure_dir: str = str(DEFAULT_FIGURE_DIR)
    returncode: int | None = None
    stdout_tail: str = ""
    stderr_tail: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "collector": self.collector,
            "status": self.status,
            "requested_at": self.requested_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "authorization_confirmed": self.authorization_confirmed,
            "subscription_id": self.subscription_id,
            "tenant_id": self.tenant_id,
            "output_dir": self.output_dir,
            "figure_dir": self.figure_dir,
            "returncode": self.returncode,
            "stdout_tail": self.stdout_tail,
            "stderr_tail": self.stderr_tail,
            "error": self.error,
            "artifacts": latest_artifacts(Path(self.output_dir)),
        }


class LocalAssessmentRunner:
    """Manage local CRIS-SME assessment subprocesses for the API."""

    def __init__(
        self,
        *,
        output_dir: Path = DEFAULT_OUTPUT_DIR,
        figure_dir: Path = DEFAULT_FIGURE_DIR,
        command_runner: CommandRunner = subprocess.run,
    ) -> None:
        self.output_dir = output_dir
        self.figure_dir = figure_dir
        self.command_runner = command_runner
        self._runs: dict[str, AssessmentRun] = {}
        self._lock = threading.Lock()

    def azure_environment(self) -> dict[str, Any]:
        """Return Azure CLI posture without requiring frontend secrets."""
        az_path = shutil.which("az")
        if not az_path:
            return {
                "azure_cli_available": False,
                "authenticated": False,
                "account": None,
                "message": "Azure CLI was not found on this machine.",
            }
        try:
            completed = self.command_runner(
                ["az", "account", "show", "--output", "json"],
                capture_output=True,
                text=True,
                timeout=20,
            )
        except Exception as exc:  # pragma: no cover - exercised through API behavior
            return {
                "azure_cli_available": True,
                "authenticated": False,
                "account": None,
                "message": f"Azure CLI account check failed: {exc}",
            }
        if completed.returncode != 0:
            return {
                "azure_cli_available": True,
                "authenticated": False,
                "account": None,
                "message": _tail(completed.stderr) or "Run az login before starting an assessment.",
            }
        try:
            account = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError:
            account = {}
        return {
            "azure_cli_available": True,
            "authenticated": True,
            "account": {
                "subscription_id": str(account.get("id", "")),
                "subscription_name": str(account.get("name", "")),
                "tenant_id": str(account.get("tenantId", "")),
                "user": account.get("user", {}),
            },
            "message": "Azure CLI is authenticated.",
        }

    def start_azure_assessment(self, request: dict[str, Any]) -> AssessmentRun:
        """Start a local Azure assessment run."""
        if not bool(request.get("authorization_confirmed")):
            raise ValueError("authorization_confirmed must be true before an Azure assessment can run.")

        run = AssessmentRun(
            run_id=f"run_{uuid.uuid4().hex[:16]}",
            collector="azure",
            authorization_confirmed=True,
            subscription_id=str(request.get("subscription_id", "")).strip(),
            tenant_id=str(request.get("tenant_id", "")).strip(),
            output_dir=str(self.output_dir),
            figure_dir=str(self.figure_dir),
        )
        with self._lock:
            self._runs[run.run_id] = run
        thread = threading.Thread(target=self._execute_azure_run, args=(run.run_id,), daemon=True)
        thread.start()
        return run

    def assess_public_exposure(self, request: dict[str, Any]) -> dict[str, Any]:
        """Run a scoped public exposure assessment for authorised targets."""
        raw_targets = request.get("targets", [])
        if isinstance(raw_targets, str):
            targets = [line.strip() for line in raw_targets.splitlines()]
        elif isinstance(raw_targets, list):
            targets = [str(item).strip() for item in raw_targets]
        else:
            raise ValueError("targets must be a list or newline-separated string.")

        scanner = PublicExposureScanner()
        report = scanner.assess(
            targets,
            authorization_confirmed=bool(request.get("authorization_confirmed")),
        )
        artifacts = write_public_exposure_outputs(report, self.output_dir)
        return {**report, "artifacts": artifacts}

    def get_run(self, run_id: str) -> AssessmentRun | None:
        with self._lock:
            return self._runs.get(run_id)

    def _execute_azure_run(self, run_id: str) -> None:
        run = self.get_run(run_id)
        if run is None:
            return
        self._update_run(run_id, status="running", started_at=_utc_now())
        env = os.environ.copy()
        env["CRIS_SME_COLLECTOR"] = "azure"
        env["CRIS_SME_OUTPUT_DIR"] = str(self.output_dir)
        env["CRIS_SME_FIGURE_DIR"] = str(self.figure_dir)
        env["CRIS_SME_AUTHORIZATION_BASIS"] = "frontend_confirmed_local_authorized_access"
        if run.subscription_id:
            env["AZURE_SUBSCRIPTION_ID"] = run.subscription_id
        if run.tenant_id:
            env["CRIS_SME_AZURE_TENANT_SCOPE"] = run.tenant_id
        try:
            completed = self.command_runner(
                [sys.executable, "-m", "cris_sme.main"],
                capture_output=True,
                text=True,
                timeout=900,
                env=env,
            )
            status = "completed" if completed.returncode == 0 else "failed"
            self._update_run(
                run_id,
                status=status,
                completed_at=_utc_now(),
                returncode=completed.returncode,
                stdout_tail=_tail(completed.stdout),
                stderr_tail=_tail(completed.stderr),
                error="" if completed.returncode == 0 else (_tail(completed.stderr) or "Assessment failed."),
            )
        except Exception as exc:  # pragma: no cover - defensive runtime guard
            self._update_run(
                run_id,
                status="failed",
                completed_at=_utc_now(),
                returncode=-1,
                error=str(exc),
            )

    def _update_run(self, run_id: str, **updates: Any) -> None:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return
            for key, value in updates.items():
                setattr(run, key, value)


def latest_artifacts(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Return known artifact paths and existence flags for the latest run."""
    paths = {
        "report": output_dir / "cris_sme_report.json",
        "dashboard": output_dir / "cris_sme_dashboard_payload.json",
        "html_report": output_dir / "report.html",
        "assurance_portal": output_dir / "assurance.html",
        "evidence_room": output_dir / "evidence-room.html",
        "ce_self_assessment": output_dir / "cris_sme_ce_self_assessment.json",
        "ce_review_console": output_dir / "cris_sme_ce_review_console.json",
        "ce_evaluation_metrics": output_dir / "cris_sme_ce_evaluation_metrics.json",
        "public_exposure": output_dir / "cris_sme_public_exposure.json",
    }
    return {
        name: {
            "path": str(path),
            "exists": path.exists(),
            "updated_at": _mtime(path),
        }
        for name, path in paths.items()
    }


def create_handler(runner: LocalAssessmentRunner) -> type[BaseHTTPRequestHandler]:
    """Build a request handler bound to a runner instance."""

    class LocalRunnerHandler(BaseHTTPRequestHandler):
        server_version = "CRISSMELocalRunner/0.1"

        def do_OPTIONS(self) -> None:  # noqa: N802 - stdlib handler API
            self._send_json({"ok": True})

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            if self.path == "/health":
                self._send_json({"status": "ok", "service": "cris-sme-local-runner"})
                return
            if self.path == "/api/environment/azure":
                self._send_json(runner.azure_environment())
                return
            if self.path == "/api/artifacts/latest":
                self._send_json({"artifacts": latest_artifacts(runner.output_dir)})
                return
            if self.path.startswith("/api/assessments/"):
                run_id = self.path.rsplit("/", 1)[-1]
                run = runner.get_run(run_id)
                if run is None:
                    self._send_json({"error": "run not found"}, status=404)
                    return
                self._send_json(run.to_dict())
                return
            self._send_json({"error": "not found"}, status=404)

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
            if self.path != "/api/assessments/azure":
                if self.path == "/api/public-exposure":
                    try:
                        payload = self._read_json()
                        report = runner.assess_public_exposure(payload)
                    except ValueError as exc:
                        self._send_json({"error": str(exc)}, status=400)
                        return
                    except Exception as exc:  # pragma: no cover - defensive runtime guard
                        self._send_json({"error": str(exc)}, status=500)
                        return
                    self._send_json(report, status=200)
                    return
                self._send_json({"error": "not found"}, status=404)
                return
            try:
                payload = self._read_json()
                run = runner.start_azure_assessment(payload)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return
            except Exception as exc:  # pragma: no cover - defensive runtime guard
                self._send_json({"error": str(exc)}, status=500)
                return
            self._send_json(run.to_dict(), status=202)

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            payload = json.loads(raw or "{}")
            if not isinstance(payload, dict):
                raise ValueError("request body must be a JSON object")
            return payload

        def _send_json(self, payload: dict[str, Any], *, status: int = 200) -> None:
            body = json.dumps(payload, indent=2, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(body)

    return LocalRunnerHandler


def run_server(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    figure_dir: Path = DEFAULT_FIGURE_DIR,
) -> None:
    """Run the local assessment API server."""
    runner = LocalAssessmentRunner(output_dir=output_dir, figure_dir=figure_dir)
    server = ThreadingHTTPServer((host, port), create_handler(runner))
    print(f"CRIS-SME local runner listening on http://{host}:{port}")
    server.serve_forever()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the CRIS-SME local assessment API.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--figure-dir", default=str(DEFAULT_FIGURE_DIR))
    args = parser.parse_args()
    run_server(
        host=args.host,
        port=args.port,
        output_dir=Path(args.output_dir),
        figure_dir=Path(args.figure_dir),
    )
    return 0


def _tail(value: str, *, limit: int = 4000) -> str:
    return value[-limit:] if value else ""


def _mtime(path: Path) -> str:
    if not path.exists():
        return ""
    return datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat().replace("+00:00", "Z")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
