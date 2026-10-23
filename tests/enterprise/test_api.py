import uuid

import pytest
from sqlalchemy import select

from cris_sme.enterprise.auth import Principal
from cris_sme.enterprise import schema as s
from tests.enterprise.conftest import ISSUER, aws_connection, submit


def base(ctx):
    return f"/api/v1/tenants/{ctx['tenant']}"


def test_openapi_and_bearer_boundary(context):
    client = context["client"]
    spec = client.get("/api/v1/openapi.json").json()
    assert spec["info"]["version"] == "1.0.0"
    assert "authorizationCode" in str(spec["components"]["securitySchemes"])
    assert "secret" not in spec["components"]["schemas"]["ConnectionView"]["properties"]
    assert "cancelling" in spec["components"]["schemas"]["JobView"]["properties"]["status"]["enum"]
    assert client.get("/api/v1/docs").status_code == 200
    assert client.get("/ready").json() == {"status": "ready"}
    assert client.get("/api/v1/tenants").json()["tenants"][0]["id"] == context["tenant"]
    client.headers.pop("Authorization")
    for path in ("/api/v1/me", "/api/v1/tenants", base(context) + "/assessments"):
        assert client.get(path).status_code == 401
    assert client.get("/api/report-artifact?path=/etc/passwd").status_code == 404


@pytest.mark.parametrize("resource", ["connections", "assessments", "members", "audit"])
def test_tenant_membership_required(context, resource):
    other = context["store"].bootstrap(Principal(ISSUER, "other"), "Same display name")
    assert context["client"].get(f"/api/v1/tenants/{other}/{resource}").status_code == 404


@pytest.mark.parametrize("role", ["admin", "operator", "analyst", "auditor"])
def test_rbac_and_membership_revocation(context, token, role):
    store, tenant, client = context["store"], context["tenant"], context["client"]
    store.member(tenant, context["principal"], "member", role)
    connection = aws_connection(context)
    client.headers["Authorization"] = "Bearer " + token("member", claims={"roles": ["owner"]})
    assert client.get(base(context) + "/assessments").status_code == 200
    response = client.post(base(context) + "/assessments", headers={"Idempotency-Key": "role-test"},
                           json={"connection_id": connection, "authorization_confirmed": True})
    assert response.status_code == (202 if role in {"admin", "operator"} else 403)
    response = client.put(base(context) + "/members/elevated", json={"role": "owner"})
    assert response.status_code == 403
    store.member(tenant, context["principal"], "member", None)
    assert client.get(base(context) + "/assessments").status_code == 404


def test_last_owner_and_issuer_subject_binding(context, token):
    client, store, tenant = context["client"], context["store"], context["tenant"]
    assert client.delete(base(context) + "/members/owner").status_code == 409
    assert client.put(base(context) + "/members/owner", json={"role": "auditor"}).status_code == 409
    foreign = Principal("https://another.example", "owner")
    assert store.tenants(foreign) == []
    store.member(tenant, context["principal"], "second", "owner")
    assert client.delete(base(context) + "/members/owner").status_code == 200
    assert client.get(base(context) + "/connections").status_code == 404


def test_connection_verification_is_required_and_secrets_are_encrypted(context):
    connection = aws_connection(context, verify=False)
    client = context["client"]
    payload = {"connection_id": connection, "authorization_confirmed": True}
    assert client.post(base(context) + "/assessments", json=payload, headers={"Idempotency-Key": "a"}).status_code == 409
    assert client.post(base(context) + f"/connections/{connection}/verify").status_code == 200
    onboarding = client.get(base(context) + f"/connections/{connection}/onboarding").json()
    external = onboarding["external_id"]
    assert len(external) > 32
    assert external in str(onboarding["trust_policy"])
    assert external not in client.get(base(context) + "/connections").text
    with context["store"].engine.connect() as c:
        stored = c.execute(select(s.connections.c.secret).where(s.connections.c.id == connection)).scalar_one()
        assert external not in stored
    job = submit(context, connection)
    assert job["status"] == "queued"


def test_azure_onboarding_and_secret_validation(context):
    client = context["client"]
    scope, tenant, application = [str(uuid.uuid4()) for _ in range(3)]
    payload = dict(name="Azure", provider="azure", scope_id=scope, tenant_id=tenant,
                   client_id=application, client_secret="fixture-secret")
    response = client.post(base(context) + "/connections", json=payload)
    assert response.status_code == 201, response.text
    assert "fixture-secret" not in response.text
    connection = response.json()["id"]
    details = client.get(base(context) + f"/connections/{connection}/onboarding").json()
    assert details["subscription_id"] == scope and details["credential_stored"]
    payload["client_secret"] = "s" * 5000
    response = client.post(base(context) + "/connections", json=payload)
    assert response.status_code == 422 and "s" * 100 not in response.text
    payload["unknown_secret_field"] = "never-echo"
    response = client.post(base(context) + "/connections", json=payload)
    assert response.status_code == 422 and "never-echo" not in response.text


def test_idempotency_quota_and_disconnect(context):
    connection = aws_connection(context)
    first = submit(context, connection, "first")
    assert submit(context, connection, "first")["id"] == first["id"]
    second = submit(context, connection, "second")
    response = context["client"].post(base(context) + "/assessments", headers={"Idempotency-Key": "third"},
        json={"connection_id": connection, "authorization_confirmed": True})
    assert response.status_code == 429
    assert context["client"].post(base(context) + f"/connections/{connection}/disconnect").status_code == 200
    for job in (first, second):
        assert context["client"].get(base(context) + f"/assessments/{job['id']}").json()["status"] == "cancelled"
    assert context["store"].claim() is None


def test_idempotency_key_cannot_change_connection(context):
    first = aws_connection(context)
    second = aws_connection(context)
    submit(context, first)
    response = context["client"].post(base(context) + "/assessments", headers={"Idempotency-Key": "fixture-request"},
        json={"connection_id": second, "authorization_confirmed": True})
    assert response.status_code == 409


@pytest.mark.parametrize("authorization", [False, "true", 1, None])
def test_explicit_scan_authorization(context, authorization):
    connection = aws_connection(context)
    response = context["client"].post(base(context) + "/assessments", headers={"Idempotency-Key": "authorization"},
        json={"connection_id": connection, "authorization_confirmed": authorization})
    assert response.status_code == 422


def test_cross_tenant_objects_and_credentials_are_not_reusable(context):
    connection = aws_connection(context)
    job = submit(context, connection)
    other = context["store"].bootstrap(context["principal"], "Another owned tenant")
    client = context["client"]
    assert client.get(f"/api/v1/tenants/{other}/assessments/{job['id']}").status_code == 404
    assert client.post(f"/api/v1/tenants/{other}/connections/{connection}/verify").status_code == 404
    assert client.post(f"/api/v1/tenants/{other}/assessments", headers={"Idempotency-Key": "cross"},
        json={"connection_id": connection, "authorization_confirmed": True}).status_code == 404


def test_body_limit_host_and_private_errors(context, monkeypatch):
    client = context["client"]
    response = client.post(base(context) + "/connections", content=b"x" * 65537,
                           headers={"Content-Type": "application/json"})
    assert response.status_code == 413
    assert client.get("/health", headers={"Host": "evil.example"}).status_code == 400
    def fail(*args): raise RuntimeError("private-password-or-sql")
    monkeypatch.setattr(context["store"], "tenants", fail)
    response = client.get("/api/v1/tenants")
    assert response.status_code == 503 and "private-password" not in response.text


def test_audit_records_actions_not_credentials(context):
    connection = aws_connection(context)
    job = submit(context, connection)
    context["client"].post(base(context) + f"/assessments/{job['id']}/cancel")
    response = context["client"].get(base(context) + "/audit")
    assert response.status_code == 200
    actions = {row["action"] for row in response.json()["events"]}
    assert {"connection.created", "connection.verified", "assessment.queued", "assessment.cancel_requested"} <= actions
    assert "external_id" not in response.text and "client_secret" not in response.text


def test_readiness_does_not_accept_readonly_postgresql(context):
    store = context["store"]
    original = store.engine
    store.engine = original.execution_options(postgresql_readonly=True)
    try:
        assert context["client"].get("/ready").status_code == 503
        assert context["client"].get("/health").status_code == 200
    finally:
        store.engine = original
