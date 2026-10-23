"""Explicit target-account verification and isolated provider environments."""
import re

from cris_sme.api.worker_environment import scan_environment


ROLE = re.compile(r"arn:(aws|aws-us-gov|aws-cn):iam::([0-9]{12}):role/[A-Za-z0-9_+=,.@/-]{1,512}\Z")


def verify_connection(connection):
    """Read target identity; never provision or alter customer resources."""
    if connection["provider"] == "aws":
        import boto3
        from botocore.config import Config
        config = Config(connect_timeout=3, read_timeout=10, retries={"max_attempts": 1})
        region = {"aws": "us-east-1", "aws-us-gov": "us-gov-west-1", "aws-cn": "cn-north-1"}[
            ROLE.fullmatch(connection["config"]["role_arn"]).group(1)]
        sts = boto3.Session().client("sts", region_name=region, config=config)
        credentials = sts.assume_role(RoleArn=connection["config"]["role_arn"],
            ExternalId=connection["secret"]["external_id"], RoleSessionName="cris-connection-verification",
            DurationSeconds=900)["Credentials"]
        from botocore.exceptions import ClientError
        for external in (None, "cris-invalid-" + connection["secret"]["external_id"]):
            negative = {"RoleArn": connection["config"]["role_arn"], "RoleSessionName": "cris-trust-verification",
                        "DurationSeconds": 900}
            if external is not None:
                negative["ExternalId"] = external
            try:
                sts.assume_role(**negative)
            except ClientError as exc:
                if exc.response.get("Error", {}).get("Code") not in {"AccessDenied", "AccessDeniedException"}:
                    raise
            else:
                raise ValueError("The target role must enforce its connection-specific external ID")
        target = boto3.client("sts", region_name=region, config=config,
            aws_access_key_id=credentials["AccessKeyId"], aws_secret_access_key=credentials["SecretAccessKey"],
            aws_session_token=credentials["SessionToken"])
        if target.get_caller_identity()["Account"] != connection["scope_id"]:
            raise ValueError("Target account mismatch")
    else:
        from azure.identity import ClientSecretCredential
        from azure.mgmt.resource import SubscriptionClient
        with ClientSecretCredential(tenant_id=connection["config"]["tenant_id"],
            client_id=connection["config"]["client_id"], client_secret=connection["secret"]["client_secret"],
            connection_timeout=5, read_timeout=10, retry_total=1) as credential:
            with SubscriptionClient(credential, connection_timeout=5, read_timeout=10, retry_total=1) as client:
                subscription = client.subscriptions.get(connection["scope_id"])
                if str(subscription.subscription_id).lower() != connection["scope_id"].lower() or (
                    getattr(subscription, "tenant_id", None) and str(subscription.tenant_id).lower() != connection["config"]["tenant_id"].lower()):
                    raise ValueError("Target subscription mismatch")


def aws_onboarding(connection, backend_principal):
    if not ROLE.fullmatch(backend_principal):
        raise ValueError("Configure the backend IAM role before onboarding")
    return {"role_arn": connection["config"]["role_arn"], "external_id": connection["secret"]["external_id"],
        "trust_policy": {"Version": "2012-10-17", "Statement": [{"Effect": "Allow",
            "Principal": {"AWS": backend_principal}, "Action": "sts:AssumeRole",
            "Condition": {"StringEquals": {"sts:ExternalId": connection["secret"]["external_id"]}}}]},
        "permission_note": "Attach only the documented CRIS read permissions; account ID alone grants no access."}


def worker_environment(parent, lease, output, figures):
    connection = lease["connection"]
    provider = connection["provider"]
    organization_name = lease.get("organization_name", connection["name"])
    env = scan_environment(parent, provider)
    # Enterprise scope is connection-owned, never inherited from operator CLI state.
    for key in list(env):
        if key.startswith("CRIS_SME_") or key in {"AWS_PROFILE", "AWS_DEFAULT_PROFILE", "AZURE_SUBSCRIPTION_ID"}:
            env.pop(key)
    env.update(CRIS_SME_COLLECTOR=provider, CRIS_SME_OUTPUT_DIR=str(output), CRIS_SME_FIGURE_DIR=str(figures),
               CRIS_SME_AUTHORIZATION_BASIS="tenant_connection_explicit_authorization", CRIS_SME_ENABLE_NARRATOR="false")
    if provider == "aws":
        env.update(AWS_ACCOUNT_ID=connection["scope_id"], CRIS_SME_AWS_TENANT_SCOPE=connection["scope_id"],
            CRIS_SME_AWS_ROLE_ARN=connection["config"]["role_arn"], CRIS_SME_AWS_EXTERNAL_ID=connection["secret"]["external_id"],
            CRIS_SME_AWS_ORGANIZATION_ID=lease["tenant_id"], CRIS_SME_AWS_ORGANIZATION_NAME=organization_name)
    else:
        env.update(AZURE_TENANT_ID=connection["config"]["tenant_id"], AZURE_CLIENT_ID=connection["config"]["client_id"],
            AZURE_CLIENT_SECRET=connection["secret"]["client_secret"], AZURE_SUBSCRIPTION_ID=connection["scope_id"],
            CRIS_SME_AZURE_TENANT_SCOPE=connection["scope_id"], CRIS_SME_AZURE_ORGANIZATION_ID=lease["tenant_id"],
            CRIS_SME_AZURE_ORGANIZATION_NAME=organization_name)
    return env
