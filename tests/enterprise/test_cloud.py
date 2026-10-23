from types import SimpleNamespace
import uuid

import pytest

from cris_sme.enterprise.cloud import aws_onboarding, verify_connection, worker_environment


def connection(provider="aws"):
    return {"id": str(uuid.uuid4()), "name": "Fixture", "provider": provider, "scope_id": "123456789012",
            "config": {"role_arn": "arn:aws:iam::123456789012:role/reader"}, "secret": {"external_id": "fixture-external"}}


def test_aws_verification_assumes_role_and_checks_target(monkeypatch):
    import boto3
    calls = []
    def assume(**kwargs):
        calls.append(kwargs)
        if kwargs.get("ExternalId") != "fixture-external":
            from botocore.exceptions import ClientError
            raise ClientError({"Error": {"Code": "AccessDenied"}}, "AssumeRole")
        return {"Credentials": {"AccessKeyId": "temporary", "SecretAccessKey": "temporary-secret", "SessionToken": "temporary-session"}}
    monkeypatch.setattr(boto3, "Session", lambda: SimpleNamespace(client=lambda *args, **kwargs: SimpleNamespace(assume_role=assume)))
    monkeypatch.setattr(boto3, "client", lambda *args, **kwargs: SimpleNamespace(get_caller_identity=lambda: {"Account": "123456789012"}))
    verify_connection(connection())
    assert calls[0]["ExternalId"] == "fixture-external" and calls[0]["DurationSeconds"] == 900
    for negative in calls[1:3]:
        assert {key: value for key, value in negative.items() if key != "ExternalId"} == {
            key: value for key, value in calls[0].items() if key != "ExternalId"}
    monkeypatch.setattr(boto3, "client", lambda *args, **kwargs: SimpleNamespace(get_caller_identity=lambda: {"Account": "999999999999"}))
    with pytest.raises(ValueError, match="mismatch"):
        verify_connection(connection())


def test_aws_role_without_external_id_enforcement_is_rejected(monkeypatch):
    import boto3
    credentials = {"AccessKeyId": "temporary", "SecretAccessKey": "secret", "SessionToken": "token"}
    monkeypatch.setattr(boto3, "Session", lambda: SimpleNamespace(client=lambda *args, **kwargs:
        SimpleNamespace(assume_role=lambda **kwargs: {"Credentials": credentials})))
    with pytest.raises(ValueError, match="enforce"):
        verify_connection(connection())


def test_azure_verification_uses_explicit_application_and_scope(monkeypatch):
    import azure.identity
    import azure.mgmt.resource
    scope, tenant, application = [str(uuid.uuid4()) for _ in range(3)]
    row = {"provider": "azure", "scope_id": scope, "config": {"tenant_id": tenant, "client_id": application},
           "secret": {"client_secret": "fixture-secret"}}
    calls = []
    class Credential:
        def __init__(self, **kwargs): calls.append(kwargs)
        def __enter__(self): return self
        def __exit__(self, *args): pass
    class Client:
        def __init__(self, *args, **kwargs):
            self.subscriptions = SimpleNamespace(get=lambda _: SimpleNamespace(subscription_id=scope, tenant_id=tenant))
        def __enter__(self): return self
        def __exit__(self, *args): pass
    monkeypatch.setattr(azure.identity, "ClientSecretCredential", Credential)
    monkeypatch.setattr(azure.mgmt.resource, "SubscriptionClient", Client)
    verify_connection(row)
    assert calls[0]["tenant_id"] == tenant and calls[0]["client_secret"] == "fixture-secret"


def test_trust_document_restricts_backend_role_and_external_id():
    result = aws_onboarding(connection(), "arn:aws:iam::111111111111:role/backend")
    statement = result["trust_policy"]["Statement"][0]
    assert statement["Condition"]["StringEquals"]["sts:ExternalId"] == "fixture-external"
    assert statement["Principal"] == {"AWS": "arn:aws:iam::111111111111:role/backend"}
    with pytest.raises(ValueError):
        aws_onboarding(connection(), "*")


@pytest.mark.parametrize("provider", ["aws", "azure"])
def test_worker_scope_is_not_inherited_from_local_operator(provider, tmp_path):
    row = connection(provider)
    if provider == "azure":
        row.update(scope_id=str(uuid.uuid4()), config={"tenant_id": str(uuid.uuid4()), "client_id": str(uuid.uuid4())},
                   secret={"client_secret": "connection-secret"})
    lease = {"tenant_id": str(uuid.uuid4()), "connection": row}
    env = worker_environment({"PATH": "/usr/bin", "CRIS_SME_COLLECTOR": "mock", "CRIS_SME_ENABLE_NARRATOR": "true",
        "AWS_ACCOUNT_ID": "999999999999", "AWS_PROFILE": "somebody-else", "AZURE_CLIENT_SECRET": "stale-secret",
        "VERCEL_TOKEN": "unrelated-secret", "CRIS_SME_AWS_REGIONS": "wrong-scope"}, lease, tmp_path / "reports", tmp_path / "figures")
    assert env["CRIS_SME_COLLECTOR"] == provider and env["CRIS_SME_ENABLE_NARRATOR"] == "false"
    assert env[f"CRIS_SME_{provider.upper()}_ORGANIZATION_ID"] == lease["tenant_id"]
    assert "VERCEL_TOKEN" not in env and "AWS_PROFILE" not in env and "CRIS_SME_AWS_REGIONS" not in env
    if provider == "azure":
        assert env["AZURE_CLIENT_SECRET"] == "connection-secret" and "AWS_ACCOUNT_ID" not in env
    else:
        assert env["AWS_ACCOUNT_ID"] == "123456789012" and "AZURE_CLIENT_SECRET" not in env
