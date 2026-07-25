# Unit tests for the boto3-backed AWS collector in CRIS-SME.
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any, Callable

import pytest

from cris_sme.collectors.aws_collector import AwsCollector, AwsCollectorSettings


@pytest.fixture(autouse=True)
def block_unmocked_boto3_calls(monkeypatch) -> None:
    """Keep unit tests from reaching real AWS, even if boto3 is installed."""

    def fail_if_called(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Unmocked boto3 call in AwsCollector unit tests.")

    monkeypatch.setattr("boto3.client", fail_if_called)
    monkeypatch.setattr("boto3.Session", fail_if_called)


class FakePaginator:
    """Minimal boto3-shaped paginator stub: yields pre-set pages, or one page from a single-page fn."""

    def __init__(
        self,
        *,
        pages: list[dict[str, Any]] | None = None,
        single_page_fn: Callable[..., Any] | None = None,
    ) -> None:
        self._pages = pages
        self._single_page_fn = single_page_fn

    def paginate(self, **kwargs: Any) -> list[dict[str, Any]]:
        if self._pages is not None:
            return self._pages
        result = self._single_page_fn(**kwargs) if self._single_page_fn else {}
        return [result] if isinstance(result, dict) else []


class FakeClient:
    """Minimal boto3-shaped client stub: dispatches by method name to a configured response."""

    def __init__(self, **responses: Any) -> None:
        self._responses = responses
        self._paginated_responses: dict[str, list[dict[str, Any]]] = {}

    def __getattr__(self, name: str) -> Callable[..., Any]:
        value = self._responses.get(name)

        def _call(*args: Any, **kwargs: Any) -> Any:
            if value is None:
                return {}
            if callable(value):
                return value(*args, **kwargs)
            return value

        return _call

    def get_paginator(self, operation_name: str) -> FakePaginator:
        if operation_name in self._paginated_responses:
            return FakePaginator(pages=self._paginated_responses[operation_name])
        return FakePaginator(single_page_fn=getattr(self, operation_name))


def make_factory(clients: dict[str, FakeClient]) -> Callable[[str, str | None], Any]:
    def factory(service_name: str, region: str | None) -> Any:
        _ = region
        return clients.get(service_name, FakeClient())

    return factory


def make_collector(
    clients: dict[str, FakeClient],
    *,
    settings: AwsCollectorSettings | None = None,
) -> AwsCollector:
    return AwsCollector(
        settings=settings or AwsCollectorSettings(regions=("us-east-1",)),
        client_factory=make_factory(clients),
    )


# -- Pagination --------------------------------------------------------------


def test_paginate_allow_failure_aggregates_items_across_pages() -> None:
    """A truncated multi-page response must not silently undercount.

    This is the regression test for the gap found before live testing:
    `_paginate_allow_failure` previously read only the first page of any
    list/describe call, which would have undercounted on any account with
    more resources than fit in one page.
    """
    iam = FakeClient(list_users={"Users": [{"UserName": "only-page-one"}]})
    iam._paginated_responses["list_users"] = [
        {"Users": [{"UserName": "user-a"}, {"UserName": "user-b"}]},
        {"Users": [{"UserName": "user-c"}]},
    ]
    collector = make_collector({"iam": iam})

    users = collector._paginate_allow_failure(iam, "list_users", items_key="Users")

    assert [user["UserName"] for user in users] == ["user-a", "user-b", "user-c"]


def test_paginate_allow_failure_returns_empty_on_failure() -> None:
    def raise_error(**kwargs: Any) -> Any:
        raise RuntimeError("AccessDenied")

    iam = FakeClient(list_roles=raise_error)
    collector = make_collector({"iam": iam})

    assert collector._paginate_allow_failure(iam, "list_roles", items_key="Roles") == []


# -- Cross-account AssumeRole -------------------------------------------------


def test_assume_role_credentials_builds_correct_kwargs_and_returns_credentials() -> None:
    captured: dict[str, Any] = {}

    def assume_role(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {
            "Credentials": {
                "AccessKeyId": "ASIA-temp",
                "SecretAccessKey": "secret-temp",
                "SessionToken": "token-temp",
            }
        }

    sts = FakeClient(assume_role=assume_role)
    settings = AwsCollectorSettings(
        regions=("us-east-1",),
        role_arn="arn:aws:iam::222222222222:role/cris-sme-target",
        external_id="shared-secret-id",
    )
    collector = make_collector({}, settings=settings)

    credentials = collector._assume_role_credentials(sts)

    assert captured["RoleArn"] == "arn:aws:iam::222222222222:role/cris-sme-target"
    assert captured["ExternalId"] == "shared-secret-id"
    assert captured["RoleSessionName"].startswith("cris-sme-assessment-")
    assert credentials == {
        "AccessKeyId": "ASIA-temp",
        "SecretAccessKey": "secret-temp",
        "SessionToken": "token-temp",
    }


def test_assume_role_credentials_omits_external_id_when_not_configured() -> None:
    captured: dict[str, Any] = {}

    def assume_role(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {"Credentials": {}}

    sts = FakeClient(assume_role=assume_role)
    settings = AwsCollectorSettings(
        regions=("us-east-1",),
        role_arn="arn:aws:iam::222222222222:role/cris-sme-target",
    )
    collector = make_collector({}, settings=settings)

    collector._assume_role_credentials(sts)

    assert "ExternalId" not in captured


def test_assume_role_credentials_raises_clearly_on_failure() -> None:
    def raise_access_denied(**kwargs: Any) -> Any:
        raise RuntimeError("AccessDenied: not authorized to assume this role")

    sts = FakeClient(assume_role=raise_access_denied)
    settings = AwsCollectorSettings(
        regions=("us-east-1",),
        role_arn="arn:aws:iam::222222222222:role/cris-sme-target",
    )
    collector = make_collector({}, settings=settings)

    with pytest.raises(ValueError, match="Unable to assume AWS role"):
        collector._assume_role_credentials(sts)


# -- IAM domain --------------------------------------------------------------


def test_organization_name_resolves_from_consistent_resource_tags() -> None:
    tagging = FakeClient(
        get_resources={
            "ResourceTagMappingList": [
                {"Tags": [{"Key": "organization", "Value": "SIGI Technologies"}]},
                {"Tags": [{"Key": "organization", "Value": "SIGI Technologies"}]},
            ]
        }
    )
    collector = make_collector({"resourcegroupstaggingapi": tagging})

    name, source = collector._resolve_organization_name("000832363767")

    assert name == "SIGI Technologies"
    assert source == "resource_tag"


def test_organization_name_searches_all_assessment_regions() -> None:
    clients_by_region = {
        "us-east-1": FakeClient(get_resources={"ResourceTagMappingList": []}),
        "eu-west-2": FakeClient(
            get_resources={
                "ResourceTagMappingList": [
                    {"Tags": [{"Key": "organization", "Value": "SIGI Technologies"}]}
                ]
            }
        ),
    }

    def factory(service_name: str, region: str | None) -> Any:
        if service_name == "resourcegroupstaggingapi":
            return clients_by_region[str(region)]
        return FakeClient()

    collector = AwsCollector(
        AwsCollectorSettings(regions=("us-east-1", "eu-west-2")),
        client_factory=factory,
    )

    assert collector._resolve_organization_name(
        "000832363767", ["us-east-1", "eu-west-2"]
    ) == ("SIGI Technologies", "resource_tag")


def test_explicit_organization_name_takes_priority_over_cloud_metadata() -> None:
    settings = AwsCollectorSettings(
        regions=("us-east-1",),
        organization_name="Configured Customer",
    )
    collector = make_collector({}, settings=settings)

    assert collector._resolve_organization_name("111111111111") == (
        "Configured Customer",
        "configured",
    )


def test_ambiguous_organization_tags_do_not_guess_customer_identity() -> None:
    tagging = FakeClient(
        get_resources={
            "ResourceTagMappingList": [
                {"Tags": [{"Key": "organization", "Value": "Customer A"}]},
                {"Tags": [{"Key": "organization", "Value": "Customer B"}]},
            ]
        }
    )
    collector = make_collector({"resourcegroupstaggingapi": tagging})

    assert collector._resolve_organization_name("111111111111") == (
        "AWS SME Account",
        "default",
    )


def test_collect_iam_profile_detects_privileged_users_without_mfa() -> None:
    def attached_user_policies(**kwargs: Any) -> dict[str, Any]:
        if kwargs.get("UserName") == "admin":
            return {"AttachedPolicies": [{"PolicyArn": "arn:aws:iam::aws:policy/AdministratorAccess"}]}
        return {"AttachedPolicies": []}

    def mfa_devices(**kwargs: Any) -> dict[str, Any]:
        if kwargs.get("UserName") == "admin":
            return {"MFADevices": []}
        return {"MFADevices": [{"SerialNumber": "x"}]}

    iam = FakeClient(
        list_users={"Users": [{"UserName": "admin"}, {"UserName": "alice"}]},
        list_roles={"Roles": []},
        list_attached_user_policies=attached_user_policies,
        list_attached_role_policies={"AttachedPolicies": []},
        list_mfa_devices=mfa_devices,
        list_access_keys={"AccessKeyMetadata": []},
        get_account_password_policy={"MinimumPasswordLength": 14},
        get_account_summary={"SummaryMap": {"AccountMFAEnabled": 1}},
    )
    sts = FakeClient(
        get_caller_identity={
            "Account": "111111111111",
            "Arn": "arn:aws:iam::111111111111:user/admin",
        }
    )
    access_analyzer = FakeClient(list_analyzers={"analyzers": []})

    collector = make_collector(
        {"iam": iam, "sts": sts, "accessanalyzer": access_analyzer}
    )
    profile, metadata = collector._collect_iam_profile()

    assert profile.privileged_accounts == 1
    assert profile.privileged_accounts_without_mfa == 1
    assert profile.conditional_access_enforced_for_admins is True
    assert profile.signed_in_user_is_directory_admin is True
    assert metadata["conditional_access_accessible"] is True
    assert metadata["iam_collection_mode"] == "aws_iam_user_role_inventory"


def test_principal_is_privileged_detects_admin_via_inline_policy() -> None:
    """A custom inline policy with Allow Action="*" Resource="*" must count as admin-equivalent.

    Only checking attached managed policies (the literal AdministratorAccess
    ARN) misses any custom inline policy granting the same effective access
    under a different name.
    """
    iam = FakeClient(
        list_attached_user_policies={"AttachedPolicies": []},
        list_user_policies={"PolicyNames": ["FullAccessInline"]},
        get_user_policy={
            "PolicyDocument": {
                "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]
            }
        },
        list_groups_for_user={"Groups": []},
    )
    collector = make_collector({"iam": iam})

    assert collector._principal_is_privileged(iam, "user", "power-user") is True


def test_principal_is_privileged_detects_admin_via_group_attached_policy() -> None:
    """A user with no direct admin grant but membership in an admin-policy group must count as admin.

    Privilege granted only through IAM group membership is invisible to a
    check that only inspects the user's own attached/inline policies.
    """
    iam = FakeClient(
        list_attached_user_policies={"AttachedPolicies": []},
        list_user_policies={"PolicyNames": []},
        list_groups_for_user={"Groups": [{"GroupName": "admins"}]},
        list_attached_group_policies={
            "AttachedPolicies": [{"PolicyArn": "arn:aws:iam::aws:policy/AdministratorAccess"}]
        },
    )
    collector = make_collector({"iam": iam})

    assert collector._principal_is_privileged(iam, "user", "grouped-user") is True


def test_principal_is_privileged_ignores_non_admin_inline_and_group_policies() -> None:
    iam = FakeClient(
        list_attached_user_policies={"AttachedPolicies": []},
        list_user_policies={"PolicyNames": ["ReadOnlyInline"]},
        get_user_policy={
            "PolicyDocument": {
                "Statement": [{"Effect": "Allow", "Action": "s3:GetObject", "Resource": "*"}]
            }
        },
        list_groups_for_user={"Groups": [{"GroupName": "readers"}]},
        list_attached_group_policies={
            "AttachedPolicies": [{"PolicyArn": "arn:aws:iam::aws:policy/ReadOnlyAccess"}]
        },
    )
    collector = make_collector({"iam": iam})

    assert collector._principal_is_privileged(iam, "user", "regular-user") is False


def test_collect_iam_profile_degrades_when_apis_inaccessible() -> None:
    def raise_access_denied(**kwargs: Any) -> Any:
        raise RuntimeError("AccessDenied")

    iam = FakeClient(get_account_password_policy=raise_access_denied)
    collector = make_collector({"iam": iam})
    profile, metadata = collector._collect_iam_profile()

    assert profile.privileged_accounts == 0
    assert profile.conditional_access_enforced_for_admins is False
    assert metadata["conditional_access_accessible"] is False
    assert metadata["iam_collection_mode"] == "default_no_iam_inventory"


def test_collect_iam_profile_flags_stale_access_keys() -> None:
    stale_date = datetime.now(UTC) - timedelta(days=200)

    def last_used(**kwargs: Any) -> dict[str, Any]:
        return {"AccessKeyLastUsed": {"LastUsedDate": stale_date}}

    iam = FakeClient(
        list_users={"Users": [{"UserName": "service-user"}]},
        list_roles={"Roles": []},
        list_attached_user_policies={"AttachedPolicies": []},
        list_attached_role_policies={"AttachedPolicies": []},
        list_access_keys={
            "AccessKeyMetadata": [{"AccessKeyId": "AKIA1", "Status": "Active"}]
        },
        get_access_key_last_used=last_used,
    )
    collector = make_collector({"iam": iam, "sts": FakeClient(), "accessanalyzer": FakeClient()})
    profile, _ = collector._collect_iam_profile()

    assert profile.stale_service_principals == 1


# -- Network domain ------------------------------------------------------------


def test_collect_network_profile_detects_public_exposure() -> None:
    security_groups = {
        "SecurityGroups": [
            {
                "GroupId": "sg-1",
                "IpPermissions": [
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 22,
                        "ToPort": 22,
                        "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                    },
                    {
                        "IpProtocol": "tcp",
                        "FromPort": 3389,
                        "ToPort": 3389,
                        "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
                    },
                ],
            }
        ]
    }
    ec2 = FakeClient(
        describe_security_groups=security_groups,
        describe_vpc_endpoints={"VpcEndpoints": [{"VpcEndpointId": "vpce-1"}]},
    )
    collector = make_collector({"ec2": ec2})
    profile, metadata = collector._collect_network_profile(["us-east-1"])

    assert profile.internet_exposed_rdp_assets == 1
    assert profile.internet_exposed_ssh_assets == 1
    assert profile.permissive_nsg_rules == 2
    assert profile.private_endpoints_configured == 1
    assert profile.public_storage_endpoints == 0
    assert metadata["network_collection_mode"] == "aws_ec2_security_group_inventory"


def test_collect_network_profile_degrades_when_no_security_groups() -> None:
    collector = make_collector({"ec2": FakeClient()})
    profile, metadata = collector._collect_network_profile(["us-east-1"])

    assert profile.internet_exposed_rdp_assets == 0
    assert metadata["network_collection_mode"] == "default_no_network_inventory"


def test_collect_network_profile_detects_internet_facing_http_only_load_balancer() -> None:
    """An internet-facing ALB serving HTTP with no HTTPS listener is a distinct exposure path.

    Security-group rules alone never see this: the ALB's own security group
    can be tight while the load balancer itself is still internet-facing
    and unencrypted at the listener layer.
    """
    ec2 = FakeClient()

    def describe_listeners(**kwargs: Any) -> dict[str, Any]:
        if kwargs.get("LoadBalancerArn") == "arn:aws:elasticloadbalancing:lb/http-only":
            return {"Listeners": [{"Protocol": "HTTP", "Port": 80}]}
        return {"Listeners": [{"Protocol": "HTTPS", "Port": 443}]}

    elbv2 = FakeClient(
        describe_load_balancers={
            "LoadBalancers": [
                {
                    "LoadBalancerArn": "arn:aws:elasticloadbalancing:lb/http-only",
                    "Scheme": "internet-facing",
                },
                {
                    "LoadBalancerArn": "arn:aws:elasticloadbalancing:lb/https-ok",
                    "Scheme": "internet-facing",
                },
                {
                    "LoadBalancerArn": "arn:aws:elasticloadbalancing:lb/internal",
                    "Scheme": "internal",
                },
            ]
        },
        describe_listeners=describe_listeners,
    )

    collector = make_collector({"ec2": ec2, "elbv2": elbv2})
    _profile, metadata = collector._collect_network_profile(["us-east-1"])

    assert metadata["load_balancer_count"] == 3
    assert metadata["internet_facing_load_balancer_count"] == 2
    assert metadata["http_only_internet_facing_load_balancer_count"] == 1


# -- Data domain ---------------------------------------------------------------


def test_collect_data_profile_detects_public_unencrypted_buckets_and_databases() -> None:
    def policy_status(**kwargs: Any) -> dict[str, Any]:
        is_public = kwargs.get("Bucket") == "public-bucket"
        return {"PolicyStatus": {"IsPublic": is_public}}

    def encryption(**kwargs: Any) -> dict[str, Any]:
        if kwargs.get("Bucket") == "public-bucket":
            return {"ServerSideEncryptionConfiguration": {"Rules": [{}]}}
        raise RuntimeError("ServerSideEncryptionConfigurationNotFoundError")

    def versioning(**kwargs: Any) -> dict[str, Any]:
        if kwargs.get("Bucket") == "public-bucket":
            return {"Status": "Enabled"}
        return {"Status": "Suspended"}

    def tagging(**kwargs: Any) -> dict[str, Any]:
        if kwargs.get("Bucket") == "public-bucket":
            return {"TagSet": [{"Key": "cris-sme-public-intent", "Value": "intentional-public-service"}]}
        return {"TagSet": []}

    s3 = FakeClient(
        list_buckets={"Buckets": [{"Name": "public-bucket"}, {"Name": "private-bucket"}]},
        get_bucket_policy_status=policy_status,
        get_bucket_acl={"Grants": []},
        get_bucket_encryption=encryption,
        get_bucket_versioning=versioning,
        get_bucket_tagging=tagging,
    )
    rds = FakeClient(
        describe_db_instances={
            "DBInstances": [
                {"DBInstanceIdentifier": "db1", "PubliclyAccessible": False, "StorageEncrypted": True},
                {"DBInstanceIdentifier": "db2", "PubliclyAccessible": True, "StorageEncrypted": False},
            ]
        }
    )
    kms = FakeClient(
        list_keys={"Keys": [{"KeyId": "key1"}]},
        describe_key={"KeyMetadata": {"KeyState": "Enabled"}},
    )
    secretsmanager = FakeClient(list_secrets={"SecretList": [{"RotationEnabled": True}]})

    collector = make_collector({"s3": s3, "rds": rds, "kms": kms, "secretsmanager": secretsmanager})
    profile, metadata = collector._collect_data_profile(["us-east-1"])

    assert profile.public_storage_assets == 1
    assert profile.unencrypted_data_stores == 2
    assert metadata["intentional_public_service_count"] == 1
    assert metadata["public_sql_server_count"] == 1
    assert metadata["unencrypted_sql_database_count"] == 1
    assert profile.key_vault_count == 1
    assert profile.key_vault_purge_protected_count == 1
    assert profile.key_vault_mfa_enabled is True
    assert 0.0 < profile.backup_coverage_ratio < 1.0
    assert metadata["buckets_without_public_access_block_count"] == 2


def test_collect_data_profile_degrades_when_no_storage_inventory() -> None:
    collector = make_collector({"s3": FakeClient(), "rds": FakeClient(), "kms": FakeClient()})
    profile, metadata = collector._collect_data_profile(["us-east-1"])

    assert profile.public_storage_assets == 0
    assert profile.key_vault_posture_state == "not_observed"
    assert metadata["data_collection_mode"] == "default_no_storage_inventory"


def test_collect_data_profile_uses_bucket_region_specific_client() -> None:
    """Per-bucket calls must run against a client built for the bucket's own region.

    A client built for the wrong region would get PermanentRedirect-style
    failures on real AWS for every per-bucket call; this proves the
    collector resolves each bucket's region via get_bucket_location and
    routes per-bucket calls through a same-region client instead of always
    reusing the primary-region client.
    """
    calls_by_region: dict[str | None, list[str]] = {}

    def make_region_client(region: str | None) -> FakeClient:
        def get_bucket_location(**kwargs: Any) -> dict[str, Any]:
            return {"LocationConstraint": "eu-west-2"}

        def get_bucket_acl(**kwargs: Any) -> dict[str, Any]:
            calls_by_region.setdefault(region, []).append("get_bucket_acl")
            return {"Grants": []}

        return FakeClient(
            list_buckets={"Buckets": [{"Name": "remote-bucket"}]},
            get_bucket_location=get_bucket_location,
            get_bucket_acl=get_bucket_acl,
        )

    region_clients: dict[str | None, FakeClient] = {}

    def factory(service_name: str, region: str | None) -> Any:
        if service_name != "s3":
            return FakeClient()
        if region not in region_clients:
            region_clients[region] = make_region_client(region)
        return region_clients[region]

    collector = AwsCollector(
        settings=AwsCollectorSettings(regions=("us-east-1",)),
        client_factory=factory,
    )
    collector._collect_data_profile(["us-east-1"])

    assert "get_bucket_acl" not in calls_by_region.get("us-east-1", [])
    assert calls_by_region.get("eu-west-2") == ["get_bucket_acl"]


def test_collect_data_profile_public_access_block_suppresses_acl_false_positive() -> None:
    """A public ACL grant neutralized by Block Public Access must not be flagged.

    S3 Block Public Access (IgnorePublicAcls) makes AWS itself ignore public
    ACL grants when evaluating actual access; without checking it, the
    collector would over-report exposure for a bucket AWS does not actually
    treat as public.
    """
    s3 = FakeClient(
        list_buckets={"Buckets": [{"Name": "protected-bucket"}]},
        get_bucket_policy_status={"PolicyStatus": {"IsPublic": False}},
        get_bucket_acl={
            "Grants": [
                {"Grantee": {"URI": "http://acs.amazonaws.com/groups/global/AllUsers"}}
            ]
        },
        get_public_access_block={
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            }
        },
    )
    collector = make_collector({"s3": s3, "rds": FakeClient(), "kms": FakeClient()})
    profile, metadata = collector._collect_data_profile(["us-east-1"])

    assert profile.public_storage_assets == 0
    assert metadata["buckets_without_public_access_block_count"] == 0


# -- Monitoring domain ----------------------------------------------------------


def test_collect_monitoring_profile_detects_centralized_logging_and_threat_detection() -> None:
    cloudtrail = FakeClient(
        describe_trails={
            "trailList": [
                {
                    "Name": "main-trail",
                    "IsMultiRegionTrail": True,
                    "CloudWatchLogsLogGroupArn": (
                        "arn:aws:logs:us-east-1:111111111111:log-group:my-trail-logs:*"
                    ),
                }
            ]
        },
        get_trail_status={"IsLogging": True},
    )
    logs = FakeClient(
        describe_log_groups={"logGroups": [{"logGroupName": "my-trail-logs", "retentionInDays": 90}]}
    )
    cloudwatch = FakeClient(describe_alarms={"MetricAlarms": [{}, {}, {}, {}]})
    guardduty = FakeClient(list_detectors={"DetectorIds": ["d1"]})
    securityhub = FakeClient(get_enabled_standards={"StandardsSubscriptions": [{"StandardsArn": "x"}]})
    ssm = FakeClient(list_documents={"DocumentIdentifiers": [{"DocumentType": "Automation"}]})

    collector = make_collector(
        {
            "cloudtrail": cloudtrail,
            "logs": logs,
            "cloudwatch": cloudwatch,
            "guardduty": guardduty,
            "securityhub": securityhub,
            "ssm": ssm,
        }
    )
    profile, metadata = collector._collect_monitoring_profile(["us-east-1"])

    assert profile.activity_log_retention_days == 90
    assert profile.critical_alert_coverage_ratio == 1.0
    assert profile.defender_coverage_ratio == 1.0
    assert profile.centralized_logging_enabled is True
    assert profile.incident_response_runbooks_enabled is True
    assert metadata["guardduty_enabled"] is True


def test_collect_monitoring_profile_counts_active_threat_detection_findings() -> None:
    """Detector/standard existence alone must not be conflated with actual findings.

    GuardDuty/Security Hub being "enabled" only proves the tooling is
    configured; an account can have both enabled and still be sitting on
    unread critical findings, which this test proves get surfaced as counts.
    """

    def list_findings(**kwargs: Any) -> dict[str, Any]:
        criterion = kwargs.get("FindingCriteria", {}).get("Criterion", {})
        if "severity" in criterion:
            return {"FindingIds": ["finding-high-1"]}
        return {"FindingIds": ["finding-1", "finding-2", "finding-high-1"]}

    guardduty = FakeClient(
        list_detectors={"DetectorIds": ["detector-1"]},
        list_findings=list_findings,
    )
    securityhub = FakeClient(
        get_enabled_standards={"StandardsSubscriptions": [{"StandardsArn": "x"}]},
        get_findings={
            "Findings": [
                {"Severity": {"Label": "CRITICAL"}},
                {"Severity": {"Label": "LOW"}},
            ]
        },
    )
    collector = make_collector(
        {
            "cloudtrail": FakeClient(),
            "cloudwatch": FakeClient(),
            "guardduty": guardduty,
            "securityhub": securityhub,
            "ssm": FakeClient(),
        }
    )
    _profile, metadata = collector._collect_monitoring_profile(["us-east-1"])

    assert metadata["guardduty_active_finding_count"] == 3
    assert metadata["guardduty_high_severity_finding_count"] == 1
    assert metadata["securityhub_active_finding_count"] == 2
    assert metadata["securityhub_critical_finding_count"] == 1


def test_collect_monitoring_profile_treats_stopped_trail_as_not_centralized() -> None:
    cloudtrail = FakeClient(
        describe_trails={
            "trailList": [
                {"Name": "stopped-trail", "IsMultiRegionTrail": True},
            ]
        },
        get_trail_status={"IsLogging": False},
    )
    collector = make_collector(
        {
            "cloudtrail": cloudtrail,
            "cloudwatch": FakeClient(),
            "guardduty": FakeClient(),
            "securityhub": FakeClient(),
            "ssm": FakeClient(),
        }
    )
    profile, _metadata = collector._collect_monitoring_profile(["us-east-1"])

    assert profile.centralized_logging_enabled is False


def test_collect_monitoring_profile_degrades_when_no_trails() -> None:
    collector = make_collector(
        {
            "cloudtrail": FakeClient(),
            "cloudwatch": FakeClient(),
            "guardduty": FakeClient(),
            "securityhub": FakeClient(),
            "ssm": FakeClient(),
        }
    )
    profile, metadata = collector._collect_monitoring_profile(["us-east-1"])

    assert profile.activity_log_retention_days == 0
    assert profile.centralized_logging_enabled is False
    assert metadata["monitoring_collection_mode"] == "default_no_monitoring_inventory"


# -- Compute domain --------------------------------------------------------------


def test_collect_compute_profile_detects_hardening_and_patch_compliance() -> None:
    ec2 = FakeClient(
        describe_instances={
            "Reservations": [
                {
                    "Instances": [
                        {"InstanceId": "i-1", "MetadataOptions": {"HttpTokens": "required"}},
                        {"InstanceId": "i-2", "MetadataOptions": {"HttpTokens": "optional"}},
                    ]
                }
            ]
        }
    )
    ssm = FakeClient(
        describe_instance_information={"InstanceInformationList": [{"InstanceId": "i-1"}]},
        describe_instance_patch_states={
            "InstancePatchStates": [
                {"InstanceId": "i-1", "InstancesWithCriticalNonCompliantPatches": 0},
                {"InstanceId": "i-2", "InstancesWithCriticalNonCompliantPatches": 2},
            ]
        },
    )
    backup = FakeClient(
        list_protected_resources={
            "Results": [{"ResourceType": "EC2", "ResourceArn": "arn:aws:ec2:i-1"}]
        }
    )

    collector = make_collector({"ec2": ec2, "ssm": ssm, "backup": backup})
    profile, metadata = collector._collect_compute_profile(["us-east-1"])

    assert metadata["virtual_machine_count"] == 2
    assert profile.hardened_baseline_coverage_ratio == 0.5
    assert profile.unpatched_critical_vms == 1
    assert profile.endpoint_protection_coverage_ratio == 0.5
    assert profile.workload_backup_agent_coverage_ratio == 0.5


def test_collect_compute_profile_chunks_patch_state_requests_beyond_fifty_instances() -> None:
    """describe_instance_patch_states allows at most 50 InstanceIds per call.

    With 60 instances, a single un-chunked call would silently drop the
    last 10; this proves the collector issues two chunked calls (50 + 10)
    and aggregates patch-compliance across both instead of truncating.
    """
    instance_count = 60
    ec2 = FakeClient(
        describe_instances={
            "Reservations": [
                {
                    "Instances": [
                        {"InstanceId": f"i-{index}", "MetadataOptions": {"HttpTokens": "required"}}
                        for index in range(instance_count)
                    ]
                }
            ]
        }
    )

    seen_chunk_sizes: list[int] = []

    def describe_instance_patch_states(**kwargs: Any) -> dict[str, Any]:
        instance_ids = kwargs.get("InstanceIds", [])
        seen_chunk_sizes.append(len(instance_ids))
        return {
            "InstancePatchStates": [
                {"InstanceId": instance_id, "InstancesWithCriticalNonCompliantPatches": 0}
                for instance_id in instance_ids
            ]
        }

    ssm = FakeClient(
        describe_instance_information={"InstanceInformationList": []},
        describe_instance_patch_states=describe_instance_patch_states,
    )
    backup = FakeClient(list_protected_resources={"Results": []})

    collector = make_collector({"ec2": ec2, "ssm": ssm, "backup": backup})
    profile, metadata = collector._collect_compute_profile(["us-east-1"])

    assert seen_chunk_sizes == [50, 10]
    assert metadata["vm_patch_compliant_count"] == instance_count
    assert profile.unpatched_critical_vms == 0


def test_collect_compute_profile_degrades_when_no_instances() -> None:
    collector = make_collector({"ec2": FakeClient(), "ssm": FakeClient(), "backup": FakeClient()})
    profile, metadata = collector._collect_compute_profile(["us-east-1"])

    assert metadata["virtual_machine_count"] == 0
    assert metadata["compute_collection_mode"] == "default_no_compute_inventory"
    assert profile.unpatched_critical_vms == 0


def test_collect_compute_profile_detects_lambda_with_public_url_and_policy() -> None:
    """A public Function URL or wildcard resource policy is a direct exposure path.

    Lambda has no EC2 analog in ComputeProfile's VM-shaped fields, so this
    proves the signal surfaces as compute metadata instead of being
    silently dropped because the account has zero EC2 instances.
    """

    def get_function_url_config(**kwargs: Any) -> dict[str, Any]:
        if kwargs.get("FunctionName") == "public-url-fn":
            return {"AuthType": "NONE"}
        return {"AuthType": "AWS_IAM"}

    def get_policy(**kwargs: Any) -> dict[str, Any]:
        if kwargs.get("FunctionName") == "public-policy-fn":
            return {
                "Policy": json.dumps(
                    {
                        "Statement": [
                            {"Effect": "Allow", "Principal": "*", "Action": "lambda:InvokeFunction"}
                        ]
                    }
                )
            }
        return {
            "Policy": json.dumps(
                {
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "apigateway.amazonaws.com"},
                            "Action": "lambda:InvokeFunction",
                            "Condition": {"ArnLike": {"AWS:SourceArn": "arn:aws:execute-api:*"}},
                        }
                    ]
                }
            )
        }

    lambda_client = FakeClient(
        list_functions={
            "Functions": [
                {"FunctionName": "public-url-fn"},
                {"FunctionName": "public-policy-fn"},
                {"FunctionName": "private-fn"},
            ]
        },
        get_function_url_config=get_function_url_config,
        get_policy=get_policy,
    )

    collector = make_collector(
        {"ec2": FakeClient(), "ssm": FakeClient(), "backup": FakeClient(), "lambda": lambda_client}
    )
    profile, metadata = collector._collect_compute_profile(["us-east-1"])

    assert metadata["virtual_machine_count"] == 0
    assert metadata["compute_collection_mode"] == "aws_lambda_inventory"
    assert metadata["lambda_function_count"] == 3
    assert metadata["lambda_functions_with_public_url_count"] == 1
    assert metadata["lambda_functions_with_public_policy_count"] == 1
    assert profile.unpatched_critical_vms == 0


def test_collect_compute_profile_detects_ecs_services_and_eks_public_endpoints() -> None:
    """ECS/EKS have no EC2 analog either; container-only accounts must not be invisible.

    Also proves an EKS cluster with an unrestricted (0.0.0.0/0, or
    unspecified) public API endpoint is distinguished from one whose public
    endpoint is restricted to a named CIDR range.
    """
    ecs = FakeClient(
        list_clusters={"clusterArns": ["arn:aws:ecs:cluster/prod"]},
        describe_clusters={"clusters": [{"clusterArn": "arn:aws:ecs:cluster/prod", "activeServicesCount": 4}]},
    )

    def describe_cluster(**kwargs: Any) -> dict[str, Any]:
        if kwargs.get("name") == "open-cluster":
            return {
                "cluster": {
                    "resourcesVpcConfig": {
                        "endpointPublicAccess": True,
                        "publicAccessCidrs": ["0.0.0.0/0"],
                    }
                }
            }
        if kwargs.get("name") == "restricted-cluster":
            return {
                "cluster": {
                    "resourcesVpcConfig": {
                        "endpointPublicAccess": True,
                        "publicAccessCidrs": ["203.0.113.0/24"],
                    }
                }
            }
        return {"cluster": {"resourcesVpcConfig": {"endpointPublicAccess": False}}}

    eks = FakeClient(
        list_clusters={"clusters": ["open-cluster", "restricted-cluster", "private-cluster"]},
        describe_cluster=describe_cluster,
    )

    collector = make_collector(
        {"ec2": FakeClient(), "ssm": FakeClient(), "backup": FakeClient(), "ecs": ecs, "eks": eks}
    )
    profile, metadata = collector._collect_compute_profile(["us-east-1"])

    assert metadata["virtual_machine_count"] == 0
    assert metadata["compute_collection_mode"] == "aws_container_inventory"
    assert metadata["ecs_cluster_count"] == 1
    assert metadata["ecs_active_service_count"] == 4
    assert metadata["eks_cluster_count"] == 3
    assert metadata["eks_clusters_with_public_endpoint_count"] == 2
    assert metadata["eks_clusters_with_unrestricted_public_endpoint_count"] == 1
    assert profile.unpatched_critical_vms == 0


# -- Governance domain ------------------------------------------------------------


def test_collect_governance_profile_detects_tagging_and_budgets() -> None:
    tagging_api = FakeClient(
        get_resources={
            "ResourceTagMappingList": [
                {"Tags": [{"Key": "env", "Value": "prod"}]},
                {"Tags": []},
            ]
        }
    )

    def notifications(**kwargs: Any) -> dict[str, Any]:
        return {"Notifications": [{"NotificationType": "ACTUAL"}]}

    budgets = FakeClient(
        describe_budgets={"Budgets": [{"BudgetName": "monthly"}]},
        describe_notifications_for_budget=notifications,
    )
    organizations = FakeClient(list_policies={"Policies": [{"Id": "p1"}, {"Id": "p2"}]})
    ec2 = FakeClient(
        describe_volumes={"Volumes": [{"VolumeId": "vol-1"}]},
        describe_addresses={"Addresses": [{"PublicIp": "1.2.3.4"}]},
    )

    collector = make_collector(
        {
            "resourcegroupstaggingapi": tagging_api,
            "budgets": budgets,
            "organizations": organizations,
            "ec2": ec2,
        }
    )
    profile, metadata = collector._collect_governance_profile(["us-east-1"], "111111111111")

    assert profile.tagging_coverage_ratio == 0.5
    assert profile.budget_alerts_enabled is True
    assert profile.budget_alert_count == 1
    assert profile.policy_assignment_coverage_ratio == 0.4
    assert profile.orphaned_resource_count == 2


def test_collect_governance_profile_degrades_when_budgets_inaccessible() -> None:
    collector = make_collector(
        {
            "resourcegroupstaggingapi": FakeClient(),
            "budgets": FakeClient(describe_budgets=lambda **_: (_ for _ in ()).throw(RuntimeError("denied"))),
            "organizations": FakeClient(),
            "ec2": FakeClient(),
        }
    )
    profile, metadata = collector._collect_governance_profile(["us-east-1"], "111111111111")

    assert profile.budget_alerts_enabled is False
    assert profile.budget_evidence_state == "unavailable"


def test_collect_governance_profile_detects_config_recorder_and_compliance() -> None:
    """AWS Config recorder/rule-compliance state must be observed, not just inferred elsewhere.

    Every other domain infers posture from individual service APIs; AWS
    Config's own recorder status and rule evaluations are a distinct,
    higher-level signal this collector never checked before.
    """
    config_client = FakeClient(
        describe_configuration_recorder_status={
            "ConfigurationRecordersStatus": [{"name": "default", "recording": True}]
        },
        get_compliance_summary_by_config_rule={
            "ComplianceSummary": {
                "CompliantResourceCount": {"CappedCount": 7},
                "NonCompliantResourceCount": {"CappedCount": 3},
            }
        },
    )
    collector = make_collector(
        {
            "resourcegroupstaggingapi": FakeClient(),
            "budgets": FakeClient(),
            "organizations": FakeClient(),
            "ec2": FakeClient(),
            "config": config_client,
        }
    )
    _profile, metadata = collector._collect_governance_profile(["us-east-1"], "111111111111")

    assert metadata["config_recorder_enabled"] is True
    assert metadata["config_compliant_rule_count"] == 7
    assert metadata["config_noncompliant_rule_count"] == 3


def test_collect_governance_profile_degrades_when_config_not_recording() -> None:
    collector = make_collector(
        {
            "resourcegroupstaggingapi": FakeClient(),
            "budgets": FakeClient(),
            "organizations": FakeClient(),
            "ec2": FakeClient(),
            "config": FakeClient(),
        }
    )
    _profile, metadata = collector._collect_governance_profile(["us-east-1"], "111111111111")

    assert metadata["config_recorder_enabled"] is False
    assert metadata["config_compliant_rule_count"] == 0
    assert metadata["config_noncompliant_rule_count"] == 0


# -- IoT domain ----------------------------------------------------------------


def test_collect_iot_profile_detects_overbroad_policy_and_diagnostics() -> None:
    def get_policy(**kwargs: Any) -> dict[str, Any]:
        return {
            "policyDocument": json.dumps(
                {"Statement": [{"Effect": "Allow", "Action": "iot:*", "Resource": "*"}]}
            )
        }

    def get_topic_rule(**kwargs: Any) -> dict[str, Any]:
        return {"rule": {"actions": [{"cloudwatchMetric": {}}]}}

    iot = FakeClient(
        list_things={"things": [{"thingName": "device1"}]},
        list_thing_groups={"thingGroups": [{"groupName": "group1"}]},
        list_certificates={"certificates": [{"certificateId": "c1"}]},
        list_policies={"policies": [{"policyName": "overbroad-policy"}]},
        get_policy=get_policy,
        list_topic_rules={"rules": [{"ruleName": "rule1"}]},
        get_topic_rule=get_topic_rule,
        list_security_profiles={"securityProfileIdentifiers": [{"name": "sp1"}]},
    )
    ec2 = FakeClient(describe_vpc_endpoints={"VpcEndpoints": [{"VpcEndpointId": "vpce-iot"}]})

    collector = make_collector({"iot": iot, "ec2": ec2})
    profile, metadata = collector._collect_iot_profile(["us-east-1"])

    assert profile is not None
    assert profile.iot_hub_count == 1
    assert profile.device_identity_count == 1
    assert profile.overbroad_shared_access_policy_count == 1
    assert profile.defender_iot_enabled is True
    assert profile.public_network_access_enabled is False
    assert profile.private_endpoint_count == 1
    assert metadata["iot_collection_mode"] == "aws_iot_core_inventory"


def test_collect_iot_profile_returns_none_when_no_things() -> None:
    collector = make_collector({"iot": FakeClient(), "ec2": FakeClient()})
    profile, metadata = collector._collect_iot_profile(["us-east-1"])

    assert profile is None
    assert metadata["iot_collection_mode"] == "default_no_iot_hub_inventory"


# -- End-to-end collect_profiles ------------------------------------------------


def test_collect_profiles_returns_aws_provider_profile() -> None:
    sts = FakeClient(
        get_caller_identity={
            "Account": "222222222222",
            "Arn": "arn:aws:iam::222222222222:user/operator",
        }
    )
    collector = make_collector({"sts": sts})

    profiles = collector.collect_profiles()

    assert len(profiles) == 1
    assert profiles[0].provider == "aws"
    assert profiles[0].metadata["account_id"] == "222222222222"
    assert profiles[0].metadata["collection_mode"] == "aws_boto3_account_inventory"


def test_collect_profiles_filters_by_configured_account_id() -> None:
    sts = FakeClient(
        get_caller_identity={
            "Account": "222222222222",
            "Arn": "arn:aws:iam::222222222222:user/operator",
        }
    )
    settings = AwsCollectorSettings(regions=("us-east-1",), account_id="222222222222")
    collector = make_collector({"sts": sts}, settings=settings)

    profiles = collector.collect_profiles()
    assert profiles[0].metadata["account_id"] == "222222222222"


def test_collect_profiles_raises_when_account_unresolvable() -> None:
    collector = make_collector({"sts": FakeClient()})

    with pytest.raises(ValueError, match="Unable to resolve an AWS account"):
        collector.collect_profiles()


def test_collect_profiles_short_circuits_remaining_calls_when_no_credentials() -> None:
    """Once STS proves there are no usable credentials, no other service should be called.

    This is the fix for the latency problem: previously every domain
    independently re-discovered the missing-credentials failure (each paying
    its own credential-chain lookup cost); now it's discovered once and every
    other call is skipped outright.
    """
    call_count = {"iam": 0}

    def raise_no_credentials(**kwargs: Any) -> Any:
        raise RuntimeError("Unable to locate credentials")

    def track_iam_call(**kwargs: Any) -> dict[str, Any]:
        call_count["iam"] += 1
        return {"Users": [{"UserName": "admin"}]}

    settings = AwsCollectorSettings(regions=("us-east-1",), account_id="333333333333")
    collector = make_collector(
        {
            "sts": FakeClient(get_caller_identity=raise_no_credentials),
            "iam": FakeClient(list_users=track_iam_call),
        },
        settings=settings,
    )

    profiles = collector.collect_profiles()

    assert profiles[0].metadata["account_id"] == "333333333333"
    assert call_count["iam"] == 0, "IAM should never be called once credentials are known to be absent"
    assert collector._has_credentials() is False


# -- Small static helpers --------------------------------------------------------


def test_security_group_rule_helpers_detect_public_exposure() -> None:
    public_rule = {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}
    private_rule = {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "10.0.0.0/8"}]}

    assert AwsCollector._security_group_rule_is_public(public_rule) is True
    assert AwsCollector._security_group_rule_is_public(private_rule) is False
    assert AwsCollector._security_group_rule_exposes_port(public_rule, target_port=22) is True
    assert AwsCollector._security_group_rule_exposes_port(public_rule, target_port=3389) is False


def test_tags_indicate_intentional_public_service() -> None:
    assert AwsCollector._tags_indicate_intentional_public_service(
        {"cris-sme-public-intent": "intentional-public-service"}
    )
    assert not AwsCollector._tags_indicate_intentional_public_service({"env": "prod"})
