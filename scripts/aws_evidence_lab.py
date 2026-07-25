# Repeatable AWS evidence lab harness for CRIS-SME live dataset generation.
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
SCENARIO_FILE = REPO_ROOT / "labs" / "aws-evidence-lab" / "scenarios.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "outputs" / "aws-evidence-lab"


@dataclass(frozen=True)
class AwsLabContext:
    scenario: dict[str, Any]
    run_id: str
    region: str
    stack_name: str
    suffix: str
    tags: dict[str, str]
    dry_run: bool


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deploy, assess, and clean up controlled AWS evidence-lab scenarios.",
    )
    parser.add_argument(
        "action",
        choices=("list", "deploy", "assess", "cleanup", "cycle"),
        help="Action to perform. cycle = deploy, assess, then cleanup.",
    )
    parser.add_argument(
        "--scenario",
        default="public-exposure",
        help="Scenario id from labs/aws-evidence-lab/scenarios.json.",
    )
    parser.add_argument(
        "--region",
        default=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1",
        help="AWS region for lab resources.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Stable run id. Defaults to UTC timestamp.",
    )
    parser.add_argument(
        "--stack-name",
        default=None,
        help="Override CloudFormation stack name. Defaults to cris-lab-{scenario}-{run_id}.",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Root directory for assessment outputs.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print AWS and CRIS commands without executing them.",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="For cycle action, keep lab resources after assessment instead of deleting them.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm creation or deletion of AWS lab resources. Required for non-dry-run deploy, cleanup, and cycle actions.",
    )
    args = parser.parse_args(argv)

    catalog = load_catalog()
    if args.action == "list":
        print(json.dumps(summarize_catalog(catalog), indent=2))
        return 0
    if args.action in {"deploy", "cleanup", "cycle"} and not args.dry_run and not args.yes:
        raise SystemExit(
            "Refusing to create or delete AWS resources without --yes. "
            "Use --dry-run to preview commands."
        )

    scenario = find_scenario(catalog, args.scenario)
    run_id = normalize_run_id(args.run_id or datetime.now(UTC).strftime("%Y%m%d%H%M%S"))
    stack_name = args.stack_name or f"cris-lab-{scenario['id']}-{run_id}"
    context = build_context(
        scenario=scenario,
        run_id=run_id,
        region=args.region,
        stack_name=stack_name,
        dry_run=args.dry_run,
    )

    if args.action == "deploy":
        deploy(context)
    elif args.action == "assess":
        assess(context, Path(args.output_root))
    elif args.action == "cleanup":
        cleanup(context)
    elif args.action == "cycle":
        deploy(context)
        assess(context, Path(args.output_root))
        if not args.keep:
            cleanup(context)

    return 0


def load_catalog(path: Path = SCENARIO_FILE) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("AWS evidence lab catalog must contain at least one scenario.")
    return payload


def summarize_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": catalog.get("version"),
        "scenarios": [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "dataset_source_type": item.get("dataset_source_type"),
                "dataset_use": item.get("dataset_use"),
                "expected_controls": [
                    finding.get("control_id")
                    for finding in item.get("expected_findings", [])
                    if isinstance(finding, dict)
                ],
            }
            for item in catalog.get("scenarios", [])
        ],
    }


def find_scenario(catalog: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    for scenario in catalog.get("scenarios", []):
        if scenario.get("id") == scenario_id:
            return scenario
    valid = ", ".join(str(item.get("id")) for item in catalog.get("scenarios", []))
    raise ValueError(f"Unknown scenario '{scenario_id}'. Valid scenarios: {valid}")


def build_context(
    *,
    scenario: dict[str, Any],
    run_id: str,
    region: str,
    stack_name: str,
    dry_run: bool,
) -> AwsLabContext:
    suffix = re.sub(r"[^a-z0-9]", "", f"{scenario['id']}{run_id}".lower())[-12:]
    tags = {
        "cris-sme-lab": "true",
        "cris-sme-scenario": str(scenario["id"]),
        "cris-sme-run-id": run_id,
        "cris-sme-purpose": "evidence-dataset",
        "cris-sme-owner": os.getenv("CRIS_SME_AWS_LAB_OWNER", os.getenv("USER", "unknown")),
        "cris-sme-delete-after": (datetime.now(UTC) + timedelta(days=2)).date().isoformat(),
        "cris-sme-managed-by": "cris-sme-aws-evidence-lab",
        "organization": str(scenario.get("organization_name", scenario["title"])),
    }
    return AwsLabContext(
        scenario=scenario,
        run_id=run_id,
        region=region,
        stack_name=stack_name,
        suffix=suffix,
        tags=tags,
        dry_run=dry_run,
    )


def deploy(context: AwsLabContext) -> None:
    print(
        f"Deploying AWS evidence lab scenario '{context.scenario['id']}' "
        f"as stack {context.stack_name} in {context.region}"
    )
    template_path = write_template(context)
    run_aws(
        [
            "cloudformation",
            "deploy",
            "--stack-name",
            context.stack_name,
            "--template-file",
            str(template_path),
            "--region",
            context.region,
            "--parameter-overrides",
            f"LabName={context.stack_name}",
            f"LabSuffix={context.suffix}",
            f"ScenarioId={context.scenario['id']}",
            f"OrganizationName={context.scenario.get('organization_name', context.scenario['title'])}",
            "--tags",
            *format_tags(context.tags),
        ],
        context,
    )
    write_manifest(context, status="deployed")
    print_assessment_command(context)


def assess(context: AwsLabContext, output_root: Path) -> None:
    output_dir = output_root / context.run_id / str(context.scenario["id"]) / "reports"
    figure_dir = output_root / context.run_id / str(context.scenario["id"]) / "figures"
    if not context.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        figure_dir.mkdir(parents=True, exist_ok=True)
    write_manifest(context, status="assessment_started", output_dir=output_dir)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    env["CRIS_SME_AWS_ORGANIZATION_NAME"] = str(
        context.scenario.get("organization_name", context.scenario.get("title", "AWS Evidence Lab"))
    )
    env["CRIS_SME_AWS_SECTOR"] = str(context.scenario.get("sector", "Research Lab"))
    env["CRIS_SME_AWS_REGIONS"] = context.region
    env["AWS_DEFAULT_REGION"] = context.region
    hydrate_aws_sdk_credentials(env)

    command = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "run_assessment_snapshot.py"),
        "--collector",
        "aws",
        "--output-dir",
        str(output_dir),
        "--figure-dir",
        str(figure_dir),
        "--dataset-source-type",
        str(context.scenario["dataset_source_type"]),
        "--authorization-basis",
        str(context.scenario["authorization_basis"]),
        "--dataset-use",
        str(context.scenario["dataset_use"]),
    ]
    run_command(command, context, env=env, cwd=REPO_ROOT)
    if not context.dry_run:
        copy_manifest_to_output(context, output_dir)


def hydrate_aws_sdk_credentials(env: dict[str, str]) -> None:
    """Expose AWS CLI login credentials to SDKs that lack the login provider."""
    if env.get("AWS_ACCESS_KEY_ID"):
        return
    profile = env.get("AWS_PROFILE")
    if not profile:
        return
    completed = subprocess.run(
        ["aws", "configure", "export-credentials", "--profile", profile, "--format", "process"],
        capture_output=True,
        text=True,
        check=True,
    )
    credentials = json.loads(completed.stdout)
    env["AWS_ACCESS_KEY_ID"] = str(credentials["AccessKeyId"])
    env["AWS_SECRET_ACCESS_KEY"] = str(credentials["SecretAccessKey"])
    if credentials.get("SessionToken"):
        env["AWS_SESSION_TOKEN"] = str(credentials["SessionToken"])


def cleanup(context: AwsLabContext) -> None:
    print(f"Deleting AWS evidence lab stack {context.stack_name} in {context.region}")
    run_aws(
        [
            "cloudformation",
            "delete-stack",
            "--stack-name",
            context.stack_name,
            "--region",
            context.region,
        ],
        context,
    )
    run_aws(
        [
            "cloudformation",
            "wait",
            "stack-delete-complete",
            "--stack-name",
            context.stack_name,
            "--region",
            context.region,
        ],
        context,
    )
    write_manifest(context, status="cleanup_requested")


def build_template(context: AwsLabContext) -> dict[str, Any]:
    if context.scenario["id"] == "sigi-full-spectrum":
        return sigi_full_spectrum_template()
    if context.scenario["id"] == "public-exposure":
        return public_exposure_template()
    if context.scenario["id"] == "clean-baseline":
        return clean_baseline_template()
    raise ValueError(f"Scenario '{context.scenario['id']}' has no CloudFormation template.")


def sigi_full_spectrum_template() -> dict[str, Any]:
    template = base_template(include_internet_gateway=True)
    resources = template["Resources"]
    resources.update(
        {
            "PublicSubnetB": {
                "Type": "AWS::EC2::Subnet",
                "Properties": {
                    "VpcId": {"Ref": "Vpc"},
                    "CidrBlock": "10.84.0.16/28",
                    "AvailabilityZone": {"Fn::Select": [1, {"Fn::GetAZs": ""}]},
                    "MapPublicIpOnLaunch": True,
                    "Tags": tag_properties("sigi-public-subnet-b"),
                },
            },
            "PublicRouteTable": {
                "Type": "AWS::EC2::RouteTable",
                "Properties": {"VpcId": {"Ref": "Vpc"}, "Tags": tag_properties("sigi-public-routes")},
            },
            "DefaultPublicRoute": {
                "Type": "AWS::EC2::Route",
                "DependsOn": "GatewayAttachment",
                "Properties": {
                    "RouteTableId": {"Ref": "PublicRouteTable"},
                    "DestinationCidrBlock": "0.0.0.0/0",
                    "GatewayId": {"Ref": "InternetGateway"},
                },
            },
            "PublicSubnetARouteAssociation": {
                "Type": "AWS::EC2::SubnetRouteTableAssociation",
                "Properties": {"SubnetId": {"Ref": "Subnet"}, "RouteTableId": {"Ref": "PublicRouteTable"}},
            },
            "PublicSubnetBRouteAssociation": {
                "Type": "AWS::EC2::SubnetRouteTableAssociation",
                "Properties": {"SubnetId": {"Ref": "PublicSubnetB"}, "RouteTableId": {"Ref": "PublicRouteTable"}},
            },
            "OpenAdminSecurityGroup": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "SIGI controlled lab public administration and database exposure",
                    "VpcId": {"Ref": "Vpc"},
                    "SecurityGroupIngress": [
                        {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "CidrIp": "0.0.0.0/0", "Description": "Intentional public SSH lab signal"},
                        {"IpProtocol": "tcp", "FromPort": 3389, "ToPort": 3389, "CidrIp": "0.0.0.0/0", "Description": "Intentional public RDP lab signal"},
                        {"IpProtocol": "tcp", "FromPort": 5432, "ToPort": 5432, "CidrIp": "0.0.0.0/0", "Description": "Intentional public PostgreSQL lab signal"},
                        {"IpProtocol": "-1", "CidrIp": "10.0.0.0/8", "Description": "Intentionally broad private ingress"},
                    ],
                    "SecurityGroupEgress": [{"IpProtocol": "-1", "CidrIp": "0.0.0.0/0"}],
                    "Tags": tag_properties("sigi-open-admin-sg"),
                },
            },
            "WeakWorkload": {
                "Type": "AWS::EC2::Instance",
                "Properties": {
                    "ImageId": {"Ref": "LatestAmiId"},
                    "InstanceType": "t3.micro",
                    "SubnetId": {"Ref": "Subnet"},
                    "SecurityGroupIds": [{"Ref": "OpenAdminSecurityGroup"}],
                    "MetadataOptions": {"HttpEndpoint": "enabled", "HttpTokens": "optional"},
                    "Tags": tag_properties("sigi-weak-workload"),
                },
            },
            "OrphanedVolume": {
                "Type": "AWS::EC2::Volume",
                "Properties": {
                    "AvailabilityZone": {"Fn::GetAtt": ["WeakWorkload", "AvailabilityZone"]},
                    "Size": 1,
                    "Encrypted": False,
                    "Tags": tag_properties("sigi-orphaned-volume"),
                },
            },
            "OrphanedElasticIp": {"Type": "AWS::EC2::EIP", "Properties": {"Domain": "vpc", "Tags": tag_properties("sigi-orphaned-eip")}},
            "PublicDataBucket": public_bucket_resource("sigi-public"),
            "PublicDataBucketPolicy": public_bucket_policy("PublicDataBucket"),
            "ProtectedEvidenceBucket": private_bucket_resource("sigi-protected"),
            "TrailBucket": private_bucket_resource("sigi-trail"),
            "TrailBucketPolicy": cloudtrail_bucket_policy(),
            "AuditTrail": {
                "Type": "AWS::CloudTrail::Trail",
                "DependsOn": "TrailBucketPolicy",
                "Properties": {
                    "TrailName": {"Ref": "LabName"},
                    "S3BucketName": {"Ref": "TrailBucket"},
                    "IsLogging": True,
                    "IsMultiRegionTrail": True,
                    "IncludeGlobalServiceEvents": True,
                    "EnableLogFileValidation": True,
                    "Tags": tag_properties("sigi-audit-trail"),
                },
            },
            "ShortRetentionLogGroup": {"Type": "AWS::Logs::LogGroup", "Properties": {"RetentionInDays": 7, "Tags": tag_properties("sigi-short-retention-logs")}},
            "CpuAlarm": cloudwatch_alarm("CPUUtilization", "AWS/EC2", "WeakWorkload"),
            "StatusAlarm": cloudwatch_alarm("StatusCheckFailed", "AWS/EC2", "WeakWorkload"),
            "NetworkAlarm": cloudwatch_alarm("NetworkIn", "AWS/EC2", "WeakWorkload"),
            "DatabaseSecret": {
                "Type": "AWS::SecretsManager::Secret",
                "Properties": {
                    "Description": "Synthetic SIGI lab database credentials; no customer data",
                    "GenerateSecretString": {"SecretStringTemplate": "{\"username\":\"sigiadmin\"}", "GenerateStringKey": "password", "PasswordLength": 24, "ExcludePunctuation": True},
                    "Tags": tag_properties("sigi-database-secret"),
                },
            },
            "DatabaseSubnetGroup": {
                "Type": "AWS::RDS::DBSubnetGroup",
                "Properties": {"DBSubnetGroupDescription": "SIGI controlled lab public database subnets", "SubnetIds": [{"Ref": "Subnet"}, {"Ref": "PublicSubnetB"}], "Tags": tag_properties("sigi-db-subnets")},
            },
            "WeakDatabase": {
                "Type": "AWS::RDS::DBInstance",
                "DeletionPolicy": "Delete",
                "Properties": {
                    "Engine": "postgres",
                    "DBInstanceClass": "db.t3.micro",
                    "AllocatedStorage": "20",
                    "StorageType": "gp2",
                    "StorageEncrypted": False,
                    "PubliclyAccessible": True,
                    "BackupRetentionPeriod": 0,
                    "DeletionProtection": False,
                    "MultiAZ": False,
                    "AutoMinorVersionUpgrade": False,
                    "MasterUsername": "sigiadmin",
                    "ManageMasterUserPassword": True,
                    "DBSubnetGroupName": {"Ref": "DatabaseSubnetGroup"},
                    "VPCSecurityGroups": [{"Ref": "OpenAdminSecurityGroup"}],
                    "Tags": tag_properties("sigi-weak-database"),
                },
            },
            "IncidentRunbook": {
                "Type": "AWS::SSM::Document",
                "Properties": {
                    "DocumentType": "Automation",
                    "Content": {"schemaVersion": "0.3", "description": "SIGI synthetic incident triage runbook", "mainSteps": [{"name": "RecordTriage", "action": "aws:executeScript", "inputs": {"Runtime": "python3.11", "Handler": "handler", "Script": "def handler(events, context):\n    return {'status': 'triage-recorded'}"}}]},
                    "Tags": tag_properties("sigi-incident-runbook"),
                },
            },
            "ApplicationCluster": {"Type": "AWS::ECS::Cluster", "Properties": {"ClusterName": {"Fn::Sub": "sigi-app-${LabSuffix}"}, "ClusterSettings": [{"Name": "containerInsights", "Value": "disabled"}], "Tags": tag_properties("sigi-application-cluster")}},
            "ClinicalThingGroup": {"Type": "AWS::IoT::ThingGroup", "Properties": {"ThingGroupName": {"Fn::Sub": "sigi-clinical-${LabSuffix}"}, "Tags": tag_properties("sigi-clinical-iot-group")}},
            "ClinicalSensorOne": iot_thing("sensor-01"),
            "ClinicalSensorTwo": iot_thing("sensor-02"),
            "ClinicalGateway": iot_thing("gateway-01"),
            "OverbroadIotPolicy": {"Type": "AWS::IoT::Policy", "Properties": {"PolicyName": {"Fn::Sub": "sigi-overbroad-${LabSuffix}"}, "PolicyDocument": {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Action": "iot:*", "Resource": "*"}]}, "Tags": tag_properties("sigi-overbroad-iot-policy")}},
        }
    )
    template["Outputs"].update({
        "WeakInstanceId": {"Value": {"Ref": "WeakWorkload"}},
        "DatabaseEndpoint": {"Value": {"Fn::GetAtt": ["WeakDatabase", "Endpoint.Address"]}},
        "PublicBucketName": {"Value": {"Ref": "PublicDataBucket"}},
    })
    return template


def clean_baseline_template() -> dict[str, Any]:
    template = base_template()
    template["Resources"].update(
        {
            "PrivateOnlySecurityGroup": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "CRIS-SME clean-baseline private-only lab security group",
                    "VpcId": {"Ref": "Vpc"},
                    "SecurityGroupEgress": [
                        {
                            "IpProtocol": "-1",
                            "CidrIp": "0.0.0.0/0",
                            "Description": "Default outbound access for lab baseline",
                        }
                    ],
                    "Tags": tag_properties("clean-baseline-private-sg"),
                },
            },
            "PrivateBucket": private_bucket_resource("clean"),
        }
    )
    return template


def public_exposure_template() -> dict[str, Any]:
    template = base_template(include_internet_gateway=True)
    template["Resources"].update(
        {
            "OpenAdminSecurityGroup": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "CRIS-SME lab security group with intentionally public SSH and RDP rules",
                    "VpcId": {"Ref": "Vpc"},
                    "SecurityGroupIngress": [
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 22,
                            "ToPort": 22,
                            "CidrIp": "0.0.0.0/0",
                            "Description": "Intentional CRIS-SME lab SSH exposure, no instances attached",
                        },
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 3389,
                            "ToPort": 3389,
                            "CidrIp": "0.0.0.0/0",
                            "Description": "Intentional CRIS-SME lab RDP exposure, no instances attached",
                        },
                    ],
                    "SecurityGroupEgress": [
                        {
                            "IpProtocol": "-1",
                            "CidrIp": "0.0.0.0/0",
                            "Description": "Default outbound access for lab baseline",
                        }
                    ],
                    "Tags": tag_properties("public-exposure-open-admin-sg"),
                },
            },
            "PublicLabBucket": public_bucket_resource("public"),
            "PublicLabBucketPolicy": {
                "Type": "AWS::S3::BucketPolicy",
                "Properties": {
                    "Bucket": {"Ref": "PublicLabBucket"},
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Sid": "CrisSmeLabPublicReadEmptyBucket",
                                "Effect": "Allow",
                                "Principal": "*",
                                "Action": "s3:GetObject",
                                "Resource": {
                                    "Fn::Sub": "arn:${AWS::Partition}:s3:::${PublicLabBucket}/*"
                                },
                            }
                        ],
                    },
                },
            },
        }
    )
    return template


def public_bucket_policy(bucket_logical_id: str) -> dict[str, Any]:
    return {
        "Type": "AWS::S3::BucketPolicy",
        "Properties": {
            "Bucket": {"Ref": bucket_logical_id},
            "PolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "CrisSmeLabPublicReadEmptyBucket",
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "s3:GetObject",
                        "Resource": {"Fn::Sub": f"arn:${{AWS::Partition}}:s3:::${{{bucket_logical_id}}}/*"},
                    }
                ],
            },
        },
    }


def cloudtrail_bucket_policy() -> dict[str, Any]:
    return {
        "Type": "AWS::S3::BucketPolicy",
        "Properties": {
            "Bucket": {"Ref": "TrailBucket"},
            "PolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "AWSCloudTrailAclCheck",
                        "Effect": "Allow",
                        "Principal": {"Service": "cloudtrail.amazonaws.com"},
                        "Action": "s3:GetBucketAcl",
                        "Resource": {"Fn::GetAtt": ["TrailBucket", "Arn"]},
                        "Condition": {"StringEquals": {"AWS:SourceArn": {"Fn::Sub": "arn:${AWS::Partition}:cloudtrail:${AWS::Region}:${AWS::AccountId}:trail/${AWS::StackName}"}}},
                    },
                    {
                        "Sid": "AWSCloudTrailWrite",
                        "Effect": "Allow",
                        "Principal": {"Service": "cloudtrail.amazonaws.com"},
                        "Action": "s3:PutObject",
                        "Resource": {"Fn::Sub": "${TrailBucket.Arn}/AWSLogs/${AWS::AccountId}/*"},
                        "Condition": {
                            "StringEquals": {
                                "s3:x-amz-acl": "bucket-owner-full-control",
                                "AWS:SourceArn": {"Fn::Sub": "arn:${AWS::Partition}:cloudtrail:${AWS::Region}:${AWS::AccountId}:trail/${AWS::StackName}"},
                            }
                        },
                    },
                ],
            },
        },
    }


def cloudwatch_alarm(metric_name: str, namespace: str, instance_logical_id: str) -> dict[str, Any]:
    return {
        "Type": "AWS::CloudWatch::Alarm",
        "Properties": {
            "AlarmDescription": f"SIGI controlled lab {metric_name} signal",
            "MetricName": metric_name,
            "Namespace": namespace,
            "Statistic": "Average",
            "Period": 300,
            "EvaluationPeriods": 1,
            "Threshold": 1,
            "ComparisonOperator": "GreaterThanThreshold",
            "TreatMissingData": "notBreaching",
            "Dimensions": [{"Name": "InstanceId", "Value": {"Ref": instance_logical_id}}],
            "Tags": tag_properties(f"sigi-{metric_name.lower()}-alarm"),
        },
    }


def iot_thing(name: str) -> dict[str, Any]:
    return {
        "Type": "AWS::IoT::Thing",
        "Properties": {
            "ThingName": {"Fn::Sub": f"sigi-{name}-${{LabSuffix}}"},
            "AttributePayload": {"Attributes": {"environment": "controlled-lab", "organization": "SIGI-Technologies"}},
        },
    }


def base_template(*, include_internet_gateway: bool = False) -> dict[str, Any]:
    resources: dict[str, Any] = {
        "Vpc": {
            "Type": "AWS::EC2::VPC",
            "Properties": {
                "CidrBlock": "10.84.0.0/24",
                "EnableDnsHostnames": True,
                "EnableDnsSupport": True,
                "Tags": tag_properties("cris-sme-aws-lab-vpc"),
            },
        },
        "Subnet": {
            "Type": "AWS::EC2::Subnet",
            "Properties": {
                "VpcId": {"Ref": "Vpc"},
                "CidrBlock": "10.84.0.0/28",
                "AvailabilityZone": {"Fn::Select": [0, {"Fn::GetAZs": ""}]},
                "MapPublicIpOnLaunch": include_internet_gateway,
                "Tags": tag_properties("cris-sme-aws-lab-subnet"),
            },
        },
    }
    if include_internet_gateway:
        resources.update(
            {
                "InternetGateway": {
                    "Type": "AWS::EC2::InternetGateway",
                    "Properties": {
                        "Tags": tag_properties("cris-sme-aws-lab-igw"),
                    },
                },
                "GatewayAttachment": {
                    "Type": "AWS::EC2::VPCGatewayAttachment",
                    "Properties": {
                        "VpcId": {"Ref": "Vpc"},
                        "InternetGatewayId": {"Ref": "InternetGateway"},
                    },
                },
            }
        )
    return {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "CRIS-SME controlled, tagged AWS evidence lab managed as one stack.",
        "Parameters": {
            "LabName": {"Type": "String"},
            "LabSuffix": {"Type": "String"},
            "ScenarioId": {"Type": "String"},
            "OrganizationName": {"Type": "String", "Default": "CRIS-SME Evidence Lab"},
            "LatestAmiId": {
                "Type": "AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>",
                "Default": "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64",
            },
        },
        "Resources": resources,
        "Outputs": {
            "VpcId": {"Value": {"Ref": "Vpc"}},
            "ScenarioId": {"Value": {"Ref": "ScenarioId"}},
        },
    }


def private_bucket_resource(prefix: str) -> dict[str, Any]:
    return {
        "Type": "AWS::S3::Bucket",
        "Properties": {
            "BucketName": bucket_name(prefix),
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": [
                    {
                        "ServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256",
                        }
                    }
                ]
            },
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            },
            "VersioningConfiguration": {"Status": "Enabled"},
            "Tags": tag_properties(f"{prefix}-private-bucket"),
        },
    }


def public_bucket_resource(prefix: str) -> dict[str, Any]:
    return {
        "Type": "AWS::S3::Bucket",
        "Properties": {
            "BucketName": bucket_name(prefix),
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": False,
                "BlockPublicPolicy": False,
                "IgnorePublicAcls": False,
                "RestrictPublicBuckets": False,
            },
            "OwnershipControls": {
                "Rules": [{"ObjectOwnership": "BucketOwnerPreferred"}],
            },
            "Tags": tag_properties(f"{prefix}-empty-public-bucket"),
        },
    }


def bucket_name(prefix: str) -> dict[str, Any]:
    return {
        "Fn::Sub": [
            "cris-sme-${Prefix}-${AWS::AccountId}-${AWS::Region}-${LabSuffix}",
            {"Prefix": prefix},
        ]
    }


def tag_properties(name: str) -> list[dict[str, Any]]:
    return [
        {"Key": "Name", "Value": name},
        {"Key": "cris-sme-lab", "Value": "true"},
        {"Key": "cris-sme-scenario", "Value": {"Ref": "ScenarioId"}},
        {"Key": "cris-sme-run-id", "Value": {"Ref": "LabSuffix"}},
        {"Key": "cris-sme-purpose", "Value": "evidence-dataset"},
        {"Key": "cris-sme-managed-by", "Value": "cris-sme-aws-evidence-lab"},
        {"Key": "organization", "Value": {"Ref": "OrganizationName"}},
    ]


def write_template(context: AwsLabContext) -> Path:
    template = build_template(context)
    if context.dry_run:
        path = Path(tempfile.gettempdir()) / f"{context.stack_name}.template.json"
    else:
        path = manifest_dir(context) / f"{context.stack_name}.template.json"
    if not context.dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(template, indent=2), encoding="utf-8")
    else:
        print(f"Dry run: CloudFormation template would be written to {path}")
    return path


def format_tags(tags: dict[str, str]) -> list[str]:
    return [f"{key}={value}" for key, value in tags.items()]


def normalize_run_id(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9-]", "-", value.strip()).strip("-").lower()
    if not normalized:
        raise ValueError("run id cannot be empty")
    return normalized[:24]


def run_aws(args: list[str], context: AwsLabContext) -> None:
    run_command(["aws", *args], context)


def run_command(
    command: list[str],
    context: AwsLabContext,
    *,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> None:
    printable = " ".join(command)
    print(f"$ {printable}")
    if context.dry_run:
        return
    subprocess.run(command, cwd=cwd, env=env, check=True)


def print_assessment_command(context: AwsLabContext) -> None:
    command = [
        "python3",
        "scripts/aws_evidence_lab.py",
        "assess",
        "--scenario",
        str(context.scenario["id"]),
        "--run-id",
        context.run_id,
        "--stack-name",
        context.stack_name,
        "--region",
        context.region,
    ]
    print("Next assessment command:")
    print(f"$ {' '.join(command)}")


def manifest_dir(context: AwsLabContext) -> Path:
    directory = DEFAULT_OUTPUT_ROOT / context.run_id / str(context.scenario["id"])
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def manifest_path(context: AwsLabContext) -> Path:
    return manifest_dir(context) / "lab_manifest.json"


def write_manifest(
    context: AwsLabContext,
    *,
    status: str,
    output_dir: Path | None = None,
) -> None:
    if context.dry_run:
        print(f"Dry run: skipped lab manifest write for status '{status}'.")
        return
    payload = {
        "status": status,
        "generated_at": datetime.now(UTC).isoformat(),
        "run_id": context.run_id,
        "scenario": context.scenario,
        "region": context.region,
        "stack_name": context.stack_name,
        "tags": context.tags,
        "output_dir": str(output_dir) if output_dir else None,
    }
    path = manifest_path(context)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote lab manifest: {path}")


def copy_manifest_to_output(context: AwsLabContext, output_dir: Path) -> None:
    source = manifest_path(context)
    if source.exists():
        shutil.copy2(source, output_dir / "lab_manifest.json")


def main_with_args_for_test(argv: list[str]) -> int:
    """Run the CLI entrypoint with explicit args for unit tests."""
    return main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
