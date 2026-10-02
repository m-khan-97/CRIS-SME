# Local HTTP API runner for frontend-driven CRIS-SME assessments.
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, unquote, urlparse

from cris_sme.api.run_repository import SqliteAssessmentRunRepository
from cris_sme.api.state_ownership import own_state
from cris_sme.api.public_progress import read_public_events
from cris_sme.api.worker_environment import scan_environment
from cris_sme.api.request_validation import (
    PublicRequestError, require_authorization, boolean_option, azure_inputs, aws_inputs, public_targets,
)
from cris_sme.api.artifact_access import (
    ArtifactTooLarge, FIGURE_FILES, MAX_REPORT_BYTES, is_report_export, read_regular_file,
)
from cris_sme.api.request_limits import BoundedHTTPServer, DEFAULT_MAX_CONNECTIONS, HeaderDeadlineReader
from cris_sme.api.browser_policy import (
    BrowserRequestPolicy, DEFAULT_ALLOWED_HOSTS, DEFAULT_ALLOWED_ORIGINS,
)
from cris_sme.engine.public_exposure import (
    PublicExposureScanner,
    PublicExposureSettings,
    write_public_exposure_outputs,
)


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
DEFAULT_OUTPUT_DIR = Path("outputs/reports")
DEFAULT_FIGURE_DIR = Path("outputs/figures")
DEFAULT_DATABASE_NAME = "assessment_runs.sqlite3"
MAX_REQUEST_BODY_BYTES = 64 * 1024
DEFAULT_REQUEST_READ_TIMEOUT = 10.0
PUBLIC_EXPOSURE_EXPORTS = frozenset({"cris_sme_public_exposure.json", "cris_sme_public_exposure.md"})

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


class AssessmentBusyError(PublicRequestError):
    """The local runner's shared output namespace is already in use."""

    status = 409


class RequestBodyError(PublicRequestError):
    """A request rejected before invoking a collector or probe."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


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

    @classmethod
    def from_persisted(cls, values: dict[str, Any]) -> AssessmentRun:
        """Restore private run state from the SQLite repository."""
        fields = cls.__dataclass_fields__
        return cls(**{key: value for key, value in values.items() if key in fields})

    def to_persisted(self) -> dict[str, Any]:
        """Return durable run state, deliberately excluding the AWS External ID."""
        values = vars(self).copy()
        values.pop("external_id", None)
        return values

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
            "stdout_tail": "",
            "stderr_tail": "",
            "error": ("Assessment failed. Review private local diagnostics using the run ID."
                      if self.status == "failed" else ""),
            "diagnostics_withheld": True,
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
        database_path: Path | None = None,
        command_runner: CommandRunner = subprocess.run,
    ) -> None:
        self.output_dir = output_dir
        self.figure_dir = figure_dir
        self.command_runner = command_runner
        self.database_path = database_path or output_dir / ".runs" / DEFAULT_DATABASE_NAME
        self._repository = SqliteAssessmentRunRepository(self.database_path)
        self._runs: dict[str, AssessmentRun] = {}
        self._lock = threading.Lock()
        self._scan_slot = threading.BoundedSemaphore(1)
        self._restore_persisted_runs()

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
                env=scan_environment(os.environ, "azure"),
            )
        except Exception:
            return {
                "status": "error",
                "azure_cli_available": True,
                "authenticated": False,
                "account": None,
                "error": "azure_cli_check_failed",
                "message": "Azure CLI account check failed. Check the local Azure CLI configuration and sign-in.",
            }
        if completed.returncode != 0:
            return {
                "status": "unauthenticated",
                "azure_cli_available": True,
                "authenticated": False,
                "account": None,
                "error": "azure_cli_unauthenticated",
                "message": "Azure CLI authentication could not be confirmed. Run az login before starting an assessment.",
            }
        try:
            account = json.loads(completed.stdout or "{}")
            if not isinstance(account, dict) or not account.get("id"):
                raise ValueError("Invalid account response")
        except (ValueError, RecursionError):
            return {
                "status": "error", "azure_cli_available": True, "authenticated": False,
                "account": None, "error": "azure_cli_invalid_response",
                "message": "Azure CLI returned an invalid account response. Check the local CLI configuration.",
            }
        user = account.get("user")
        user = user if isinstance(user, dict) else {}
        return {
            "status": "authenticated",
            "azure_cli_available": True,
            "authenticated": True,
            "account": {
                "subscription_id": str(account.get("id", "")),
                "subscription_name": str(account.get("name", "")),
                "tenant_id": str(account.get("tenantId", "")),
                "user": {key: user[key] for key in ("name", "type") if isinstance(user.get(key), str)},
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
        except Exception:
            return {
                "status": "credentials_missing",
                "credentials_available": False,
                "authenticated": False,
                "account": None,
                "error": "aws_credentials_unavailable",
                "message": "AWS credential check failed. Refresh the configured credentials and verify account access.",
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
        values = aws_inputs(request, require_role=True)
        role_arn = values["role_arn"]
        external_id = values["external_id"] or None

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
        except Exception:
            return {
                "status": "failed",
                "verified": False,
                "account_id": None,
                "arn": None,
                "message": "Unable to assume role. Check credentials, the role trust policy, permissions and external ID.",
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
        require_authorization(request)
        values = aws_inputs(request)

        run_id = f"run_{uuid.uuid4().hex[:16]}"
        run = AssessmentRun(
            run_id=run_id,
            collector="aws",
            authorization_confirmed=True,
            **values,
            output_dir=str(self.output_dir / "assessments" / run_id / "reports"),
            figure_dir=str(self.output_dir / "assessments" / run_id / "figures"),
            events_path=str(self.output_dir / ".runs" / f"{run_id}.events.jsonl"),
        )
        return self._start_scan(run, self._execute_aws_run)

    def start_azure_assessment(self, request: dict[str, Any]) -> AssessmentRun:
        """Start a local Azure assessment run."""
        require_authorization(request)
        values = azure_inputs(request)

        run_id = f"run_{uuid.uuid4().hex[:16]}"
        run = AssessmentRun(
            run_id=run_id,
            collector="azure",
            authorization_confirmed=True,
            **values,
            output_dir=str(self.output_dir / "assessments" / run_id / "reports"),
            figure_dir=str(self.output_dir / "assessments" / run_id / "figures"),
            events_path=str(self.output_dir / ".runs" / f"{run_id}.events.jsonl"),
        )
        return self._start_scan(run, self._execute_azure_run)

    def _acquire_scan(self) -> None:
        if not self._scan_slot.acquire(blocking=False):
            raise AssessmentBusyError("An assessment is already active. Wait for it to finish before starting another.")

    def _start_scan(self, run: AssessmentRun, execute: Callable[[str], None]) -> AssessmentRun:
        self._acquire_scan()
        registered = False
        try:
            self._register_run(run)
            registered = True
            thread = threading.Thread(target=self._execute_scan, args=(run.run_id, execute), daemon=True)
            thread.start()
        except Exception:
            try:
                if registered:
                    self._update_run(run.run_id, status="failed", completed_at=_utc_now(),
                                     returncode=-1, error="Unable to start assessment worker.")
            finally:
                self._scan_slot.release()
            raise
        return run

    def _register_run(self, run: AssessmentRun) -> None:
        # Reserve a fresh namespace; never reuse a directory after an ID collision.
        Path(run.output_dir).parent.mkdir(parents=True, exist_ok=False)
        Path(run.output_dir).mkdir()
        Path(run.figure_dir).mkdir()
        with self._lock:
            self._repository.save(run.to_persisted())
            self._runs[run.run_id] = run

    def _execute_scan(self, run_id: str, execute: Callable[[str], None]) -> None:
        try:
            execute(run_id)
        except Exception:
            self._update_run(run_id, status="failed", completed_at=_utc_now(),
                             returncode=-1, error="Assessment worker failed unexpectedly.")
        finally:
            self._scan_slot.release()

    def assess_public_exposure(self, request: dict[str, Any]) -> dict[str, Any]:
        """Run a scoped public exposure assessment for authorised targets."""
        require_authorization(request)
        targets = public_targets(request)
        scanner = PublicExposureScanner(
            settings=PublicExposureSettings(
                scan_common_ports=boolean_option(request, "scan_common_ports")
            )
        )
        run_id = f"run_{uuid.uuid4().hex[:16]}"
        run = AssessmentRun(
            run_id=run_id, collector="public_exposure", authorization_confirmed=True,
            output_dir=str(self.output_dir / "assessments" / run_id / "reports"),
            figure_dir=str(self.output_dir / "assessments" / run_id / "figures"),
        )
        self._acquire_scan()
        registered = False
        try:
            self._register_run(run)
            registered = True
            self._update_run(run_id, status="running", started_at=_utc_now())
            try:
                report = scanner.assess(targets, authorization_confirmed=True)
            except ValueError:
                raise PublicRequestError("Invalid public-exposure targets. Supply valid hostnames or HTTP(S) URLs.") from None
            report = {**report, "run_id": run_id}
            artifacts = write_public_exposure_outputs(report, Path(run.output_dir))
            self._update_run(run_id, status="completed", completed_at=_utc_now(), returncode=0)
            return {
                "status": "completed",
                "message": "Public exposure assessment completed for authorised targets.",
                **report,
                "artifacts": artifacts,
            }
        except Exception:
            if registered:
                self._update_run(run_id, status="failed", completed_at=_utc_now(),
                                 returncode=-1, error="Public exposure assessment failed.")
            raise
        finally:
            self._scan_slot.release()

    def get_run(self, run_id: str) -> AssessmentRun | None:
        with self._lock:
            run = self._runs.get(run_id)
            if run is not None:
                return run
            persisted = self._repository.get(run_id)
            if persisted is None:
                return None
            run = AssessmentRun.from_persisted(persisted)
            self._runs[run_id] = run
            return run

    def assessment_runs(self, *, limit: int = 100) -> list[dict[str, Any]]:
        """Return durable process-level assessment runs, newest first."""
        return [
            AssessmentRun.from_persisted(values).to_dict()
            for values in self._repository.list(limit=limit)
        ]

    def assessment_history(self) -> list[dict[str, Any]]:
        """Return persisted report snapshots, newest first."""
        return [entry for entry, _ in self.report_index()]

    def completed_output_dirs(self, *, collector: str | None = None) -> list[Path]:
        """Return server-assigned namespaces, defaulting to completed cloud runs."""
        directories = []
        for run in self._repository.completed_outputs(collector=collector):
            run_id = run["run_id"]
            if not re.fullmatch(r"run_[0-9a-f]{16}", run_id):
                continue
            directory = self.output_dir / "assessments" / run_id / "reports"
            if Path(run["output_dir"]).absolute() == directory.absolute():
                directories.append(directory)
        return directories

    def report_index(self) -> list[tuple[dict[str, Any], Path]]:
        return _report_index(self.output_dir, completed_dirs=self.completed_output_dirs())

    def latest_output_dir(self) -> Path:
        """Compatibility alias; never publish a running or failed cloud run."""
        published = {path.parent for _, path in self.report_index()}
        for directory in self.completed_output_dirs():
            if directory in published:
                return directory
        return self.output_dir

    def latest_artifact_listing(self) -> dict[str, Any]:
        artifacts = latest_artifacts(self.latest_output_dir())
        artifacts["public_exposure"] = latest_artifacts(self.latest_public_output_dir())["public_exposure"]
        return artifacts

    def public_output_dirs(self) -> list[Path]:
        """Publish only readable completed public-exposure reports."""
        directories = []
        root = self.output_dir.absolute()
        for directory in self.completed_output_dirs(collector="public_exposure"):
            try:
                relative = (directory / "cris_sme_public_exposure.json").absolute().relative_to(root)
                report = json.loads(read_regular_file(root, relative, max_bytes=MAX_REPORT_BYTES))
                if isinstance(report, dict) and report.get("run_id") == directory.parent.name:
                    directories.append(directory)
            except (OSError, ValueError, UnicodeError, RecursionError):
                continue
        return directories

    def latest_public_output_dir(self) -> Path:
        directories = self.public_output_dirs()
        return directories[0] if directories else self.output_dir

    def assessment_report(self, report_id: str) -> dict[str, Any] | None:
        """Return one persisted report selected by its stable report identifier."""
        for entry, path in self.report_index():
            if entry["report_id"] == report_id:
                try:
                    root = (self.output_dir.parent if self.output_dir.parent.name == "outputs"
                            else self.output_dir).absolute()
                    report = json.loads(read_regular_file(root, path.absolute().relative_to(root),
                                                          max_bytes=MAX_REPORT_BYTES))
                    return report if isinstance(report, dict) else None
                except (OSError, ValueError, UnicodeError, RecursionError):
                    return None
        return None

    def _execute_azure_run(self, run_id: str) -> None:
        run = self.get_run(run_id)
        if run is None:
            return
        self._update_run(run_id, status="running", started_at=_utc_now())
        env = scan_environment(os.environ, "azure")
        env["CRIS_SME_COLLECTOR"] = "azure"
        env["CRIS_SME_OUTPUT_DIR"] = run.output_dir
        env["CRIS_SME_FIGURE_DIR"] = run.figure_dir
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
        env = scan_environment(os.environ, "aws")
        env["CRIS_SME_COLLECTOR"] = "aws"
        env["CRIS_SME_OUTPUT_DIR"] = run.output_dir
        env["CRIS_SME_FIGURE_DIR"] = run.figure_dir
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
            self._repository.save(run.to_persisted())

    def _restore_persisted_runs(self) -> None:
        """Restore durable state and close runs interrupted by a process restart."""
        if not self.database_path.is_file():
            return
        self._repository.mark_interrupted(completed_at=_utc_now())
        for values in self._repository.list(limit=1000):
            run = AssessmentRun.from_persisted(values)
            self._runs[run.run_id] = run


def _aws_login_environment(
    command_runner: CommandRunner,
    env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Return temporary SDK variables for an AWS CLI v2 login profile."""
    source = os.environ if env is None else env
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
            env=scan_environment(source, "aws"),
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
    """Return a safe progress projection, never raw worker diagnostics."""
    return read_public_events(events_path)


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


def _report_index(output_dir: Path, *, completed_dirs: list[Path] | None = None) -> list[tuple[dict[str, Any], Path]]:
    """Index the current report and durable history snapshots by run ID."""
    candidates = [output_dir / "cris_sme_report.json"]
    candidates.extend(directory / "cris_sme_report.json" for directory in (completed_dirs or []))
    history_dir = output_dir / "history"
    if history_dir.is_dir():
        candidates.extend(history_dir.glob("cris_sme_report_*.json"))
    # Evidence-lab runs use isolated report directories so one organization's
    # artifacts cannot overwrite another's. Include those persisted reports in
    # the same ledger when the standard outputs/reports directory is in use.
    if output_dir.parent.name == "outputs":
        candidates.extend(path for path in output_dir.parent.rglob("cris_sme_report.json")
                          if "assessments" not in path.relative_to(output_dir.parent).parts)

    indexed: dict[str, tuple[dict[str, Any], Path]] = {}
    root = (output_dir.parent if output_dir.parent.name == "outputs" else output_dir).absolute()
    for path in candidates:
        try:
            report = json.loads(read_regular_file(root, path.absolute().relative_to(root),
                                                  max_bytes=MAX_REPORT_BYTES))
        except (OSError, ValueError, UnicodeError, RecursionError):
            continue
        if not isinstance(report, dict):
            continue

        run_metadata = report.get("run_metadata") or {}
        organizations = report.get("organizations") or []
        if not isinstance(run_metadata, dict) or not isinstance(organizations, list):
            continue
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


def create_handler(
    runner: LocalAssessmentRunner, *, browser_policy: BrowserRequestPolicy | None = None,
    request_read_timeout: float = DEFAULT_REQUEST_READ_TIMEOUT,
) -> type[BaseHTTPRequestHandler]:
    """Build a request handler bound to a runner instance."""
    policy = browser_policy or BrowserRequestPolicy()
    if not math.isfinite(request_read_timeout) or request_read_timeout <= 0:
        raise ValueError("request read timeout must be finite and greater than zero")

    class LocalRunnerHandler(BaseHTTPRequestHandler):
        server_version = "CRISSMELocalRunner/0.1"

        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(request_read_timeout)
            self.rfile = HeaderDeadlineReader(self.rfile, self.connection, request_read_timeout)

        def handle_one_request(self) -> None:
            self.rfile.start_headers()
            super().handle_one_request()

        def parse_request(self) -> bool:
            try:
                if not super().parse_request():
                    return False
            finally:
                self.rfile.finish_headers()
            rejection = policy.rejection(self.headers)
            self._browser_request_allowed = rejection is None
            if rejection:
                self.close_connection = True
                self._send_error(rejection[1], status=rejection[0])
                return False
            return True

        def _cors_headers(self) -> None:
            self.send_header("Vary", "Origin")
            origin = self.headers.get("Origin")
            if getattr(self, "_browser_request_allowed", False) and origin:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def do_OPTIONS(self) -> None:  # noqa: N802 - stdlib handler API
            self._send_json({"ok": True})

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            try:
                self._dispatch_get()
            except Exception:
                self._send_error("Unable to complete the request. Check the local runner configuration and try again.", status=500)

        def _dispatch_get(self) -> None:
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
                self._send_json({"artifacts": runner.latest_artifact_listing()})
                return
            if request_path == "/api/assessment-history":
                self._send_json({"assessments": runner.assessment_history()})
                return
            if request_path == "/api/assessment-runs":
                query = parse_qs(parsed_url.query)
                try:
                    limit = int(query.get("limit", ["100"])[0])
                except ValueError:
                    self._send_error("limit must be an integer", status=400)
                    return
                self._send_json({"runs": runner.assessment_runs(limit=limit)})
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
                relative = Path(relative_path)
                if not is_report_export(relative):
                    raise ValueError("Not a report export")
                directory = (runner.latest_public_output_dir() if relative.name in
                             PUBLIC_EXPOSURE_EXPORTS else runner.latest_output_dir())
                root = runner.output_dir.absolute()
                body = read_regular_file(root, (directory / relative).absolute().relative_to(root))
            except ArtifactTooLarge as exc:
                self._send_error(str(exc), status=413)
                return
            except (OSError, ValueError):
                self._send_error("not found", status=404)
                return
            self._send_artifact(directory / relative, body)

        def _send_artifact(self, target: Path, body: bytes) -> None:
            self.send_response(200)
            self.send_header("Content-Type", _content_type_for(target))
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self._cors_headers()
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _serve_report_artifact(self, artifact_path: str) -> None:
            outputs_root = (
                runner.output_dir.parent
                if runner.output_dir.parent.name == "outputs"
                else runner.output_dir
            ).absolute()
            try:
                target = Path(artifact_path).absolute()
                parts = target.relative_to(outputs_root).parts if target.is_relative_to(outputs_root) else (target.name,)
                if any(part.startswith(".") for part in parts):
                    raise ValueError("Not a report export")
                directories = {runner.output_dir.absolute()}
                for _, report_path in runner.report_index():
                    parent = report_path.absolute().parent
                    directories.add(parent.parent if parent.name == "history" else parent)
                allowed = any(target.is_relative_to(directory) and
                              is_report_export(target.relative_to(directory))
                              for directory in directories)
                figure_dir = getattr(runner, "figure_dir", None)
                if figure_dir is not None and target.parent == figure_dir.absolute() and target.name in FIGURE_FILES:
                    body = read_regular_file(figure_dir, Path(target.name))
                elif target.name in PUBLIC_EXPOSURE_EXPORTS and target.parent in {
                    directory.absolute() for directory in runner.public_output_dirs()
                }:
                    body = read_regular_file(outputs_root, target.relative_to(outputs_root))
                elif allowed:
                    body = read_regular_file(outputs_root, target.relative_to(outputs_root))
                elif target.name in FIGURE_FILES and any(
                    directory.name == "reports" and target.parent == directory.parent / "figures"
                    for directory in directories
                ):
                    body = read_regular_file(outputs_root, target.relative_to(outputs_root))
                else:
                    raise ValueError("Not a report export")
            except ArtifactTooLarge as exc:
                self._send_error(str(exc), status=413)
                return
            except (OSError, ValueError):
                self._send_error("not found", status=404)
                return
            self._send_artifact(target, body)

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
                except PublicRequestError as exc:
                    self._send_error(str(exc), status=getattr(exc, "status", 400))
                    return
                except Exception:
                    self._send_error("Unable to verify the AWS role. Check the local runner configuration and try again.", status=500)
                    return
                self._send_json(result, status=200)
                return
            if self.path == "/api/public-exposure":
                try:
                    payload = self._read_json()
                    report = runner.assess_public_exposure(payload)
                except PublicRequestError as exc:
                    self._send_error(str(exc), status=getattr(exc, "status", 400))
                    return
                except Exception:
                    self._send_error("Unable to complete the public-exposure assessment. Check the local runner configuration and try again.", status=500)
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
            except PublicRequestError as exc:
                self._send_error(str(exc), status=getattr(exc, "status", 400))
                return
            except Exception:
                self._send_error("Unable to start the assessment. Check the local runner configuration and try again.", status=500)
                return
            self._send_json(run.to_dict(), status=202)

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _read_json(self) -> dict[str, Any]:
            # Reject ambiguous framing before reading bytes or starting work.
            if self.headers.get_all("Transfer-Encoding"):
                raise RequestBodyError("transfer encoding is not supported")
            lengths = self.headers.get_all("Content-Length", [])
            if not lengths:
                raise RequestBodyError("Content-Length is required", status=411)
            if len(lengths) != 1:
                raise RequestBodyError("exactly one Content-Length is required")
            value = lengths[0].strip()
            if not value.isascii() or not value.isdecimal():
                raise RequestBodyError("Content-Length must be a nonnegative decimal integer")
            if len(value) > 16 or int(value) > MAX_REQUEST_BODY_BYTES:
                raise RequestBodyError("request body exceeds 65536 bytes", status=413)
            length = int(value)
            types = self.headers.get_all("Content-Type", [])
            if len(types) != 1 or types[0].split(";", 1)[0].strip().lower() != "application/json":
                raise RequestBodyError("Content-Type must be application/json", status=415)
            raw = self._read_body(length) if length else b"{}"

            def reject_constant(value: str) -> None:
                raise ValueError("non-standard JSON constant")

            try:
                payload = json.loads(raw.decode("utf-8"), parse_constant=reject_constant)
            except (ValueError, RecursionError):
                raise RequestBodyError("request body must be valid UTF-8 JSON") from None
            if not isinstance(payload, dict):
                raise RequestBodyError("request body must be a JSON object")
            return payload

        def _read_body(self, length: int) -> bytes:
            deadline = time.monotonic() + request_read_timeout
            previous_timeout = self.connection.gettimeout()
            body = bytearray()
            try:
                while len(body) < length:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError
                    self.connection.settimeout(remaining)
                    # read1 returns available buffered data or performs one socket read;
                    # read(length) could keep accepting trickled bytes past the deadline.
                    chunk = self.rfile.read1(length - len(body))
                    if not chunk:
                        raise RequestBodyError("request body is incomplete")
                    body.extend(chunk)
                if time.monotonic() > deadline:
                    raise TimeoutError
            except TimeoutError:
                self.close_connection = True
                raise RequestBodyError("request body read deadline exceeded", status=408) from None
            finally:
                self.connection.settimeout(previous_timeout)
            return bytes(body)

        def _send_json(self, payload: dict[str, Any], *, status: int = 200) -> None:
            body = json.dumps(payload, indent=2, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self._cors_headers()
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
    database_path: Path | None = None,
    allowed_hosts: tuple[str, ...] = DEFAULT_ALLOWED_HOSTS,
    allowed_origins: tuple[str, ...] = DEFAULT_ALLOWED_ORIGINS,
    request_read_timeout: float = DEFAULT_REQUEST_READ_TIMEOUT,
    max_connections: int = DEFAULT_MAX_CONNECTIONS,
) -> None:
    """Run the local assessment API server."""
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("port must be an integer between 0 and 65535")
    if isinstance(request_read_timeout, bool) or not math.isfinite(request_read_timeout) or request_read_timeout <= 0:
        raise ValueError("request read timeout must be finite and greater than zero")
    if isinstance(max_connections, bool) or not isinstance(max_connections, int) or max_connections < 1:
        raise ValueError("max connections must be a positive integer")
    policy = BrowserRequestPolicy(allowed_hosts=allowed_hosts, allowed_origins=allowed_origins)
    database_path = database_path or output_dir / ".runs" / DEFAULT_DATABASE_NAME
    with own_state(output_dir, figure_dir, database_path):
        runner = LocalAssessmentRunner(
            output_dir=output_dir,
            figure_dir=figure_dir,
            database_path=database_path,
        )
        server = BoundedHTTPServer((host, port), create_handler(
            runner, browser_policy=policy, request_read_timeout=request_read_timeout,
        ), max_connections=max_connections)
        print(f"CRIS-SME local runner listening on http://{host}:{port}")
        try:
            server.serve_forever()
        finally:
            server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the CRIS-SME local assessment API.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--request-read-timeout", type=float, default=DEFAULT_REQUEST_READ_TIMEOUT,
                        help="Socket idle timeout and separate total header/body deadlines in seconds (default: 10).")
    parser.add_argument("--max-connections", type=int, default=DEFAULT_MAX_CONNECTIONS,
                        help="Maximum simultaneous local API connections (default: 16).")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--figure-dir", default=str(DEFAULT_FIGURE_DIR))
    parser.add_argument("--allowed-host", action="append", help="Allowed hostname (repeatable; replaces defaults).")
    parser.add_argument("--allowed-origin", action="append", help="Allowed browser origin (repeatable; replaces defaults).")
    parser.add_argument(
        "--database-path",
        default="",
        help="SQLite run-state database (default: <output-dir>/.runs/assessment_runs.sqlite3).",
    )
    args = parser.parse_args()
    run_server(
        host=args.host,
        port=args.port,
        output_dir=Path(args.output_dir),
        figure_dir=Path(args.figure_dir),
        database_path=Path(args.database_path) if args.database_path else None,
        allowed_hosts=tuple(args.allowed_host) if args.allowed_host else DEFAULT_ALLOWED_HOSTS,
        allowed_origins=tuple(args.allowed_origin) if args.allowed_origin else DEFAULT_ALLOWED_ORIGINS,
        request_read_timeout=args.request_read_timeout,
        max_connections=args.max_connections,
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
