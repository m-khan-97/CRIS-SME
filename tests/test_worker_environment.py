"""Scan children receive only provider-scoped, explicitly supported settings."""
import subprocess
import time

import pytest

from cris_sme.api.local_runner import LocalAssessmentRunner, _aws_login_environment
from cris_sme.api.worker_environment import scan_environment


@pytest.mark.parametrize("provider", ["aws", "azure"])
def test_unrelated_secrets_and_stale_targets_are_not_inherited(provider):
    source = {key: "private" for key in (
        "DATABASE_URL", "GITHUB_TOKEN", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "LD_PRELOAD",
        "PYTHONSTARTUP", "AWS_ACCOUNT_ID", "AZURE_SUBSCRIPTION_ID",
        "CRIS_SME_AWS_ROLE_ARN", "CRIS_SME_AWS_EXTERNAL_ID", "CRIS_SME_AWS_ORGANIZATION_NAME",
        "CRIS_SME_AZURE_ORGANIZATION_NAME", "CRIS_SME_OUTPUT_DIR", "CRIS_SME_RUNNER_EVENTS_PATH",
        "CRIS_SME_AWS_ORGANIZATION_ID", "CRIS_SME_AZURE_ORGANIZATION_ID",
    )}
    assert scan_environment(source, provider) == {}


def test_provider_credentials_and_profile_paths_are_isolated():
    source = {"PATH": "/bin", "HOME": "/home/operator", "AWS_ACCESS_KEY_ID": "aws-key",
              "AWS_PROFILE": "profile", "AWS_WEB_IDENTITY_TOKEN_FILE": "/aws/token",
              "AZURE_CLIENT_SECRET": "azure-secret", "AZURE_CONFIG_DIR": "/azure/cache"}
    aws, azure = (scan_environment(source, provider) for provider in ("aws", "azure"))
    assert aws["AWS_PROFILE"] == "profile"
    assert aws["AWS_WEB_IDENTITY_TOKEN_FILE"] == "/aws/token"
    assert "AZURE_CLIENT_SECRET" not in aws
    assert azure["AZURE_CONFIG_DIR"] == "/azure/cache"
    assert azure["AZURE_CLIENT_SECRET"] == "azure-secret"
    assert "AWS_ACCESS_KEY_ID" not in azure
    assert aws["HOME"] == azure["HOME"] == "/home/operator"


@pytest.mark.parametrize("enabled", ["true", "1", "yes", "on", "false", "0", "invalid", ""])
def test_narrator_key_only_follows_explicit_enablement(enabled):
    result = scan_environment({"CRIS_SME_ENABLE_NARRATOR": enabled, "ANTHROPIC_API_KEY": "key"}, "aws")
    assert ("ANTHROPIC_API_KEY" in result) == (enabled in {"true", "1", "yes", "on"})


@pytest.mark.parametrize("provider", ["aws", "azure"])
def test_actual_scan_command_uses_filtered_environment(tmp_path, monkeypatch, provider):
    monkeypatch.setenv("GITHUB_TOKEN", "unrelated-secret")
    monkeypatch.setenv("AWS_ACCOUNT_ID", "stale-account")
    monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "stale-subscription")
    monkeypatch.setenv("CRIS_SME_AWS_ROLE_ARN", "stale-role")
    monkeypatch.setenv("CRIS_SME_AZURE_ORGANIZATION_NAME", "wrong-customer")
    monkeypatch.setattr("cris_sme.api.local_runner._aws_login_environment", lambda *args: {})
    captured = []
    def command(cmd, **kwargs):
        captured.append(kwargs["env"])
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    runner = LocalAssessmentRunner(output_dir=tmp_path, command_runner=command)
    run = getattr(runner, f"start_{provider}_assessment")({"authorization_confirmed": True})
    deadline = time.monotonic() + 3
    while runner.get_run(run.run_id).status not in {"completed", "failed"}:
        assert time.monotonic() < deadline
        time.sleep(0.01)
    assert run.status == "completed"
    env = captured[0]
    assert env["CRIS_SME_COLLECTOR"] == provider
    assert env["CRIS_SME_OUTPUT_DIR"] == str(tmp_path / "assessments" / run.run_id / "reports")
    assert "GITHUB_TOKEN" not in env
    assert "AWS_ACCOUNT_ID" not in env
    assert "AZURE_SUBSCRIPTION_ID" not in env
    assert "CRIS_SME_AWS_ROLE_ARN" not in env
    assert "CRIS_SME_AZURE_ORGANIZATION_NAME" not in env


def test_empty_export_environment_does_not_fall_back_to_parent(monkeypatch):
    monkeypatch.setenv("AWS_PROFILE", "unwanted-parent-profile")
    def forbidden(*args, **kwargs):
        pytest.fail("Empty explicit environment must not discover parent profile")

    assert _aws_login_environment(forbidden, {}) == {}


def test_cli_credential_export_is_filtered():
    def command(cmd, **kwargs):
        assert kwargs["env"] == {"AWS_PROFILE": "selected"}
        return subprocess.CompletedProcess(cmd, 0, stdout='{"AccessKeyId":"key","SecretAccessKey":"secret"}', stderr="")

    assert _aws_login_environment(command, {"AWS_PROFILE": "selected", "GITHUB_TOKEN": "private"})["AWS_ACCESS_KEY_ID"] == "key"
