"""Tenant-scoped PostgreSQL metadata and fenced assessment leases."""
import json
import uuid

from cryptography.fernet import Fernet
from sqlalchemy import and_, create_engine, delete, false, func, insert, or_, select, update

from cris_sme.enterprise import schema as s


ROLES = {"owner", "admin", "operator", "analyst", "auditor"}
ADMIN = {"owner", "admin"}
OPERATE = ADMIN | {"operator"}


class Rejected(Exception):
    def __init__(self, message="Resource not found", status=404):
        super().__init__(message)
        self.status = status


def new_id():
    return str(uuid.uuid4())


class Store:
    def __init__(self, engine, encryption_key):
        if engine.dialect.name != "postgresql":
            raise ValueError("Enterprise storage requires PostgreSQL")
        self.engine, self.cipher = engine, Fernet(encryption_key)

    @classmethod
    def connect(cls, url, encryption_key):
        engine = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5,
                               pool_timeout=5, hide_parameters=True,
                               connect_args={"connect_timeout": 5, "options": "-c statement_timeout=5000 -c lock_timeout=1000"})
        return cls(engine, encryption_key)

    def check_schema(self):
        with self.engine.connect() as c:
            if list(c.execute(select(s.versions.c.version)).scalars()) != [1]:
                raise RuntimeError("Run enterprise migrations before serving requests")

    def check_ready(self):
        self.check_schema()
        with self.engine.connect() as c:
            transaction = c.begin()
            try:
                c.execute(update(s.jobs).where(false()).values(status=s.jobs.c.status))
            finally:
                transaction.rollback()

    def _now(self, c):
        return int(c.execute(select(func.extract("epoch", func.clock_timestamp()))).scalar_one())

    def _access(self, c, tenant, principal, roles=ROLES, *, lock=False):
        query = select(s.tenants.c.id).where(s.tenants.c.id == tenant)
        if lock:
            query = query.with_for_update()
        if c.execute(query).first() is None:
            raise Rejected()
        role = c.execute(select(s.memberships.c.role).where(
            s.memberships.c.tenant_id == tenant, s.memberships.c.issuer == principal.issuer,
            s.memberships.c.subject == principal.subject)).scalar_one_or_none()
        if role is None:
            raise Rejected()
        if role not in roles:
            raise Rejected("Insufficient role", 403)
        return role

    def _audit(self, c, tenant, subject, action, resource):
        c.execute(insert(s.audit).values(id=new_id(), tenant_id=tenant, subject=subject,
                                        action=action, resource_id=resource, created_at=self._now(c)))

    def bootstrap(self, principal, name):
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 200 or not 1 <= len(principal.subject) <= 255:
            raise ValueError("Bootstrap requires an organization name and verified OIDC subject")
        tenant = new_id()
        with self.engine.begin() as c:
            c.execute(insert(s.tenants).values(id=tenant, name=name))
            c.execute(insert(s.memberships).values(tenant_id=tenant, issuer=principal.issuer,
                                                  subject=principal.subject, role="owner"))
            self._audit(c, tenant, principal.subject, "tenant.created", tenant)
        return tenant

    def tenants(self, principal):
        with self.engine.connect() as c:
            return [dict(row) for row in c.execute(select(s.tenants, s.memberships.c.role).join(
                s.memberships, s.memberships.c.tenant_id == s.tenants.c.id).where(
                s.memberships.c.issuer == principal.issuer, s.memberships.c.subject == principal.subject)).mappings()]

    def members(self, tenant, principal):
        with self.engine.connect() as c:
            self._access(c, tenant, principal, ADMIN)
            return [dict(row) for row in c.execute(select(s.memberships).where(s.memberships.c.tenant_id == tenant)).mappings()]

    def member(self, tenant, principal, subject, role):
        if role is not None and role not in ROLES:
            raise Rejected("Invalid role", 422)
        with self.engine.begin() as c:
            caller = self._access(c, tenant, principal, ADMIN, lock=True)
            scope = and_(s.memberships.c.tenant_id == tenant, s.memberships.c.issuer == principal.issuer,
                         s.memberships.c.subject == subject)
            previous = c.execute(select(s.memberships.c.role).where(scope)).scalar_one_or_none()
            if caller != "owner" and (role == "owner" or previous == "owner"):
                raise Rejected("Only owners manage ownership", 403)
            if previous == "owner" and role != "owner":
                owners = c.execute(select(func.count()).select_from(s.memberships).where(
                    s.memberships.c.tenant_id == tenant, s.memberships.c.role == "owner")).scalar_one()
                if owners == 1:
                    raise Rejected("Cannot remove the last owner", 409)
            c.execute(delete(s.memberships).where(scope))
            if role is not None:
                c.execute(insert(s.memberships).values(tenant_id=tenant, issuer=principal.issuer, subject=subject, role=role))
            if role not in OPERATE:
                scope_jobs = and_(s.jobs.c.tenant_id == tenant, s.jobs.c.requested_by_issuer == principal.issuer,
                                  s.jobs.c.requested_by_subject == subject)
                c.execute(update(s.jobs).where(scope_jobs, s.jobs.c.status == "queued")
                          .values(status="cancelled", cancel_requested=True))
                c.execute(update(s.jobs).where(scope_jobs, s.jobs.c.status.in_(["running", "cancelling"]))
                          .values(status="cancelling", cancel_requested=True))
            self._audit(c, tenant, principal.subject, "membership.changed", tenant)

    def add_connection(self, tenant, principal, name, provider, scope_id, config, secret):
        connection_id = new_id()
        with self.engine.begin() as c:
            self._access(c, tenant, principal, ADMIN, lock=True)
            c.execute(insert(s.connections).values(id=connection_id, tenant_id=tenant, name=name,
                provider=provider, scope_id=scope_id, config=json.dumps(config),
                secret=self.cipher.encrypt(json.dumps(secret).encode()).decode(), enabled=True, verified_until=0))
            self._audit(c, tenant, principal.subject, "connection.created", connection_id)
        return connection_id

    def _connection(self, c, tenant, connection_id, *, lock=False):
        query = select(s.connections).where(s.connections.c.tenant_id == tenant, s.connections.c.id == connection_id)
        row = c.execute(query.with_for_update() if lock else query).mappings().first()
        if row is None:
            raise Rejected()
        return dict(row)

    def connection(self, tenant, principal, connection_id, *, secrets=False):
        with self.engine.connect() as c:
            self._access(c, tenant, principal, ADMIN if secrets else ROLES)
            row = self._connection(c, tenant, connection_id)
            if secrets:
                row["secret"] = json.loads(self.cipher.decrypt(row["secret"].encode()))
            else:
                row.pop("secret")
            row["config"] = json.loads(row["config"])
            return row

    def connection_list(self, tenant, principal):
        with self.engine.connect() as c:
            self._access(c, tenant, principal)
            rows = c.execute(select(s.connections.c.id, s.connections.c.name, s.connections.c.provider,
                                    s.connections.c.scope_id, s.connections.c.enabled, s.connections.c.verified_until)
                             .where(s.connections.c.tenant_id == tenant)).mappings()
            return [dict(row) for row in rows]

    def verified(self, tenant, principal, connection_id):
        with self.engine.begin() as c:
            self._access(c, tenant, principal, ADMIN, lock=True)
            row = self._connection(c, tenant, connection_id)
            if not row["enabled"]:
                raise Rejected("Connection is disconnected", 409)
            c.execute(update(s.connections).where(s.connections.c.id == connection_id).values(verified_until=self._now(c) + 3600))
            self._audit(c, tenant, principal.subject, "connection.verified", connection_id)

    def disconnect(self, tenant, principal, connection_id):
        with self.engine.begin() as c:
            self._access(c, tenant, principal, ADMIN, lock=True)
            self._connection(c, tenant, connection_id)
            c.execute(update(s.connections).where(s.connections.c.id == connection_id).values(enabled=False, verified_until=0))
            c.execute(update(s.jobs).where(s.jobs.c.tenant_id == tenant, s.jobs.c.connection_id == connection_id,
                                          s.jobs.c.status == "queued").values(status="cancelled", cancel_requested=True))
            c.execute(update(s.jobs).where(s.jobs.c.tenant_id == tenant, s.jobs.c.connection_id == connection_id,
                s.jobs.c.status.in_(["running", "cancelling"])).values(status="cancelling", cancel_requested=True))
            self._audit(c, tenant, principal.subject, "connection.disconnected", connection_id)

    def submit(self, tenant, principal, connection_id, idempotency_key):
        with self.engine.begin() as c:
            self._access(c, tenant, principal, OPERATE, lock=True)
            previous = c.execute(select(s.jobs).where(s.jobs.c.tenant_id == tenant,
                s.jobs.c.idempotency_key == idempotency_key)).mappings().first()
            if previous:
                if previous["connection_id"] != connection_id:
                    raise Rejected("Idempotency key belongs to another request", 409)
                return self._public_job(previous)
            row = self._connection(c, tenant, connection_id)
            if not row["enabled"] or row["verified_until"] <= self._now(c):
                raise Rejected("Verify an enabled connection before scanning", 409)
            count = c.execute(select(func.count()).select_from(s.jobs).where(s.jobs.c.tenant_id == tenant,
                s.jobs.c.status.in_(["queued", "running", "cancelling"]))).scalar_one()
            if count >= 2:
                raise Rejected("Organization scan capacity reached", 429)
            job = dict(id=new_id(), tenant_id=tenant, connection_id=connection_id, idempotency_key=idempotency_key,
                       requested_by_issuer=principal.issuer, requested_by_subject=principal.subject,
                       status="queued", requested_at=self._now(c), attempt=0, lease_token="", lease_until=0,
                       cancel_requested=False, error_code="")
            c.execute(insert(s.jobs).values(**job))
            self._audit(c, tenant, principal.subject, "assessment.queued", job["id"])
            return self._public_job(job)

    @staticmethod
    def _public_job(row):
        return {key: row[key] for key in ("id", "tenant_id", "connection_id", "status", "requested_at", "attempt", "error_code")}

    def job_list(self, tenant, principal):
        with self.engine.connect() as c:
            self._access(c, tenant, principal)
            return [self._public_job(row) for row in c.execute(select(s.jobs).where(s.jobs.c.tenant_id == tenant)
                .order_by(s.jobs.c.requested_at.desc(), s.jobs.c.id).limit(100)).mappings()]

    def job(self, tenant, principal, job_id):
        with self.engine.connect() as c:
            self._access(c, tenant, principal)
            row = c.execute(select(s.jobs).where(s.jobs.c.tenant_id == tenant, s.jobs.c.id == job_id)).mappings().first()
            if row is None:
                raise Rejected()
            result = self._public_job(row)
            result["artifacts"] = [dict(a) for a in c.execute(select(s.artifacts.c.id, s.artifacts.c.name,
                s.artifacts.c.sha256, s.artifacts.c.size).where(s.artifacts.c.tenant_id == tenant,
                s.artifacts.c.job_id == job_id)).mappings()] if row["status"] == "completed" else []
            return result

    def cancel(self, tenant, principal, job_id):
        with self.engine.begin() as c:
            self._access(c, tenant, principal, OPERATE, lock=True)
            row = c.execute(select(s.jobs).where(s.jobs.c.tenant_id == tenant, s.jobs.c.id == job_id)
                            .with_for_update()).mappings().first()
            if row is None:
                raise Rejected()
            if row["status"] in {"completed", "failed"}:
                raise Rejected("Assessment is already terminal", 409)
            status = "cancelled" if row["status"] in {"queued", "cancelled"} else "cancelling"
            c.execute(update(s.jobs).where(s.jobs.c.id == job_id).values(status=status, cancel_requested=True))
            self._audit(c, tenant, principal.subject, "assessment.cancel_requested", job_id)

    def claim(self, *, lease_seconds=30):
        if not 3 <= lease_seconds <= 300:
            raise ValueError("Lease must be between 3 and 300 seconds")
        with self.engine.begin() as c:
            now = self._now(c)
            c.execute(update(s.jobs).where(s.jobs.c.status == "cancelling", s.jobs.c.lease_until <= now).values(status="cancelled"))
            c.execute(update(s.jobs).where(s.jobs.c.status == "running", s.jobs.c.lease_until <= now,
                s.jobs.c.attempt >= 3).values(status="failed", error_code="attempts_exhausted"))
            allowed = select(s.connections.c.id).where(s.connections.c.enabled.is_(True), s.connections.c.verified_until > now)
            c.execute(update(s.jobs).where(or_(s.jobs.c.status == "queued",
                and_(s.jobs.c.status == "running", s.jobs.c.lease_until <= now)), ~s.jobs.c.connection_id.in_(allowed))
                      .values(status="failed", error_code="connection_unavailable"))
            row = c.execute(select(s.jobs).where(s.jobs.c.connection_id.in_(allowed), or_(s.jobs.c.status == "queued",
                and_(s.jobs.c.status == "running", s.jobs.c.lease_until <= now, s.jobs.c.attempt < 3)))
                .order_by(s.jobs.c.requested_at, s.jobs.c.id).with_for_update(skip_locked=True).limit(1)).mappings().first()
            if row is None:
                return None
            lease = {**row, "status": "running", "attempt": row["attempt"] + 1,
                     "lease_token": new_id(), "lease_until": now + lease_seconds}
            c.execute(update(s.jobs).where(s.jobs.c.id == row["id"]).values(status="running", attempt=lease["attempt"],
                lease_token=lease["lease_token"], lease_until=lease["lease_until"]))
            config = self._connection(c, row["tenant_id"], row["connection_id"])
            config["config"] = json.loads(config["config"])
            config["secret"] = json.loads(self.cipher.decrypt(config["secret"].encode()))
            lease["connection"] = config
            lease["organization_name"] = c.execute(select(s.tenants.c.name).where(s.tenants.c.id == row["tenant_id"])).scalar_one()
            return lease

    def heartbeat(self, lease, *, lease_seconds=30):
        if not 3 <= lease_seconds <= 300:
            raise ValueError("Invalid lease duration")
        with self.engine.begin() as c:
            now = self._now(c)
            enabled = select(s.connections.c.id).where(s.connections.c.enabled.is_(True))
            return c.execute(update(s.jobs).where(s.jobs.c.id == lease["id"], s.jobs.c.lease_token == lease["lease_token"],
                s.jobs.c.status == "running", s.jobs.c.lease_until > now, s.jobs.c.cancel_requested.is_(False),
                s.jobs.c.connection_id.in_(enabled)).values(lease_until=now + lease_seconds)).rowcount == 1

    def finish(self, lease, state, artifact_rows=()):
        if state not in {"completed", "failed", "cancelled"}:
            raise ValueError("Invalid terminal state")
        with self.engine.begin() as c:
            connection = self._connection(c, lease["tenant_id"], lease["connection_id"], lock=True)
            row = c.execute(select(s.jobs).where(s.jobs.c.id == lease["id"], s.jobs.c.lease_token == lease["lease_token"],
                s.jobs.c.lease_until > self._now(c), s.jobs.c.status.in_(["running", "cancelling"]))
                .with_for_update()).mappings().first()
            if row is None:
                return False
            if row["cancel_requested"] or not connection["enabled"]:
                state = "cancelled"
            if state == "completed":
                for artifact in artifact_rows:
                    c.execute(insert(s.artifacts).values(**artifact, tenant_id=row["tenant_id"], job_id=row["id"]))
            c.execute(update(s.jobs).where(s.jobs.c.id == row["id"]).values(status=state,
                error_code="worker_failed" if state == "failed" else "", lease_token="", lease_until=0))
            self._audit(c, row["tenant_id"], "worker", "assessment." + state, row["id"])
            return True

    def artifact(self, tenant, principal, artifact_id):
        with self.engine.connect() as c:
            self._access(c, tenant, principal)
            row = c.execute(select(s.artifacts).join(s.jobs, s.jobs.c.id == s.artifacts.c.job_id).where(
                s.artifacts.c.tenant_id == tenant, s.artifacts.c.id == artifact_id, s.jobs.c.status == "completed")).mappings().first()
            if row is None:
                raise Rejected()
            return dict(row)

    def audit_list(self, tenant, principal):
        with self.engine.connect() as c:
            self._access(c, tenant, principal, ADMIN | {"auditor"})
            return [dict(row) for row in c.execute(select(s.audit).where(s.audit.c.tenant_id == tenant)
                .order_by(s.audit.c.created_at.desc(), s.audit.c.id).limit(100)).mappings()]
