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
from urllib.parse import parse_qs, unquote, urlparse

from cris_sme.engine.public_exposure import (
    PublicExposureScanner,
    PublicExposureSettings,
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
    account_id: str = ""
    organization_name: str = ""
    role_arn: str = ""
    external_id: str = ""
    output_dir: str = str(DEFAULT_OUTPUT_DIR)
    figure_dir: str = str(DEFAULT_FIGURE_DIR)
    events_path: str = ""
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
            "account_id": self.account_id,
            "organization_name": self.organization_name,
            "role_arn": self.role_arn,
            "output_dir": self.output_dir,
            "figure_dir": self.figure_dir,
            "returncode": self.returncode,
            "stdout_tail": self.stdout_tail,
            "stderr_tail": self.stderr_tail,
            "error": self.error,
            "runner_events": read_runner_events(Path(self.events_path)) if self.events_path else [],
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
                "status": "cli_missing",
                "azure_cli_available": False,
                "authenticated": False,
                "account": None,
                "error": "azure_cli_not_found",
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
                "status": "error",
                "azure_cli_available": True,
                "authenticated": False,
                "account": None,
                "error": "azure_cli_check_failed",
                "message": f"Azure CLI account check failed: {exc}",
            }
        if completed.returncode != 0:
            return {
                "status": "unauthenticated",
                "azure_cli_available": True,
                "authenticated": False,
                "account": None,
                "error": "azure_cli_unauthenticated",
                "message": _tail(completed.stderr) or "Run az login before starting an assessment.",
            }
        try:
            account = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError:
            account = {}
        return {
            "status": "authenticated",
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

    def aws_environment(self) -> dict[str, Any]:
        """Return AWS credential posture without requiring frontend secrets.

        AWS CLI login profiles are exported into process memory for boto3
        versions that do not yet implement the CLI's login credential provider.
        """
        try:
            import boto3
        except ImportError:
            return {
                "status": "sdk_missing",
                "credentials_available": False,
                "authenticated": False,
                "account": None,
                "error": "boto3_not_installed",
                "message": "The optional 'aws' dependency (boto3) is not installed.",
            }

        try:
            session = _aws_boto3_session(boto3, self.command_runner)
            sts = session.client("sts")
            identity = sts.get_caller_identity()
        except Exception as exc:  # pragma: no cover - exercised through API behavior
            return {
                "status": "credentials_missing",
                "credentials_available": False,
                "authenticated": False,
                "account": None,
                "error": "aws_credentials_unavailable",
                "message": f"AWS credential check failed: {exc}",
            }

        return {
            "status": "authenticated",
            "credentials_available": True,
            "authenticated": True,
            "account": {
                "account_id": str(identity.get("Account", "")),
                "arn": str(identity.get("Arn", "")),
            },
            "message": "AWS credentials are available.",
        }

    def validate_aws_role(self, request: dict[str, Any]) -> dict[str, Any]:
        """Validate a cross-account role can be assumed, without starting a full assessment.

        Research preview: this is a one-off check using the local ("hub")
        credential chain to assume the supplied role; it does not start a
        subprocess or write any output.
        """
        role_arn = str(request.get("role_arn", "")).strip()
        if not role_arn:
            raise ValueError("role_arn is required.")
        external_id = str(request.get("external_id", "")).strip() or None

        try:
            import boto3
        except ImportError:
            return {
                "status": "sdk_missing",
                "verified": False,
                "account_id": None,
                "arn": None,
                "message": "The optional 'aws' dependency (boto3) is not installed.",
            }

        try:
            session = _aws_boto3_session(boto3, self.command_runner)
            sts = session.client("sts")
            assume_kwargs: dict[str, Any] = {
                "RoleArn": role_arn,
                "RoleSessionName": f"cris-sme-role-check-{int(datetime.now(UTC).timestamp())}",
            }
            if external_id:
                assume_kwargs["ExternalId"] = external_id
            response = sts.assume_role(**assume_kwargs)
            credentials = response["Credentials"]
            assumed_sts = boto3.client(
                "sts",
                aws_access_key_id=credentials["AccessKeyId"],
                aws_secret_access_key=credentials["SecretAccessKey"],
                aws_session_token=credentials["SessionToken"],
            )
            identity = assumed_sts.get_caller_identity()
        except Exception as exc:  # pragma: no cover - exercised through API behavior
            return {
                "status": "failed",
                "verified": False,
                "account_id": None,
                "arn": None,
                "message": f"Unable to assume role: {exc}",
            }

        return {
            "status": "verified",
            "verified": True,
            "account_id": str(identity.get("Account", "")),
            "arn": str(identity.get("Arn", "")),
            "message": "Role assumed successfully.",
        }

    def start_aws_assessment(self, request: dict[str, Any]) -> AssessmentRun:
        """Start a local AWS assessment run."""
        if not bool(request.get("authorization_confirmed")):
            raise ValueError("authorization_confirmed must be true before an AWS assessment can run.")

        run_id = f"run_{uuid.uuid4().hex[:16]}"
        run = AssessmentRun(
            run_id=run_id,
            collector="aws",
            authorization_confirmed=True,
            account_id=str(request.get("account_id", "")).strip(),
            organization_name=str(request.get("organization_name", "")).strip(),
            role_arn=str(request.get("role_arn", "")).strip(),
            external_id=str(request.get("external_id", "")).strip(),
            output_dir=str(self.output_dir),
            figure_dir=str(self.figure_dir),
            events_path=str(self.output_dir / ".runs" / f"{run_id}.events.jsonl"),
        )
        with self._lock:
            self._runs[run.run_id] = run
        thread = threading.Thread(target=self._execute_aws_run, args=(run.run_id,), daemon=True)
        thread.start()
        return run

    def start_azure_assessment(self, request: dict[str, Any]) -> AssessmentRun:
        """Start a local Azure assessment run."""
        if not bool(request.get("authorization_confirmed")):
            raise ValueError("authorization_confirmed must be true before an Azure assessment can run.")

        run_id = f"run_{uuid.uuid4().hex[:16]}"
        run = AssessmentRun(
            run_id=run_id,
            collector="azure",
            authorization_confirmed=True,
            subscription_id=str(request.get("subscription_id", "")).strip(),
            tenant_id=str(request.get("tenant_id", "")).strip(),
            organization_name=str(request.get("organization_name", "")).strip(),
            output_dir=str(self.output_dir),
            figure_dir=str(self.figure_dir),
            events_path=str(self.output_dir / ".runs" / f"{run_id}.events.jsonl"),
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

        scanner = PublicExposureScanner(
            settings=PublicExposureSettings(
                scan_common_ports=bool(request.get("scan_common_ports"))
            )
        )
        report = scanner.assess(
            targets,
            authorization_confirmed=bool(request.get("authorization_confirmed")),
        )
        artifacts = write_public_exposure_outputs(report, self.output_dir)
        return {
            "status": "completed",
            "message": "Public exposure assessment completed for authorised targets.",
            **report,
            "artifacts": artifacts,
        }

    def get_run(self, run_id: str) -> AssessmentRun | None:
        with self._lock:
            return self._runs.get(run_id)

    def assessment_history(self) -> list[dict[str, Any]]:
        """Return persisted report snapshots, newest first."""
        return [entry for entry, _ in _report_index(self.output_dir)]

    def assessment_report(self, report_id: str) -> dict[str, Any] | None:
        """Return one persisted report selected by its stable report identifier."""
        for entry, path in _report_index(self.output_dir):
            if entry["report_id"] == report_id:
                try:
                    return json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    return None
        return None

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
        if run.events_path:
            env["CRIS_SME_RUNNER_EVENTS_PATH"] = run.events_path
        if run.subscription_id:
            env["AZURE_SUBSCRIPTION_ID"] = run.subscription_id
        if run.tenant_id:
            env["CRIS_SME_AZURE_TENANT_SCOPE"] = run.tenant_id
        if run.organization_name:
            env["CRIS_SME_AZURE_ORGANIZATION_NAME"] = run.organization_name
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

    def _execute_aws_run(self, run_id: str) -> None:
        run = self.get_run(run_id)
        if run is None:
            return
        self._update_run(run_id, status="running", started_at=_utc_now())
        env = os.environ.copy()
        env["CRIS_SME_COLLECTOR"] = "aws"
        env["CRIS_SME_OUTPUT_DIR"] = str(self.output_dir)
        env["CRIS_SME_FIGURE_DIR"] = str(self.figure_dir)
        env["CRIS_SME_AUTHORIZATION_BASIS"] = "frontend_confirmed_local_authorized_access"
        if run.events_path:
            env["CRIS_SME_RUNNER_EVENTS_PATH"] = run.events_path
        if run.account_id:
            env["AWS_ACCOUNT_ID"] = run.account_id
            env["CRIS_SME_AWS_TENANT_SCOPE"] = run.account_id
        if run.organization_name:
            env["CRIS_SME_AWS_ORGANIZATION_NAME"] = run.organization_name
        if run.role_arn:
            env["CRIS_SME_AWS_ROLE_ARN"] = run.role_arn
        if run.external_id:
            env["CRIS_SME_AWS_EXTERNAL_ID"] = run.external_id
        try:
            env.update(_aws_login_environment(self.command_runner, env))
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


def _aws_login_environment(
    command_runner: CommandRunner,
    env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Return temporary SDK variables for an AWS CLI v2 login profile."""
    source = env or os.environ
    if source.get("AWS_ACCESS_KEY_ID") or not source.get("AWS_PROFILE"):
        return {}
    try:
        completed = command_runner(
            [
                "aws",
                "configure",
                "export-credentials",
                "--profile",
                source["AWS_PROFILE"],
                "--format",
                "process",
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        if completed.returncode != 0:
            return {}
        credentials = json.loads(completed.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, KeyError):
        return {}
    exported = {
        "AWS_ACCESS_KEY_ID": str(credentials.get("AccessKeyId", "")),
        "AWS_SECRET_ACCESS_KEY": str(credentials.get("SecretAccessKey", "")),
    }
    if credentials.get("SessionToken"):
        exported["AWS_SESSION_TOKEN"] = str(credentials["SessionToken"])
    return exported if all(exported.get(key) for key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")) else {}


def _aws_boto3_session(boto3: Any, command_runner: CommandRunner) -> Any:
    credentials = _aws_login_environment(command_runner)
    if not credentials:
        return boto3.Session()
    return boto3.Session(
        aws_access_key_id=credentials["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=credentials["AWS_SECRET_ACCESS_KEY"],
        aws_session_token=credentials.get("AWS_SESSION_TOKEN"),
        region_name=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION"),
    )

def read_runner_events(events_path: Path) -> list[dict[str, Any]]:
    """Read assessment runner progress events written by a running assessment."""
    if not events_path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in events_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def latest_artifacts(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    """Return known artifact paths and existence flags for the latest run."""
    paths = {
        "report": output_dir / "cris_sme_report.json",
        "assessment_summary": output_dir / "cris_sme_assessment_summary.json",
        "sarif_report": output_dir / "cris_sme_report.sarif",
        "ocsf_findings": output_dir / "cris_sme_findings_ocsf.json",
        "findings_csv": output_dir / "cris_sme_findings.csv",
        "assets_csv": output_dir / "cris_sme_assets.csv",
        "evidence_csv": output_dir / "cris_sme_evidence.csv",
        "actions_csv": output_dir / "cris_sme_actions.csv",
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


def _report_index(output_dir: Path) -> list[tuple[dict[str, Any], Path]]:
    """Index the current report and durable history snapshots by run ID."""
    candidates = [output_dir / "cris_sme_report.json"]
    history_dir = output_dir / "history"
    if history_dir.is_dir():
        candidates.extend(history_dir.glob("cris_sme_report_*.json"))
    # Evidence-lab runs use isolated report directories so one organization's
    # artifacts cannot overwrite another's. Include those persisted reports in
    # the same ledger when the standard outputs/reports directory is in use.
    if output_dir.parent.name == "outputs":
        candidates.extend(output_dir.parent.rglob("cris_sme_report.json"))

    indexed: dict[str, tuple[dict[str, Any], Path]] = {}
    for path in candidates:
        if not path.is_file():
            continue
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(report, dict):
            continue

        run_metadata = report.get("run_metadata") or {}
        organizations = report.get("organizations") or []
        organization = organizations[0] if organizations and isinstance(organizations[0], dict) else {}
        generated_at = str(run_metadata.get("generated_at") or report.get("generated_at") or _mtime(path))
        run_id = str(run_metadata.get("run_id") or "").strip()
        report_id = run_id or f"report-{path.stem.removeprefix('cris_sme_report_')}"
        findings = report.get("prioritized_risks") or []
        entry = {
            "report_id": report_id,
            "run_id": run_id,
            "organization_id": str(organization.get("organization_id") or ""),
            "organization_name": str(organization.get("organization_name") or "Unknown organization"),
            "provider": str(organization.get("provider") or report.get("collector_mode") or "unknown"),
            "generated_at": generated_at,
            "overall_risk_score": report.get("overall_risk_score"),
            "finding_count": len(findings) if isinstance(findings, list) else 0,
            "collector_mode": str(report.get("collector_mode") or "unknown"),
        }
        existing = indexed.get(report_id)
        if existing is None or generated_at > existing[0]["generated_at"]:
            indexed[report_id] = (entry, path)

    return sorted(indexed.values(), key=lambda item: item[0]["generated_at"], reverse=True)


def create_handler(runner: LocalAssessmentRunner) -> type[BaseHTTPRequestHandler]:
    """Build a request handler bound to a runner instance."""

    class LocalRunnerHandler(BaseHTTPRequestHandler):
        server_version = "CRISSMELocalRunner/0.1"

        def do_OPTIONS(self) -> None:  # noqa: N802 - stdlib handler API
            self._send_json({"ok": True})

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            parsed_url = urlparse(self.path)
            request_path = parsed_url.path
            if request_path == "/health":
                self._send_json(
                    {
                        "status": "ok",
                        "service": "cris-sme-local-runner",
                        "message": "CRIS-SME local runner is available.",
                    }
                )
                return
            if request_path == "/api/environment/azure":
                self._send_json(runner.azure_environment())
                return
            if request_path == "/api/environment/aws":
                self._send_json(runner.aws_environment())
                return
            if request_path == "/api/artifacts/latest":
                self._send_json({"artifacts": latest_artifacts(runner.output_dir)})
                return
            if request_path == "/api/assessment-history":
                self._send_json({"assessments": runner.assessment_history()})
                return
            if request_path.startswith("/api/assessment-reports/"):
                report_id = unquote(request_path.rsplit("/", 1)[-1])
                report = runner.assessment_report(report_id)
                if report is None:
                    self._send_error("assessment report not found", status=404)
                    return
                self._send_json(report)
                return
            if request_path == "/api/report-artifact":
                artifact_path = parse_qs(parsed_url.query).get("path", [""])[0]
                self._serve_report_artifact(artifact_path)
                return
            if request_path.startswith("/api/assessments/"):
                run_id = request_path.rsplit("/", 1)[-1]
                run = runner.get_run(run_id)
                if run is None:
                    self._send_error("run not found", status=404)
                    return
                self._send_json(run.to_dict())
                return
            if request_path.startswith("/outputs/"):
                self._serve_output_file(request_path[len("/outputs/"):])
                return
            self._send_error("not found", status=404)

        def _serve_output_file(self, relative_path: str) -> None:
            relative_path = relative_path.split("?", 1)[0]
            try:
                target = (runner.output_dir / relative_path).resolve()
                base = runner.output_dir.resolve()
                target.relative_to(base)
            except ValueError:
                self._send_error("not found", status=404)
                return
            if not target.is_file():
                self._send_error("not found", status=404)
                return
            body = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", _content_type_for(target))
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _serve_report_artifact(self, artifact_path: str) -> None:
            outputs_root = (
                runner.output_dir.parent
                if runner.output_dir.parent.name == "outputs"
                else runner.output_dir
            ).resolve()
            target = Path(artifact_path)
            if not target.is_absolute():
                target = (Path.cwd() / target).resolve()
            else:
                target = target.resolve()
            try:
                target.relative_to(outputs_root)
            except ValueError:
                self._send_error("not found", status=404)
                return
            if not target.is_file():
                self._send_error("not found", status=404)
                return
            body = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", _content_type_for(target))
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
            if self.path == "/api/assessments/azure":
                self._start_assessment(runner.start_azure_assessment)
                return
            if self.path == "/api/assessments/aws":
                self._start_assessment(runner.start_aws_assessment)
                return
            if self.path == "/api/environment/aws/validate-role":
                try:
                    payload = self._read_json()
                    result = runner.validate_aws_role(payload)
                except ValueError as exc:
                    self._send_error(str(exc), status=400)
                    return
                except Exception as exc:  # pragma: no cover - defensive runtime guard
                    self._send_error(str(exc), status=500)
                    return
                self._send_json(result, status=200)
                return
            if self.path == "/api/public-exposure":
                try:
                    payload = self._read_json()
                    report = runner.assess_public_exposure(payload)
                except ValueError as exc:
                    self._send_error(str(exc), status=400)
                    return
                except Exception as exc:  # pragma: no cover - defensive runtime guard
                    self._send_error(str(exc), status=500)
                    return
                self._send_json(report, status=200)
                return
            self._send_error("not found", status=404)

        def _start_assessment(
            self,
            start_fn: Callable[[dict[str, Any]], AssessmentRun],
        ) -> None:
            try:
                payload = self._read_json()
                run = start_fn(payload)
            except ValueError as exc:
                self._send_error(str(exc), status=400)
                return
            except Exception as exc:  # pragma: no cover - defensive runtime guard
                self._send_error(str(exc), status=500)
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

        def _send_error(self, message: str, *, status: int) -> None:
            self._send_json(
                {
                    "status": "failed",
                    "message": message,
                    "error": message,
                },
                status=status,
            )

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


_CONTENT_TYPES = {
    ".json": "application/json",
    ".html": "text/html; charset=utf-8",
    ".csv": "text/csv",
    ".sarif": "application/json",
    ".txt": "text/plain; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}


def _content_type_for(path: Path) -> str:
    return _CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")


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
