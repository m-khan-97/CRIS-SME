# Tests for the local assessment API runner.
from __future__ import annotations

import json
import subprocess
import time

import pytest

from cris_sme.api.local_runner import LocalAssessmentRunner, latest_artifacts


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

    assert report["summary"]["target_count"] == 1
    assert (tmp_path / "cris_sme_public_exposure.json").exists()
    assert report["artifacts"]["json"].endswith("cris_sme_public_exposure.json")
