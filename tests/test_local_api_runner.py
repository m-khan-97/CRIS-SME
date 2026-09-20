# Tests for the local assessment API runner.
from __future__ import annotations

import json
import subprocess
import time
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import pytest

from cris_sme.api.local_runner import (
    LocalAssessmentRunner,
    _aws_login_environment,
    create_handler,
    latest_artifacts,
)


def test_azure_environment_reports_authenticated_cli(monkeypatch) -> None:
    monkeypatch.setattr("cris_sme.api.local_runner.shutil.which", lambda name: "/usr/bin/az")

    def fake_run(cmd, **kwargs) -> subprocess.CompletedProcess[str]:
        assert cmd[:3] == ["az", "account", "show"]
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout=json.dumps(
                {
                    "id": "sub-123",
                    "name": "Demo Subscription",
                    "tenantId": "tenant-456",
                    "user": {"name": "reviewer@example.com"},
                }
            ),
            stderr="",
        )

    runner = LocalAssessmentRunner(command_runner=fake_run)

    result = runner.azure_environment()

    assert result["status"] == "authenticated"
    assert result["azure_cli_available"] is True
    assert result["authenticated"] is True
    assert result["account"]["subscription_id"] == "sub-123"
    assert result["account"]["tenant_id"] == "tenant-456"


def test_start_azure_assessment_requires_authorization() -> None:
    runner = LocalAssessmentRunner()

    with pytest.raises(ValueError, match="authorization_confirmed"):
        runner.start_azure_assessment({"authorization_confirmed": False})


def test_aws_cli_login_credentials_are_exported_for_sdk() -> None:
    def fake_run(cmd, **kwargs) -> subprocess.CompletedProcess[str]:
        assert cmd == [
            "aws",
            "configure",
            "export-credentials",
            "--profile",
            "cris-sme",
            "--format",
            "process",
        ]
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout=json.dumps(
                {
                    "AccessKeyId": "temporary-key",
                    "SecretAccessKey": "temporary-secret",
                    "SessionToken": "temporary-token",
                }
            ),
            stderr="",
        )

    exported = _aws_login_environment(fake_run, {"AWS_PROFILE": "cris-sme"})

    assert exported == {
        "AWS_ACCESS_KEY_ID": "temporary-key",
        "AWS_SECRET_ACCESS_KEY": "temporary-secret",
        "AWS_SESSION_TOKEN": "temporary-token",
    }


def test_start_azure_assessment_runs_collector_with_expected_env(tmp_path) -> None:
    calls: list[dict] = []

    def fake_run(cmd, **kwargs) -> subprocess.CompletedProcess[str]:
        calls.append({"cmd": cmd, "env": kwargs.get("env", {})})
        return subprocess.CompletedProcess(cmd, 0, stdout='{"ok": true}', stderr="")

    runner = LocalAssessmentRunner(
        output_dir=tmp_path / "reports",
        figure_dir=tmp_path / "figures",
        command_runner=fake_run,
    )

    run = runner.start_azure_assessment(
        {
            "authorization_confirmed": True,
            "organization_name": "Example Azure Ltd",
            "subscription_id": "sub-123",
            "tenant_id": "tenant-456",
        }
    )

    deadline = time.time() + 2
    while runner.get_run(run.run_id).status != "completed" and time.time() < deadline:
        time.sleep(0.01)

    completed = runner.get_run(run.run_id)

    assert completed is not None
    assert completed.status == "completed"
    assert calls
    env = calls[0]["env"]
    assert env["CRIS_SME_COLLECTOR"] == "azure"
    assert env["CRIS_SME_AZURE_ORGANIZATION_NAME"] == "Example Azure Ltd"
    assert env["AZURE_SUBSCRIPTION_ID"] == "sub-123"
    assert env["CRIS_SME_AZURE_TENANT_SCOPE"] == "tenant-456"
    assert env["CRIS_SME_AUTHORIZATION_BASIS"] == "frontend_confirmed_local_authorized_access"


def test_start_aws_assessment_passes_organization_name_to_collector(tmp_path) -> None:
    calls: list[dict] = []

    def fake_run(cmd, **kwargs) -> subprocess.CompletedProcess[str]:
        calls.append({"cmd": cmd, "env": kwargs.get("env", {})})
        return subprocess.CompletedProcess(cmd, 0, stdout='{"ok": true}', stderr="")

    runner = LocalAssessmentRunner(
        output_dir=tmp_path / "reports",
        figure_dir=tmp_path / "figures",
        command_runner=fake_run,
    )
    run = runner.start_aws_assessment(
        {
            "authorization_confirmed": True,
            "organization_name": "Example AWS Ltd",
            "account_id": "111111111111",
        }
    )

    deadline = time.time() + 2
    while runner.get_run(run.run_id).status != "completed" and time.time() < deadline:
        time.sleep(0.01)

    completed = runner.get_run(run.run_id)
    assert completed is not None
    assert completed.organization_name == "Example AWS Ltd"
    assert calls[0]["env"]["CRIS_SME_AWS_ORGANIZATION_NAME"] == "Example AWS Ltd"
    assert calls[0]["env"]["AWS_ACCOUNT_ID"] == "111111111111"


def test_start_azure_assessment_sets_runner_events_path_and_exposes_events(tmp_path) -> None:
    calls: list[dict] = []

    def fake_run(cmd, **kwargs) -> subprocess.CompletedProcess[str]:
        calls.append({"cmd": cmd, "env": kwargs.get("env", {})})
        events_path = kwargs["env"]["CRIS_SME_RUNNER_EVENTS_PATH"]
        Path(events_path).parent.mkdir(parents=True, exist_ok=True)
        Path(events_path).write_text(
            json.dumps(
                {
                    "sequence": 1,
                    "phase": "collect_evidence",
                    "status": "started",
                    "message": "Collecting provider-normalized evidence profiles.",
                    "generated_at": "2026-05-13T00:00:00Z",
                    "detail": {},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(cmd, 0, stdout='{"ok": true}', stderr="")

    runner = LocalAssessmentRunner(
        output_dir=tmp_path / "reports",
        figure_dir=tmp_path / "figures",
        command_runner=fake_run,
    )

    run = runner.start_azure_assessment({"authorization_confirmed": True})

    deadline = time.time() + 2
    while runner.get_run(run.run_id).status != "completed" and time.time() < deadline:
        time.sleep(0.01)

    env = calls[0]["env"]
    assert env["CRIS_SME_RUNNER_EVENTS_PATH"].endswith(f"{run.run_id}.events.jsonl")

    completed = runner.get_run(run.run_id)
    assert completed is not None
    events = completed.to_dict()["runner_events"]
    assert events == [
        {
            "sequence": 1,
            "phase": "collect_evidence",
            "status": "started",
            "message": "Collecting provider-normalized evidence profiles.",
            "generated_at": "2026-05-13T00:00:00Z",
            "detail": {},
        }
    ]


def test_assessment_run_survives_runner_restart(tmp_path) -> None:
    def fake_run(cmd, **kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    output_dir = tmp_path / "reports"
    first_runner = LocalAssessmentRunner(output_dir=output_dir, command_runner=fake_run)
    run = first_runner.start_azure_assessment(
        {
            "authorization_confirmed": True,
            "organization_name": "Persistent Example Ltd",
        }
    )

    deadline = time.time() + 2
    while first_runner.get_run(run.run_id).status != "completed" and time.time() < deadline:
        time.sleep(0.01)

    restarted_runner = LocalAssessmentRunner(output_dir=output_dir, command_runner=fake_run)
    restored = restarted_runner.get_run(run.run_id)

    assert restored is not None
    assert restored.status == "completed"
    assert restored.organization_name == "Persistent Example Ltd"
    assert restarted_runner.assessment_runs()[0]["run_id"] == run.run_id


def test_runner_restart_marks_incomplete_persisted_run_failed(tmp_path) -> None:
    output_dir = tmp_path / "reports"
    database_path = output_dir / ".runs" / "assessment_runs.sqlite3"

    from cris_sme.api.run_repository import SqliteAssessmentRunRepository

    repository = SqliteAssessmentRunRepository(database_path)
    repository.save(
        {
            "run_id": "run_interrupted",
            "collector": "azure",
            "status": "running",
            "requested_at": "2026-09-20T10:00:00Z",
            "started_at": "2026-09-20T10:00:01Z",
            "completed_at": "",
            "authorization_confirmed": True,
            "subscription_id": "sub-123",
            "tenant_id": "tenant-456",
            "account_id": "",
            "organization_name": "Interrupted Ltd",
            "role_arn": "",
            "output_dir": str(output_dir),
            "figure_dir": str(tmp_path / "figures"),
            "events_path": "",
            "returncode": None,
            "stdout_tail": "",
            "stderr_tail": "",
            "error": "",
        }
    )

    restarted_runner = LocalAssessmentRunner(
        output_dir=output_dir,
        database_path=database_path,
    )
    restored = restarted_runner.get_run("run_interrupted")

    assert restored is not None
    assert restored.status == "failed"
    assert restored.returncode == -1
    assert "restarted" in restored.error


def test_latest_artifacts_reports_known_outputs(tmp_path) -> None:
    report_path = tmp_path / "cris_sme_report.json"
    report_path.write_text("{}", encoding="utf-8")

    artifacts = latest_artifacts(tmp_path)

    assert artifacts["report"]["exists"] is True
    assert artifacts["assessment_summary"]["exists"] is False
    assert artifacts["assessment_summary"]["path"].endswith(
        "cris_sme_assessment_summary.json"
    )
    assert artifacts["dashboard"]["exists"] is False
    assert artifacts["report"]["path"].endswith("cris_sme_report.json")


def test_assessment_history_discovers_isolated_organization_reports(tmp_path) -> None:
    output_dir = tmp_path / "outputs" / "reports"
    lab_dir = tmp_path / "outputs" / "evidence-lab" / "sigi" / "reports"
    output_dir.mkdir(parents=True)
    lab_dir.mkdir(parents=True)
    current = _sample_report("run_current", "Current Tenant", "2026-07-03T13:00:00Z")
    sigi = _sample_report("run_sigi", "SIGI Technologies", "2026-07-03T12:40:00Z")
    (output_dir / "cris_sme_report.json").write_text(json.dumps(current), encoding="utf-8")
    (lab_dir / "cris_sme_report.json").write_text(json.dumps(sigi), encoding="utf-8")

    runner = LocalAssessmentRunner(output_dir=output_dir)

    history = runner.assessment_history()
    assert [entry["organization_name"] for entry in history] == [
        "Current Tenant",
        "SIGI Technologies",
    ]
    assert runner.assessment_report("run_sigi") == sigi


def test_assessment_history_and_scoped_artifact_http_endpoints(tmp_path) -> None:
    output_dir = tmp_path / "outputs" / "reports"
    output_dir.mkdir(parents=True)
    report = _sample_report("run_sigi", "SIGI Technologies", "2026-07-03T12:40:00Z")
    report_path = output_dir / "cris_sme_report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    artifact_path = output_dir / "cris_sme_summary.txt"
    artifact_path.write_text("SIGI executive summary", encoding="utf-8")
    handler = create_handler(LocalAssessmentRunner(output_dir=output_dir))

    history = _request_json(handler, "GET", "/api/assessment-history")
    selected = _request_json(handler, "GET", "/api/assessment-reports/run_sigi")
    artifact = _request_raw(
        handler,
        "GET",
        f"/api/report-artifact?path={quote(str(artifact_path))}",
    )

    assert history["assessments"][0]["organization_name"] == "SIGI Technologies"
    assert selected["run_metadata"]["run_id"] == "run_sigi"
    assert artifact == b"SIGI executive summary"
    _request_raw(
        handler,
        "GET",
        f"/api/report-artifact?path={quote(str(tmp_path / 'secret.txt'))}",
        expected_status=404,
    )


def test_assessment_runs_http_endpoint_returns_persisted_runs(tmp_path) -> None:
    def fake_run(cmd, **kwargs) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    runner = LocalAssessmentRunner(output_dir=tmp_path, command_runner=fake_run)
    run = runner.start_aws_assessment(
        {
            "authorization_confirmed": True,
            "organization_name": "AWS Persistent Ltd",
            "external_id": "not-persisted",
        }
    )
    deadline = time.time() + 2
    while runner.get_run(run.run_id).status != "completed" and time.time() < deadline:
        time.sleep(0.01)

    payload = _request_json(
        create_handler(runner),
        "GET",
        "/api/assessment-runs?limit=10",
    )

    assert payload["runs"][0]["run_id"] == run.run_id
    assert payload["runs"][0]["organization_name"] == "AWS Persistent Ltd"
    assert "external_id" not in payload["runs"][0]


def test_public_exposure_assessment_writes_artifacts(tmp_path, monkeypatch) -> None:
    class FakeScanner:
        def __init__(self, *, settings=None) -> None:
            self.settings = settings

        def assess(self, targets, *, authorization_confirmed):
            assert targets == ["example.com"]
            assert authorization_confirmed is True
            return {
                "assessment_type": "public_exposure",
                "generated_at": "2026-05-13T00:00:00Z",
                "scope_note": "Authorised targets only.",
                "summary": {"target_count": 1, "finding_count": 0},
                "targets": [],
                "findings": [],
            }

    monkeypatch.setattr("cris_sme.api.local_runner.PublicExposureScanner", FakeScanner)
    runner = LocalAssessmentRunner(output_dir=tmp_path)

    report = runner.assess_public_exposure(
        {
            "targets": "example.com",
            "authorization_confirmed": True,
        }
    )

    assert report["status"] == "completed"
    assert report["summary"]["target_count"] == 1
    assert (tmp_path / "cris_sme_public_exposure.json").exists()
    assert report["artifacts"]["json"].endswith("cris_sme_public_exposure.json")


def test_public_exposure_assessment_passes_scan_common_ports_through(tmp_path, monkeypatch) -> None:
    captured_settings = {}

    class FakeScanner:
        def __init__(self, *, settings=None) -> None:
            captured_settings["settings"] = settings

        def assess(self, targets, *, authorization_confirmed):
            _ = targets, authorization_confirmed
            return {
                "assessment_type": "public_exposure",
                "generated_at": "2026-05-13T00:00:00Z",
                "scope_note": "Authorised targets only.",
                "summary": {"target_count": 1, "finding_count": 0},
                "targets": [],
                "findings": [],
            }

    monkeypatch.setattr("cris_sme.api.local_runner.PublicExposureScanner", FakeScanner)
    runner = LocalAssessmentRunner(output_dir=tmp_path)

    runner.assess_public_exposure(
        {
            "targets": "example.com",
            "authorization_confirmed": True,
            "scan_common_ports": True,
        }
    )

    assert captured_settings["settings"].scan_common_ports is True


def test_public_exposure_assessment_defaults_scan_common_ports_off(tmp_path, monkeypatch) -> None:
    captured_settings = {}

    class FakeScanner:
        def __init__(self, *, settings=None) -> None:
            captured_settings["settings"] = settings

        def assess(self, targets, *, authorization_confirmed):
            _ = targets, authorization_confirmed
            return {
                "assessment_type": "public_exposure",
                "generated_at": "2026-05-13T00:00:00Z",
                "scope_note": "Authorised targets only.",
                "summary": {"target_count": 1, "finding_count": 0},
                "targets": [],
                "findings": [],
            }

    monkeypatch.setattr("cris_sme.api.local_runner.PublicExposureScanner", FakeScanner)
    runner = LocalAssessmentRunner(output_dir=tmp_path)

    runner.assess_public_exposure(
        {"targets": "example.com", "authorization_confirmed": True}
    )

    assert captured_settings["settings"].scan_common_ports is False


def test_local_api_http_endpoints_return_structured_responses(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("cris_sme.api.local_runner.shutil.which", lambda name: "/usr/bin/az")

    class FakeScanner:
        def __init__(self, *, settings=None) -> None:
            self.settings = settings

        def assess(self, targets, *, authorization_confirmed):
            assert authorization_confirmed is True
            return {
                "assessment_type": "public_exposure",
                "generated_at": "2026-05-13T00:00:00Z",
                "scope_note": "Authorised targets only.",
                "summary": {"target_count": len(targets), "finding_count": 0},
                "targets": [],
                "findings": [],
            }

    def fake_run(cmd, **kwargs) -> subprocess.CompletedProcess[str]:
        if cmd[:3] == ["az", "account", "show"]:
            return subprocess.CompletedProcess(
                cmd,
                0,
                stdout=json.dumps(
                    {
                        "id": "sub-123",
                        "name": "Demo Subscription",
                        "tenantId": "tenant-456",
                    }
                ),
                stderr="",
            )
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr("cris_sme.api.local_runner.PublicExposureScanner", FakeScanner)
    runner = LocalAssessmentRunner(output_dir=tmp_path, command_runner=fake_run)
    handler = create_handler(runner)

    environment = _request_json(handler, "GET", "/api/environment/azure")
    assert environment["status"] == "authenticated"
    assert environment["account"]["subscription_id"] == "sub-123"

    public_exposure = _request_json(
        handler,
        "POST",
        "/api/public-exposure",
        {"targets": "example.com", "authorization_confirmed": True},
    )
    assert public_exposure["status"] == "completed"
    assert public_exposure["message"].startswith("Public exposure assessment completed")

    azure_run = _request_json(
        handler,
        "POST",
        "/api/assessments/azure",
        {"authorization_confirmed": True, "subscription_id": "sub-123"},
        expected_status=202,
    )
    assert azure_run["status"] in {"queued", "running", "completed"}
    assert azure_run["artifacts"]["report"]["path"].endswith("cris_sme_report.json")
    assert azure_run["artifacts"]["assessment_summary"]["path"].endswith(
        "cris_sme_assessment_summary.json"
    )


def test_local_api_serves_output_artifacts_with_path_traversal_protection(tmp_path) -> None:
    (tmp_path / "cris_sme_report.json").write_text('{"ok": true}', encoding="utf-8")
    runner = LocalAssessmentRunner(output_dir=tmp_path)
    handler = create_handler(runner)

    report = _request_json(handler, "GET", "/outputs/cris_sme_report.json")
    assert report == {"ok": True}

    _request_raw(handler, "GET", "/outputs/../secret.json", expected_status=404)
    _request_raw(handler, "GET", "/outputs/does-not-exist.json", expected_status=404)


def test_local_api_returns_structured_validation_errors(tmp_path) -> None:
    runner = LocalAssessmentRunner(output_dir=tmp_path)
    handler = create_handler(runner)

    error_payload = _request_json(
        handler,
        "POST",
        "/api/assessments/azure",
        {"authorization_confirmed": False},
        expected_status=400,
    )
    assert error_payload["status"] == "failed"
    assert "authorization_confirmed" in error_payload["message"]
    assert error_payload["error"] == error_payload["message"]


def _request_json(
    handler_class,
    method: str,
    path: str,
    payload: dict | None = None,
    *,
    expected_status: int = 200,
) -> dict:
    body = json.dumps(payload or {}).encode("utf-8") if method == "POST" else b""
    request_bytes = (
        f"{method} {path} HTTP/1.1\r\n"
        "Host: 127.0.0.1\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Content-Type: application/json\r\n"
        "\r\n"
    ).encode("utf-8") + body
    fake_socket = _FakeSocket(request_bytes)
    handler_class(fake_socket, ("127.0.0.1", 12345), object())
    raw_response = fake_socket.output.getvalue()
    header_bytes, response_body = raw_response.split(b"\r\n\r\n", 1)
    status_line = header_bytes.splitlines()[0].decode("utf-8")
    assert f" {expected_status} " in status_line
    return json.loads(response_body.decode("utf-8"))


def _sample_report(run_id: str, organization_name: str, generated_at: str) -> dict:
    return {
        "generated_at": generated_at,
        "collector_mode": "azure",
        "overall_risk_score": 38.69,
        "prioritized_risks": [{"finding_id": "finding-1"}],
        "organizations": [
            {
                "organization_id": f"org-{run_id}",
                "organization_name": organization_name,
                "provider": "azure",
            }
        ],
        "run_metadata": {"run_id": run_id, "generated_at": generated_at},
    }


def _request_raw(
    handler_class,
    method: str,
    path: str,
    *,
    expected_status: int = 200,
) -> bytes:
    request_bytes = (
        f"{method} {path} HTTP/1.1\r\n"
        "Host: 127.0.0.1\r\n"
        "Content-Length: 0\r\n"
        "\r\n"
    ).encode("utf-8")
    fake_socket = _FakeSocket(request_bytes)
    handler_class(fake_socket, ("127.0.0.1", 12345), object())
    raw_response = fake_socket.output.getvalue()
    header_bytes, response_body = raw_response.split(b"\r\n\r\n", 1)
    status_line = header_bytes.splitlines()[0].decode("utf-8")
    assert f" {expected_status} " in status_line
    return response_body


class _FakeSocket:
    def __init__(self, request_bytes: bytes) -> None:
        self.input = BytesIO(request_bytes)
        self.output = BytesIO()

    def makefile(self, mode: str, *args, **kwargs):
        if "r" in mode:
            return self.input
        return self.output

    def sendall(self, data: bytes) -> None:
        self.output.write(data)
