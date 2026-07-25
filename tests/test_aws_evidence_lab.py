# Tests for the AWS evidence lab harness.
from __future__ import annotations

import json
import subprocess

import pytest

from scripts import aws_evidence_lab, run_assessment_snapshot


def test_aws_evidence_lab_catalog_lists_expected_scenarios() -> None:
    catalog = aws_evidence_lab.load_catalog()
    summary = aws_evidence_lab.summarize_catalog(catalog)

    scenario_ids = {item["id"] for item in summary["scenarios"]}

    assert "public-exposure" in scenario_ids
    assert "clean-baseline" in scenario_ids
    assert "sigi-full-spectrum" in scenario_ids
    public = next(
        item for item in summary["scenarios"] if item["id"] == "public-exposure"
    )
    assert {"NET-001", "DATA-001"}.issubset(set(public["expected_controls"]))


def test_assessment_snapshot_runner_supports_aws() -> None:
    assert "aws" in run_assessment_snapshot.SUPPORTED_COLLECTORS


def test_cli_login_credentials_are_exposed_to_aws_sdk(monkeypatch) -> None:
    def fake_run(command, **kwargs):  # noqa: ANN001 - mirrors subprocess.run
        assert command[-3:] == ["cris-sme", "--format", "process"]
        return subprocess.CompletedProcess(
            command,
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

    monkeypatch.setattr(aws_evidence_lab.subprocess, "run", fake_run)
    env = {"AWS_PROFILE": "cris-sme"}

    aws_evidence_lab.hydrate_aws_sdk_credentials(env)

    assert env["AWS_ACCESS_KEY_ID"] == "temporary-key"
    assert env["AWS_SECRET_ACCESS_KEY"] == "temporary-secret"
    assert env["AWS_SESSION_TOKEN"] == "temporary-token"


def test_public_exposure_template_creates_open_rules_without_instances() -> None:
    template = aws_evidence_lab.public_exposure_template()
    resources = template["Resources"]

    assert "OpenAdminSecurityGroup" in resources
    assert "PublicLabBucket" in resources
    assert not any(
        resource["Type"] == "AWS::EC2::Instance"
        for resource in resources.values()
    )

    ingress = resources["OpenAdminSecurityGroup"]["Properties"]["SecurityGroupIngress"]
    assert {
        (rule["FromPort"], rule["ToPort"], rule["CidrIp"])
        for rule in ingress
    } == {
        (22, 22, "0.0.0.0/0"),
        (3389, 3389, "0.0.0.0/0"),
    }

    public_block = resources["PublicLabBucket"]["Properties"][
        "PublicAccessBlockConfiguration"
    ]
    assert public_block["BlockPublicPolicy"] is False


def test_clean_baseline_template_blocks_public_s3_access() -> None:
    template = aws_evidence_lab.clean_baseline_template()
    resources = template["Resources"]

    assert "PrivateBucket" in resources
    public_block = resources["PrivateBucket"]["Properties"][
        "PublicAccessBlockConfiguration"
    ]

    assert public_block["BlockPublicAcls"] is True
    assert public_block["BlockPublicPolicy"] is True
    assert "PrivateOnlySecurityGroup" in resources


def test_sigi_full_spectrum_template_covers_aws_evidence_domains() -> None:
    resources = aws_evidence_lab.sigi_full_spectrum_template()["Resources"]
    resource_types = {resource["Type"] for resource in resources.values()}

    assert {
        "AWS::EC2::Instance",
        "AWS::EC2::Volume",
        "AWS::S3::Bucket",
        "AWS::RDS::DBInstance",
        "AWS::SecretsManager::Secret",
        "AWS::CloudTrail::Trail",
        "AWS::CloudWatch::Alarm",
        "AWS::SSM::Document",
        "AWS::ECS::Cluster",
        "AWS::IoT::Thing",
        "AWS::IoT::Policy",
    }.issubset(resource_types)
    assert resources["WeakWorkload"]["Properties"]["MetadataOptions"]["HttpTokens"] == "optional"
    assert resources["WeakDatabase"]["Properties"]["StorageEncrypted"] is False
    assert resources["WeakDatabase"]["Properties"]["PubliclyAccessible"] is True
    assert resources["ProtectedEvidenceBucket"]["Properties"]["VersioningConfiguration"]["Status"] == "Enabled"
    assert resources["OverbroadIotPolicy"]["Properties"]["PolicyDocument"]["Statement"][0] == {
        "Effect": "Allow",
        "Action": "iot:*",
        "Resource": "*",
    }


def test_non_dry_run_deploy_requires_explicit_confirmation() -> None:
    with pytest.raises(SystemExit, match="without --yes"):
        aws_evidence_lab.main_with_args_for_test(["deploy", "--run-id", "unit"])


def test_dry_run_deploy_prints_commands_without_calling_subprocess(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):  # noqa: ANN001 - mirrors subprocess.run
        calls.append(command)
        raise AssertionError("dry-run must not execute subprocesses")

    monkeypatch.setattr(aws_evidence_lab.subprocess, "run", fake_run)

    result = aws_evidence_lab.main_with_args_for_test(
        ["deploy", "--run-id", "unit", "--dry-run"]
    )

    assert result == 0
    assert calls == []
