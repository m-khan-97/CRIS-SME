"""Operator inventory, verified transport and non-destructive retention previews."""
import hashlib
import json
from pathlib import Path

from sqlalchemy import func, select

from cris_sme.api.artifact_access import read_regular_file
from cris_sme.enterprise import schema as s
from cris_sme.enterprise.recovery import _lock
from cris_sme.enterprise.store import ADMIN


def usage(store, tenant, principal):
    with store.engine.connect() as c:
        store._access(c, tenant, principal, ADMIN)
        count, size = c.execute(select(func.count(), func.coalesce(func.sum(s.artifacts.c.size), 0))
                               .where(s.artifacts.c.tenant_id == tenant)).one()
        jobs = c.execute(select(func.count()).select_from(s.jobs).where(s.jobs.c.tenant_id == tenant)).scalar_one()
        return {"registered_artifacts": count, "registered_bytes": size, "assessments": jobs,
                "includes_unreferenced_files": False, "includes_s3_versions": False}


def retention_plan(store, tenant, principal, days: int, *, exclude=(), include_historical=False):
    if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 36500:
        raise ValueError("Retention days must be between 1 and 36500")
    if len(exclude) > 100:
        raise ValueError("At most 100 assessment exclusions are supported")
    with store.engine.connect() as c:
        store._access(c, tenant, principal, ADMIN)
        now = store._now(c)
        rows = list(c.execute(select(s.jobs.c.id, s.jobs.c.requested_at, s.connections.c.provider,
            s.connections.c.scope_id, s.historical_imports.c.imported_at)
            .join(s.connections, (s.connections.c.id == s.jobs.c.connection_id) & (s.connections.c.tenant_id == s.jobs.c.tenant_id))
            .outerjoin(s.historical_imports, (s.historical_imports.c.job_id == s.jobs.c.id) & (s.historical_imports.c.tenant_id == s.jobs.c.tenant_id))
            .where(s.jobs.c.tenant_id == tenant, s.jobs.c.status == "completed")
            .order_by(s.jobs.c.requested_at.desc(), s.jobs.c.id).limit(10001)).mappings())
        if len(rows) > 10000:
            raise ValueError("Retention preview exceeds 10000 completed assessments")
        totals = {row["job_id"]: (row["count"], row["size"]) for row in c.execute(select(s.artifacts.c.job_id,
            func.count().label("count"), func.sum(s.artifacts.c.size).label("size"))
            .where(s.artifacts.c.tenant_id == tenant).group_by(s.artifacts.c.job_id)).mappings()}
        held = set(c.execute(select(s.holds.c.job_id).where(s.holds.c.tenant_id == tenant, s.holds.c.active.is_(True))).scalars())
        expired = set(c.execute(select(s.retirements.c.job_id).where(s.retirements.c.tenant_id == tenant)).scalars())
        latest, candidates = set(), []
        for row in rows:
            scope = (row["provider"], row["scope_id"])
            keep_latest = scope not in latest
            latest.add(scope)
            age_from = row["imported_at"] if row["imported_at"] is not None else row["requested_at"]
            if keep_latest or row["id"] in exclude or row["id"] in held or row["id"] in expired or age_from >= now - days * 86400:
                continue
            if row["imported_at"] is not None and not include_historical:
                continue
            count, size = totals.get(row["id"], (0, 0))
            if count:
                candidates.append({"assessment_id": row["id"], "registered_artifacts": count,
                                   "registered_bytes": size, "age_basis": "imported_at" if row["imported_at"] is not None else "requested_at"})
        payload = {"tenant_id": tenant, "evaluated_at": now, "retention_days": days,
                   "include_historical": bool(include_historical), "excluded_assessments": sorted(set(exclude)),
                   "keep_latest_per_cloud_scope": True, "candidates": candidates, "deletion_executed": False,
                   "legal_hold_checked": True}
        return {**payload, "plan_sha256": hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()}


def copy_registered(store, root: Path, storage, *, apply=False):
    """Local-to-object migration only; never delete the source or change metadata."""
    with store.engine.begin() as c:
        _lock(c)
        if c.execute(select(s.jobs.c.id).where(s.jobs.c.status.not_in(["completed", "failed", "cancelled"])).limit(1)).first():
            raise ValueError("Drain assessments before storage migration")
        if c.execute(select(s.retirements.c.job_id).limit(1)).first():
            raise ValueError("Local quarantine history requires a separately qualified remote migration")
        rows = list(c.execute(select(s.artifacts).limit(10001)).mappings())
        if len(rows) > 10000 or sum(row["size"] for row in rows) > 512 * 1024 * 1024:
            raise ValueError("Storage migration exceeds its bounded batch limit")
        # Validate the complete local source before the first remote publication.
        for row in rows:
            content = read_regular_file(root, Path(row["key"]))
            if len(content) != row["size"] or hashlib.sha256(content).hexdigest() != row["sha256"]:
                raise ValueError("Local migration source failed integrity verification")
        if apply:
            storage.check_ready()
            for row in rows:
                content = read_regular_file(root, Path(row["key"]))
                if len(content) != row["size"] or hashlib.sha256(content).hexdigest() != row["sha256"]:
                    raise ValueError("Local migration source changed before publication")
                storage.publish(row["key"], content)
        return {"registered_artifacts": len(rows), "registered_bytes": sum(row["size"] for row in rows),
                "dry_run": not apply, "source_deleted": False, "metadata_changed": False}
