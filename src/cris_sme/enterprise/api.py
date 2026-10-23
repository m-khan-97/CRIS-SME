"""Versioned enterprise API. The legacy local runner is not mounted here."""
import asyncio
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import secrets
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.security import OAuth2AuthorizationCodeBearer
from pydantic import BaseModel, ConfigDict, Field, SecretStr, StrictBool
from starlette.middleware.trustedhost import TrustedHostMiddleware

from cris_sme.api.artifact_access import read_regular_file
from cris_sme.enterprise.auth import AccessTokenVerifier
from cris_sme.enterprise.cloud import ROLE, aws_onboarding, verify_connection
from cris_sme.enterprise.store import Rejected, Store, new_id


@dataclass(frozen=True, repr=False)
class Settings:
    issuer: str
    audience: str
    jwks_url: str
    client_id: str
    authorization_url: str
    token_url: str
    artifact_root: Path
    aws_principal_arn: str = ""
    allowed_hosts: tuple[str, ...] = ("127.0.0.1", "localhost")


class ConnectionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    provider: str = Field(pattern="^(aws|azure)$")
    scope_id: str = Field(min_length=1, max_length=36)
    role_arn: str = Field(default="", max_length=600)
    tenant_id: str = Field(default="", max_length=36)
    client_id: str = Field(default="", max_length=36)
    client_secret: SecretStr = SecretStr("")


class MemberInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str = Field(pattern="^(owner|admin|operator|analyst|auditor)$")


class ScanInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connection_id: UUID
    authorization_confirmed: StrictBool


class BodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            return await self.app(scope, receive, send)
        async def collect():
            body = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    raise ValueError("Disconnected")
                data = message.get("body", b"")
                if len(body) + len(data) > 65536:
                    raise OverflowError()
                body.extend(data)
                if not message.get("more_body", False):
                    return bytes(body)
        try:
            body = await asyncio.wait_for(collect(), timeout=10)
        except OverflowError:
            return await JSONResponse({"detail": "Request too large"}, status_code=413)(scope, receive, send)
        except (TimeoutError, ValueError):
            return await JSONResponse({"detail": "Invalid or incomplete request"}, status_code=400)(scope, receive, send)
        delivered = False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()
        await self.app(scope, replay, send)


def create_app(settings: Settings, store: Store, *, verifier=None, cloud_verify=verify_connection):
    if not settings.allowed_hosts or any("*" in host or "/" in host for host in settings.allowed_hosts):
        raise ValueError("Configure exact allowed hostnames")
    for url in (settings.authorization_url, settings.token_url):
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.fragment:
            raise ValueError("Configure HTTPS OIDC authorization and token URLs")
    store.check_schema()
    verifier = verifier or AccessTokenVerifier(settings.issuer, settings.audience, settings.jwks_url)
    oauth = OAuth2AuthorizationCodeBearer(authorizationUrl=settings.authorization_url,
        tokenUrl=settings.token_url, scopes={"openid": "Sign in", "cris.api": "CRIS API"}, auto_error=False)
    app = FastAPI(title="CRIS Enterprise API", version="1.0.0", openapi_url="/api/v1/openapi.json",
                  docs_url="/api/v1/docs", redoc_url=None,
                  swagger_ui_init_oauth={"clientId": settings.client_id, "usePkceWithAuthorizationCodeGrant": True,
                                         "scopes": "openid cris.api"})
    app.add_middleware(BodyLimit)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_hosts))

    @app.middleware("http")
    async def correlation(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Request-ID"] = new_id()
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(Rejected)
    async def rejected(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=exc.status)

    @app.exception_handler(Exception)
    async def unexpected(request, exc):
        return JSONResponse({"detail": "Service operation unavailable"}, status_code=503,
                            headers={"Cache-Control": "no-store", "X-Request-ID": new_id()})

    # Pydantic's default error response may include a submitted secret as input.
    from fastapi.exceptions import RequestValidationError
    @app.exception_handler(RequestValidationError)
    async def invalid(request, exc):
        return JSONResponse({"detail": "Invalid request fields"}, status_code=422)

    def principal(token=Depends(oauth)):
        try:
            return verifier.verify(token)
        except Exception:
            raise HTTPException(401, "Valid API access token required", headers={"WWW-Authenticate": "Bearer"}) from None

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "cris-enterprise"}

    @app.get("/ready")
    def ready():
        try:
            store.check_ready()
        except Exception:
            return JSONResponse({"status": "not_ready"}, status_code=503)
        return {"status": "ready"}

    @app.get("/api/v1/me")
    def me(actor=Depends(principal)):
        return {"issuer": actor.issuer, "subject": actor.subject}

    @app.get("/api/v1/tenants")
    def tenants(actor=Depends(principal)):
        return {"tenants": store.tenants(actor)}

    @app.get("/api/v1/tenants/{tenant}/members")
    def members(tenant: UUID, actor=Depends(principal)):
        return {"members": store.members(str(tenant), actor)}

    @app.put("/api/v1/tenants/{tenant}/members/{subject}")
    def set_member(tenant: UUID, subject: str, body: MemberInput, actor=Depends(principal)):
        if not 1 <= len(subject) <= 255:
            raise HTTPException(422, "Invalid subject")
        store.member(str(tenant), actor, subject, body.role)
        return {"status": "updated"}

    @app.delete("/api/v1/tenants/{tenant}/members/{subject}")
    def remove_member(tenant: UUID, subject: str, actor=Depends(principal)):
        store.member(str(tenant), actor, subject, None)
        return {"status": "removed"}

    @app.post("/api/v1/tenants/{tenant}/connections", status_code=201)
    def create_connection(tenant: UUID, body: ConnectionInput, actor=Depends(principal)):
        config, secret = {}, {}
        if body.provider == "aws":
            match = ROLE.fullmatch(body.role_arn)
            if not match or match.group(1) != "aws" or match.group(2) != body.scope_id or body.client_secret.get_secret_value() or body.tenant_id or body.client_id:
                raise HTTPException(422, "Supply a matching public-partition AWS account and target role")
            config, secret = {"role_arn": body.role_arn}, {"external_id": secrets.token_hex(32)}
        else:
            try:
                scope = str(UUID(body.scope_id))
                config = {"tenant_id": str(UUID(body.tenant_id)), "client_id": str(UUID(body.client_id))}
            except ValueError:
                raise HTTPException(422, "Supply Azure tenant, application and subscription UUIDs") from None
            if body.role_arn or not 1 <= len(body.client_secret.get_secret_value()) <= 4096:
                raise HTTPException(422, "Supply the Azure application credential")
            body.scope_id = scope
            secret = {"client_secret": body.client_secret.get_secret_value()}
        connection_id = store.add_connection(str(tenant), actor, body.name, body.provider, body.scope_id, config, secret)
        return store.connection(str(tenant), actor, connection_id)

    @app.get("/api/v1/tenants/{tenant}/connections")
    def connections(tenant: UUID, actor=Depends(principal)):
        return {"connections": store.connection_list(str(tenant), actor)}

    @app.get("/api/v1/tenants/{tenant}/connections/{connection}/onboarding")
    def onboarding(tenant: UUID, connection: UUID, actor=Depends(principal)):
        row = store.connection(str(tenant), actor, str(connection), secrets=True)
        if row["provider"] == "aws":
            try:
                return aws_onboarding(row, settings.aws_principal_arn)
            except ValueError:
                raise HTTPException(409, "Configure the backend AWS workload role") from None
        return {"tenant_id": row["config"]["tenant_id"], "subscription_id": row["scope_id"],
                "client_id": row["config"]["client_id"], "credential_stored": True,
                "permission_note": "Grant only the documented Azure Reader permissions; Graph access is separate."}

    @app.post("/api/v1/tenants/{tenant}/connections/{connection}/verify")
    def verify(tenant: UUID, connection: UUID, actor=Depends(principal)):
        row = store.connection(str(tenant), actor, str(connection), secrets=True)
        if not row["enabled"]:
            raise HTTPException(409, "Connection is disconnected")
        try:
            cloud_verify(row)
        except Exception:
            raise HTTPException(409, "Target identity verification failed; check the connection and cloud permissions") from None
        store.verified(str(tenant), actor, str(connection))
        return {"status": "verified", "connection_id": str(connection)}

    @app.post("/api/v1/tenants/{tenant}/connections/{connection}/disconnect")
    def disconnect(tenant: UUID, connection: UUID, actor=Depends(principal)):
        store.disconnect(str(tenant), actor, str(connection))
        return {"status": "disconnected"}

    @app.post("/api/v1/tenants/{tenant}/assessments", status_code=202)
    def assess(tenant: UUID, body: ScanInput, actor=Depends(principal), idempotency_key: str = Header()):
        if not body.authorization_confirmed or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", idempotency_key):
            raise HTTPException(422, "Explicit authorization and a valid idempotency key are required")
        return store.submit(str(tenant), actor, str(body.connection_id), idempotency_key)

    @app.get("/api/v1/tenants/{tenant}/assessments")
    def assessment_list(tenant: UUID, actor=Depends(principal)):
        return {"assessments": store.job_list(str(tenant), actor)}

    @app.get("/api/v1/tenants/{tenant}/assessments/{assessment}")
    def assessment(tenant: UUID, assessment: UUID, actor=Depends(principal)):
        return store.job(str(tenant), actor, str(assessment))

    @app.post("/api/v1/tenants/{tenant}/assessments/{assessment}/cancel")
    def cancel(tenant: UUID, assessment: UUID, actor=Depends(principal)):
        store.cancel(str(tenant), actor, str(assessment))
        return store.job(str(tenant), actor, str(assessment))

    @app.get("/api/v1/tenants/{tenant}/artifacts/{artifact}")
    def artifact(tenant: UUID, artifact: UUID, actor=Depends(principal)):
        record = store.artifact(str(tenant), actor, str(artifact))
        data = read_regular_file(settings.artifact_root, Path(record["key"]), max_bytes=32 * 1024 * 1024)
        if len(data) != record["size"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise HTTPException(409, "Artifact integrity check failed")
        return Response(data, media_type="application/octet-stream",
                        headers={"Content-Disposition": 'attachment; filename="' + record["name"] + '"'})

    @app.get("/api/v1/tenants/{tenant}/audit")
    def audit(tenant: UUID, actor=Depends(principal)):
        return {"events": store.audit_list(str(tenant), actor)}

    return app
