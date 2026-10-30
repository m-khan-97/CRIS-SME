"""Versioned enterprise metadata; migration is an explicit operator action."""
from sqlalchemy import (BigInteger, Boolean, Column, ForeignKey, ForeignKeyConstraint, Index, Integer,
                        MetaData, String, Table, Text, UniqueConstraint)

metadata = MetaData()
versions = Table("cris_schema_version", metadata, Column("version", Integer, primary_key=True))
tenants = Table("cris_tenants", metadata, Column("id", String(36), primary_key=True),
                Column("name", String(200), nullable=False))
memberships = Table("cris_memberships", metadata,
                    Column("tenant_id", ForeignKey("cris_tenants.id"), primary_key=True),
                    Column("issuer", String(512), primary_key=True), Column("subject", String(255), primary_key=True),
                    Column("role", String(20), nullable=False))
connections = Table("cris_connections", metadata, Column("id", String(36), primary_key=True),
                    Column("tenant_id", ForeignKey("cris_tenants.id"), nullable=False),
                    Column("name", String(200), nullable=False), Column("provider", String(10), nullable=False),
                    Column("scope_id", String(36), nullable=False), Column("config", Text, nullable=False),
                    Column("secret", Text, nullable=False), Column("enabled", Boolean, nullable=False),
                    Column("verified_until", Integer, nullable=False, default=0),
                    UniqueConstraint("tenant_id", "id"))
jobs = Table("cris_jobs", metadata, Column("id", String(36), primary_key=True),
             Column("tenant_id", ForeignKey("cris_tenants.id"), nullable=False),
             Column("connection_id", String(36), nullable=False), Column("idempotency_key", String(128), nullable=False),
             Column("requested_by_issuer", String(512), nullable=False),
             Column("requested_by_subject", String(255), nullable=False),
             Column("status", String(20), nullable=False), Column("requested_at", Integer, nullable=False),
             Column("attempt", Integer, nullable=False, default=0), Column("lease_token", String(36), nullable=False, default=""),
             Column("lease_until", Integer, nullable=False, default=0), Column("cancel_requested", Boolean, nullable=False, default=False),
             Column("error_code", String(40), nullable=False, default=""),
             UniqueConstraint("tenant_id", "idempotency_key"), UniqueConstraint("tenant_id", "id"),
             ForeignKeyConstraint(["tenant_id", "connection_id"], ["cris_connections.tenant_id", "cris_connections.id"]))
Index("cris_jobs_claim", jobs.c.status, jobs.c.lease_until, jobs.c.requested_at)
job_tenant_index = Index("cris_jobs_tenant_status", jobs.c.tenant_id, jobs.c.status, jobs.c.requested_at)
artifacts = Table("cris_artifacts", metadata, Column("id", String(36), primary_key=True),
                  Column("tenant_id", String(36), nullable=False), Column("job_id", String(36), nullable=False),
                  Column("name", String(160), nullable=False), Column("key", Text, nullable=False),
                  Column("sha256", String(64), nullable=False), Column("size", Integer, nullable=False),
                  ForeignKeyConstraint(["tenant_id", "job_id"], ["cris_jobs.tenant_id", "cris_jobs.id"]),
                  UniqueConstraint("job_id", "name"))
artifact_tenant_index = Index("cris_artifacts_tenant_job", artifacts.c.tenant_id, artifacts.c.job_id)
audit = Table("cris_audit", metadata, Column("id", String(36), primary_key=True),
              Column("tenant_id", ForeignKey("cris_tenants.id"), nullable=False),
              Column("subject", String(255), nullable=False), Column("action", String(60), nullable=False),
              Column("resource_id", String(36), nullable=False), Column("created_at", Integer, nullable=False))
historical_imports = Table("cris_historical_imports", metadata,
    Column("tenant_id", String(36), nullable=False), Column("job_id", String(36), primary_key=True),
    Column("source_run_id", String(160), nullable=False), Column("source_organization_id", String(512), nullable=False),
    Column("source_sha256", String(64), nullable=False), Column("bundle_sha256", String(64), nullable=False),
    Column("generated_at", String(80), nullable=False), Column("imported_at", Integer, nullable=False),
    Column("provider", String(10), nullable=False), Column("scope_id", String(36), nullable=False),
    Column("reported_source_type", String(200), nullable=False),
    ForeignKeyConstraint(["tenant_id", "job_id"], ["cris_jobs.tenant_id", "cris_jobs.id"]),
    UniqueConstraint("tenant_id", "source_run_id"), UniqueConstraint("tenant_id", "source_sha256"))

holds = Table("cris_retention_holds", metadata,
    Column("tenant_id", String(36), primary_key=True), Column("job_id", String(36), primary_key=True),
    Column("active", Boolean, nullable=False), Column("reason", String(500), nullable=False),
    Column("issuer", String(512), nullable=False), Column("subject", String(255), nullable=False),
    Column("updated_at", Integer, nullable=False),
    ForeignKeyConstraint(["tenant_id", "job_id"], ["cris_jobs.tenant_id", "cris_jobs.id"]))
retention_plans = Table("cris_retention_plans", metadata,
    Column("id", String(36), primary_key=True), Column("tenant_id", ForeignKey("cris_tenants.id"), nullable=False),
    Column("state", String(30), nullable=False), Column("reason", String(500), nullable=False),
    Column("issuer", String(512), nullable=False), Column("subject", String(255), nullable=False),
    Column("approver_issuer", String(512), nullable=False, default=""), Column("approver_subject", String(255), nullable=False, default=""),
    Column("created_at", Integer, nullable=False), Column("expires_at", Integer, nullable=False),
    Column("execute_after", Integer, nullable=False, default=0),
    Column("snapshot", Text, nullable=False), Column("sha256", String(64), nullable=False),
    UniqueConstraint("tenant_id", "id"))
hold_events = Table("cris_retention_hold_events", metadata,
    Column("id", String(36), primary_key=True), Column("tenant_id", String(36), nullable=False),
    Column("job_id", String(36), nullable=False), Column("active", Boolean, nullable=False),
    Column("reason", String(500), nullable=False), Column("issuer", String(512), nullable=False),
    Column("subject", String(255), nullable=False), Column("updated_at", Integer, nullable=False),
    ForeignKeyConstraint(["tenant_id", "job_id"], ["cris_jobs.tenant_id", "cris_jobs.id"]))
retirements = Table("cris_retirements", metadata,
    Column("job_id", String(36), primary_key=True), Column("tenant_id", String(36), nullable=False),
    Column("plan_id", String(36), nullable=False), Column("expired_at", Integer, nullable=False),
    ForeignKeyConstraint(["tenant_id", "job_id"], ["cris_jobs.tenant_id", "cris_jobs.id"]),
    ForeignKeyConstraint(["tenant_id", "plan_id"], ["cris_retention_plans.tenant_id", "cris_retention_plans.id"]),
    UniqueConstraint("tenant_id", "job_id"))
cleanup = Table("cris_retention_cleanup", metadata,
    Column("artifact_id", ForeignKey("cris_artifacts.id"), primary_key=True),
    Column("tenant_id", String(36), nullable=False), Column("job_id", String(36), nullable=False),
    Column("state", String(30), nullable=False), Column("attempts", Integer, nullable=False, default=0),
    Column("error_code", String(40), nullable=False, default=""),
    ForeignKeyConstraint(["tenant_id", "job_id"], ["cris_retirements.tenant_id", "cris_retirements.job_id"]))

limits = Table("cris_tenant_limits", metadata,
    Column("tenant_id", ForeignKey("cris_tenants.id"), primary_key=True),
    Column("quota_bytes", BigInteger, nullable=False), Column("max_artifacts", Integer, nullable=False),
    Column("updated_at", Integer, nullable=False), Column("subject", String(255), nullable=False))
rates = Table("cris_action_rates", metadata,
    Column("tenant_id", ForeignKey("cris_tenants.id"), primary_key=True), Column("action", String(40), primary_key=True),
    Column("window", Integer, nullable=False), Column("used", Integer, nullable=False))
workers = Table("cris_worker_health", metadata, Column("id", String(36), primary_key=True),
    Column("last_seen", Integer, nullable=False), Column("busy", Boolean, nullable=False))

SCHEMA_VERSION = 4


def migrate(engine):
    if engine.dialect.name != "postgresql":
        raise ValueError("Enterprise migrations require PostgreSQL")
    with engine.begin() as connection:
        connection.exec_driver_sql("SELECT pg_advisory_xact_lock(754392810)")
        versions.create(connection, checkfirst=True)
        rows = list(connection.execute(versions.select()).scalars())
        if rows not in ([], [1], [2], [3], [SCHEMA_VERSION]):
            raise RuntimeError("Unsupported enterprise schema version")
        # Additive upgrades retain existing assessment, membership and artifact rows.
        metadata.create_all(connection)
        # create_all skips indexes on existing tables during additive upgrades.
        for index in (job_tenant_index, artifact_tenant_index):
            index.create(connection, checkfirst=True)
        if rows != [SCHEMA_VERSION]:
            connection.execute(versions.delete())
            connection.execute(versions.insert().values(version=SCHEMA_VERSION))
