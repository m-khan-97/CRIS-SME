"""Consent and scope validation precede worker creation and provider access."""
import pytest

from cris_sme.api.local_runner import LocalAssessmentRunner, create_handler
from cris_sme.api.request_validation import PublicRequestError, aws_inputs, azure_inputs, public_targets
from tests.test_local_api_runner import _request_json


@pytest.mark.parametrize("route", ["aws", "azure", "public-exposure"])
@pytest.mark.parametrize("value", [False, None, "false", "true", 0, 1, [], {"yes": True}])
def test_only_boolean_true_authorizes_assessment(tmp_path, route, value):
    runner = LocalAssessmentRunner(output_dir=tmp_path)
    handler = create_handler(runner)
    path = f"/api/assessments/{route}" if route != "public-exposure" else "/api/public-exposure"
    result = _request_json(handler, "POST", path,
                           {"authorization_confirmed": value, "targets": ["example.com"]}, expected_status=400)
    assert "authorization_confirmed" in result["message"]
    assert runner.assessment_runs() == []


@pytest.mark.parametrize("value", [None, "false", "true", 1, []])
def test_port_scan_option_requires_boolean(tmp_path, value):
    handler = create_handler(LocalAssessmentRunner(output_dir=tmp_path))
    result = _request_json(handler, "POST", "/api/public-exposure", {
        "authorization_confirmed": True, "targets": ["example.com"], "scan_common_ports": value,
    }, expected_status=400)
    assert "scan_common_ports" in result["message"]


@pytest.mark.parametrize("inputs", [
    {"account_id": 123456789012}, {"account_id": "123"}, {"account_id": "١" * 12},
    {"role_arn": "arn:aws:sts::111111111111:assumed-role/test/session"},
    {"role_arn": "arn:aws:iam:eu-west-1:111111111111:role/test"},
    {"role_arn": "arn:aws:iam::111111111111:role/test space"},
    {"role_arn": "arn:aws:iam::111111111111:role/" + "a" * 65},
    {"account_id": "222222222222", "role_arn": "arn:aws:iam::111111111111:role/test"},
    {"external_id": "secret"}, {"organization_name": {"name": "SME"}},
    {"organization_name": "name\x00secret"}, {"organization_name": "a" * 257},
    {"external_id": "a", "role_arn": "arn:aws:iam::111111111111:role/test"},
    {"external_id": "bad secret", "role_arn": "arn:aws:iam::111111111111:role/test"},
])
def test_invalid_aws_scope_is_rejected_before_admission(tmp_path, inputs):
    runner = LocalAssessmentRunner(output_dir=tmp_path)
    with pytest.raises(PublicRequestError):
        runner.start_aws_assessment({"authorization_confirmed": True, **inputs})
    assert runner.assessment_runs() == []


@pytest.mark.parametrize("partition", ["aws", "aws-us-gov", "aws-cn"])
def test_valid_iam_role_and_external_id(partition):
    values = aws_inputs({"account_id": "111111111111", "role_arn":
                         f"arn:{partition}:iam::111111111111:role/service-role/read-only",
                         "external_id": "customer-id:1/2", "organization_name": " Example Ltd "})
    assert values["organization_name"] == "Example Ltd"


@pytest.mark.parametrize("field", ["subscription_id", "tenant_id"])
@pytest.mark.parametrize("value", ["sub-123", "a" * 32, None, 1, ["id"]])
def test_invalid_azure_identifier_is_rejected(field, value):
    with pytest.raises(PublicRequestError):
        azure_inputs({field: value})


def test_blank_and_valid_cloud_scope():
    assert aws_inputs({})["account_id"] == ""
    assert azure_inputs({})["subscription_id"] == ""
    value = "ABCDEF01-2345-6789-ABCD-0123456789AB"
    assert azure_inputs({"subscription_id": value})["subscription_id"] == value


@pytest.mark.parametrize("targets", [[], [1], [None], ["example.com"] * 11, ["x" * 2049], ["host\x00"]])
def test_invalid_probe_targets_rejected(targets):
    with pytest.raises(PublicRequestError):
        public_targets({"targets": targets})


def test_target_lines_preserve_strings():
    assert public_targets({"targets": " example.com\n\napi.example.com "}) == ["example.com", "api.example.com"]


def test_role_verification_rejects_invalid_scope_before_sdk(tmp_path, monkeypatch):
    def forbidden(*args):
        pytest.fail("Validation reached the cloud SDK")

    monkeypatch.setattr("cris_sme.api.local_runner._aws_boto3_session", forbidden)
    runner = LocalAssessmentRunner(output_dir=tmp_path)
    with pytest.raises(PublicRequestError):
        runner.validate_aws_role({"role_arn": "invalid-secret-value"})
