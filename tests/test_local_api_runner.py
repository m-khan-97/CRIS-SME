# Tests for the local assessment API runner.
from __future__ import annotations

import json
import subprocess
import time
from io import BytesIO

import pytest

from cris_sme.api.local_runner import (
    LocalAssessmentRunner,
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
    assert env["AZURE_SUBSCRIPTION_ID"] == "sub-123"
    assert env["CRIS_SME_AZURE_TENANT_SCOPE"] == "tenant-456"
    assert env["CRIS_SME_AUTHORIZATION_BASIS"] == "frontend_confirmed_local_authorized_access"


def test_latest_artifacts_reports_known_outputs(tmp_path) -> None:
    report_path = tmp_path / "cris_sme_report.json"
    report_path.write_text("{}", encoding="utf-8")

    artifacts = latest_artifacts(tmp_path)

    assert artifacts["report"]["exists"] is True
    assert artifacts["dashboard"]["exists"] is False
    assert artifacts["report"]["path"].endswith("cris_sme_report.json")


def test_public_exposure_assessment_writes_artifacts(tmp_path, monkeypatch) -> None:
    class FakeScanner:
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


def test_local_api_http_endpoints_return_structured_responses(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("cris_sme.api.local_runner.shutil.which", lambda name: "/usr/bin/az")

    class FakeScanner:
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
