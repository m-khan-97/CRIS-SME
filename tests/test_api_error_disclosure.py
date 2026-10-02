"""Raw provider and request-dispatch exceptions must not become client messages."""
import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

from cris_sme.api.local_runner import LocalAssessmentRunner, PublicRequestError, create_handler
from tests.test_local_api_runner import _request_json


SECRET = "Bearer confidential-token /private/credentials external-id-secret"


def fail(*args, **kwargs):
    raise RuntimeError(SECRET)


@pytest.mark.parametrize("route,method", [
    ("/api/assessments/aws", "start_aws_assessment"),
    ("/api/assessments/azure", "start_azure_assessment"),
    ("/api/environment/aws/validate-role", "validate_aws_role"),
    ("/api/public-exposure", "assess_public_exposure"),
])
@pytest.mark.parametrize("error_type", [RuntimeError, ValueError, OSError])
def test_post_exception_text_is_not_disclosed(route, method, error_type):
    def failure(*args):
        raise error_type(SECRET)

    handler = create_handler(SimpleNamespace(**{method: failure}))
    body = _request_json(handler, "POST", route, {}, expected_status=500)
    assert body["status"] == "failed"
    assert body["message"] == body["error"]
    assert SECRET not in json.dumps(body)
    assert "confidential-token" not in json.dumps(body)


@pytest.mark.parametrize("route,method", [
    ("/api/environment/aws", "aws_environment"),
    ("/api/environment/azure", "azure_environment"),
    ("/api/assessment-history", "assessment_history"),
])
def test_get_dispatch_errors_are_sanitized(route, method):
    handler = create_handler(SimpleNamespace(**{method: fail}))
    body = _request_json(handler, "GET", route, expected_status=500)
    assert SECRET not in json.dumps(body)
    assert "local runner" in body["message"]


def test_explicit_public_validation_remains_actionable():
    def validate(payload):
        raise PublicRequestError("role_arn is required.")

    handler = create_handler(SimpleNamespace(validate_aws_role=validate))
    result = _request_json(handler, "POST", "/api/environment/aws/validate-role", {}, expected_status=400)
    assert result["message"] == "role_arn is required."


@pytest.mark.parametrize("mode", ["exception", "stderr"])
def test_azure_diagnostics_are_not_disclosed(tmp_path, monkeypatch, mode):
    monkeypatch.setattr("cris_sme.api.local_runner.shutil.which", lambda name: "/usr/bin/az")
    def command(*args, **kwargs):
        if mode == "exception":
            raise subprocess.TimeoutExpired(SECRET, 20, output=SECRET, stderr=SECRET)
        return subprocess.CompletedProcess([], 1, stdout="", stderr=SECRET)

    result = LocalAssessmentRunner(output_dir=tmp_path, command_runner=command).azure_environment()
    assert not result["authenticated"]
    assert SECRET not in json.dumps(result)
    assert "token" not in result["message"]


@pytest.mark.parametrize("stdout", ["not-json", "[]", "{}", '{"user":{}}'])
def test_invalid_azure_output_does_not_claim_authentication(tmp_path, monkeypatch, stdout):
    monkeypatch.setattr("cris_sme.api.local_runner.shutil.which", lambda name: "/usr/bin/az")
    runner = LocalAssessmentRunner(output_dir=tmp_path, command_runner=lambda *args, **kwargs:
                                   subprocess.CompletedProcess([], 0, stdout=stdout, stderr=""))
    result = runner.azure_environment()
    assert result["authenticated"] is False
    assert result["error"] == "azure_cli_invalid_response"


def test_azure_user_response_exports_only_expected_fields(tmp_path, monkeypatch):
    monkeypatch.setattr("cris_sme.api.local_runner.shutil.which", lambda name: "/usr/bin/az")
    stdout = json.dumps({"id": "subscription", "user": {
        "name": "operator", "type": "user", "accessToken": SECRET,
    }})
    runner = LocalAssessmentRunner(output_dir=tmp_path, command_runner=lambda *args, **kwargs:
                                   subprocess.CompletedProcess([], 0, stdout=stdout, stderr=""))
    result = runner.azure_environment()
    assert result["account"]["user"] == {"name": "operator", "type": "user"}
    assert SECRET not in json.dumps(result)


@pytest.mark.parametrize("method", ["aws_environment", "validate_aws_role"])
def test_aws_provider_exception_is_not_disclosed(tmp_path, monkeypatch, method):
    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace())
    monkeypatch.setattr("cris_sme.api.local_runner._aws_boto3_session", fail)
    runner = LocalAssessmentRunner(output_dir=tmp_path)
    result = (runner.aws_environment() if method == "aws_environment"
              else runner.validate_aws_role({"role_arn": "arn:aws:iam::123456789012:role/test"}))
    assert SECRET not in json.dumps(result)
    assert result["message"]


def test_scanner_validation_error_does_not_reflect_input(tmp_path, monkeypatch):
    def scan(*args, **kwargs):
        raise ValueError(SECRET)

    monkeypatch.setattr("cris_sme.api.local_runner.PublicExposureScanner.assess", scan)
    runner = LocalAssessmentRunner(output_dir=tmp_path)
    handler = create_handler(runner)
    body = _request_json(handler, "POST", "/api/public-exposure",
                         {"authorization_confirmed": True, "targets": [SECRET]}, expected_status=400)
    assert SECRET not in json.dumps(body)
    assert "targets" in body["message"]
