import json
import os
import time
import uuid

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
import jwt
import pytest
from sqlalchemy import create_engine

from cris_sme.enterprise.api import Settings, create_app
from cris_sme.enterprise.auth import AccessTokenVerifier, Principal
from cris_sme.enterprise.schema import migrate
from cris_sme.enterprise.store import Store


ISSUER = "https://identity.example"


@pytest.fixture(scope="session")
def signing():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = {**json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key())), "kid": "fixture-key", "use": "sig"}
    return key, {"keys": [jwk]}


@pytest.fixture
def token(signing):
    def issue(subject="owner", *, claims=None, headers=None, remove=(), key=None):
        payload = {"iss": ISSUER, "sub": subject, "aud": "cris-api", "iat": int(time.time()),
                   "exp": int(time.time()) + 300, "scope": "openid cris.api"}
        payload.update(claims or {})
        for name in remove:
            payload.pop(name, None)
        return jwt.encode(payload, key or signing[0], algorithm="RS256", headers={"kid": "fixture-key", **(headers or {})})
    return issue


@pytest.fixture
def verifier(signing):
    return AccessTokenVerifier(ISSUER, "cris-api", "https://identity.example/keys", jwks=signing[1])


@pytest.fixture
def store():
    url = os.environ.get("CRIS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set CRIS_TEST_DATABASE_URL to a disposable PostgreSQL database")
    engine = create_engine(url, pool_size=8, max_overflow=4, hide_parameters=True,
                           connect_args={"options": "-c statement_timeout=5000 -c lock_timeout=1500"})
    schema = "test_" + uuid.uuid4().hex
    with engine.begin() as c:
        c.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
    scoped = engine.execution_options(schema_translate_map={None: schema})
    try:
        migrate(scoped)
        yield Store(scoped, Fernet.generate_key())
    finally:
        with engine.begin() as c:
            c.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        engine.dispose()


@pytest.fixture
def context(store, verifier, token, tmp_path):
    principal = Principal(ISSUER, "owner")
    tenant = store.bootstrap(principal, "Fixture organization")
    settings = Settings(ISSUER, "cris-api", "https://identity.example/keys", "browser-client",
                        "https://identity.example/authorize", "https://identity.example/token", tmp_path,
                        "arn:aws:iam::111111111111:role/cris-backend", ("testserver",))
    verified = []
    app = create_app(settings, store, verifier=verifier, cloud_verify=lambda row: verified.append(row["id"]))
    with TestClient(app, raise_server_exceptions=False) as client:
        client.headers["Authorization"] = "Bearer " + token()
        yield dict(store=store, principal=principal, tenant=tenant, client=client, root=tmp_path,
                   verified=verified, app=app, settings=settings)


def aws_connection(ctx, *, verify=True):
    client, tenant = ctx["client"], ctx["tenant"]
    response = client.post(f"/api/v1/tenants/{tenant}/connections", json={"name": "Fixture AWS", "provider": "aws",
        "scope_id": "123456789012", "role_arn": "arn:aws:iam::123456789012:role/cris-reader"})
    assert response.status_code == 201, response.text
    connection = response.json()["id"]
    if verify:
        assert client.post(f"/api/v1/tenants/{tenant}/connections/{connection}/verify").status_code == 200
    return connection


def submit(ctx, connection, key="fixture-request"):
    response = ctx["client"].post(f"/api/v1/tenants/{ctx['tenant']}/assessments",
        json={"connection_id": connection, "authorization_confirmed": True}, headers={"Idempotency-Key": key})
    assert response.status_code == 202, response.text
    return response.json()
