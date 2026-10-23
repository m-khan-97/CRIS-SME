"""Version-one enterprise metadata; migration is an explicit operator action."""
from sqlalchemy import (Boolean, Column, ForeignKey, ForeignKeyConstraint, Index, Integer,
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
artifacts = Table("cris_artifacts", metadata, Column("id", String(36), primary_key=True),
                  Column("tenant_id", String(36), nullable=False), Column("job_id", String(36), nullable=False),
                  Column("name", String(160), nullable=False), Column("key", Text, nullable=False),
                  Column("sha256", String(64), nullable=False), Column("size", Integer, nullable=False),
                  ForeignKeyConstraint(["tenant_id", "job_id"], ["cris_jobs.tenant_id", "cris_jobs.id"]),
                  UniqueConstraint("job_id", "name"))
audit = Table("cris_audit", metadata, Column("id", String(36), primary_key=True),
              Column("tenant_id", ForeignKey("cris_tenants.id"), nullable=False),
              Column("subject", String(255), nullable=False), Column("action", String(60), nullable=False),
              Column("resource_id", String(36), nullable=False), Column("created_at", Integer, nullable=False))


def migrate(engine):
    if engine.dialect.name != "postgresql":
        raise ValueError("Enterprise migrations require PostgreSQL")
    with engine.begin() as connection:
        connection.exec_driver_sql("SELECT pg_advisory_xact_lock(754392810)")
        metadata.create_all(connection)
        rows = list(connection.execute(versions.select()).scalars())
        if not rows:
            connection.execute(versions.insert().values(version=1))
        elif rows != [1]:
            raise RuntimeError("Unsupported enterprise schema version")
