"""Database-wide admission controls and redacted operational snapshots."""
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import stat

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from cris_sme.enterprise import schema as s

JOB_BYTES = 128 * 1024 * 1024
JOB_FILES = 5
STAGING_BYTES = 256 * 1024 * 1024
STAGING_FILES = 2048
MIN_FREE_BYTES = 256 * 1024 * 1024
DEFAULT_QUOTA_BYTES = 1024 * 1024 * 1024
DEFAULT_MAX_ARTIFACTS = 10_000
PENDING = ("queued", "running", "cancelling")
RATES = {"scan_submission": (24, 3600), "connection_verification": (6, 60),
         "connection_creation": (20, 3600), "retention_proposal": (12, 3600)}


def policy(c, tenant):
    row = c.execute(select(s.limits).where(s.limits.c.tenant_id == tenant)).mappings().first()
    return {"quota_bytes": row["quota_bytes"] if row else DEFAULT_QUOTA_BYTES,
            "max_artifacts": row["max_artifacts"] if row else DEFAULT_MAX_ARTIFACTS}


def budget(c, tenant, *, exclude_job=None):
    count, size = c.execute(select(func.count(), func.coalesce(func.sum(s.artifacts.c.size), 0))
                           .where(s.artifacts.c.tenant_id == tenant)).one()
    query = select(func.count()).select_from(s.jobs).where(s.jobs.c.tenant_id == tenant, s.jobs.c.status.in_(PENDING))
    if exclude_job:
        query = query.where(s.jobs.c.id != exclude_job)
    pending = c.execute(query).scalar_one()
    return {**policy(c, tenant), "registered_bytes": size, "registered_artifacts": count,
            "reserved_bytes": pending * JOB_BYTES, "reserved_artifacts": pending * JOB_FILES,
            "pending_assessments": pending}


def check_budget(c, tenant, extra_bytes, extra_files, *, exclude_job=None):
    from cris_sme.enterprise.store import Rejected
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in (extra_bytes, extra_files)):
        raise ValueError("Invalid publication size")
    usage = budget(c, tenant, exclude_job=exclude_job)
    if usage["registered_bytes"] + usage["reserved_bytes"] + extra_bytes > usage["quota_bytes"] or (
        usage["registered_artifacts"] + usage["reserved_artifacts"] + extra_files > usage["max_artifacts"]):
        raise Rejected("Organization storage capacity reached", 429, retry_after=60)


def charge(store, c, tenant, action):
    """Caller must hold the tenant row lock; denials cannot extend the window."""
    from cris_sme.enterprise.store import Rejected
    maximum, period = RATES[action]
    now = store._now(c)
    window = now // period
    row = c.execute(select(s.rates).where(s.rates.c.tenant_id == tenant, s.rates.c.action == action)).mappings().first()
    used = row["used"] if row and row["window"] == window else 0
    if used >= maximum:
        raise Rejected("Organization action rate reached", 429, retry_after=period - now % period)
    values = dict(window=window, used=used + 1)
    if row:
        c.execute(update(s.rates).where(s.rates.c.tenant_id == tenant, s.rates.c.action == action).values(**values))
    else:
        c.execute(insert(s.rates).values(tenant_id=tenant, action=action, **values))


def set_limits(store, tenant, actor, quota_bytes, max_artifacts):
    from cris_sme.enterprise.store import Rejected
    if any(isinstance(v, bool) or not isinstance(v, int) for v in (quota_bytes, max_artifacts)) or not (
        JOB_BYTES <= quota_bytes <= 1024 ** 4 and JOB_FILES <= max_artifacts <= 1_000_000):
        raise ValueError("Invalid tenant storage limits")
    with store.engine.begin() as c:
        store._access(c, tenant, actor, {"owner"}, lock=True)
        if c.execute(select(s.jobs.c.id).where(s.jobs.c.tenant_id == tenant, s.jobs.c.status.in_(PENDING)).limit(1)).first():
            raise Rejected("Drain organization assessments before changing limits", 409)
        values = dict(quota_bytes=quota_bytes, max_artifacts=max_artifacts, updated_at=store._now(c), subject=actor.subject)
        c.execute(pg_insert(s.limits).values(tenant_id=tenant, **values).on_conflict_do_update(
            index_elements=[s.limits.c.tenant_id], set_=values))
        store._audit(c, tenant, actor.subject, "operations.limits_changed", tenant)
        return {"quota_bytes": quota_bytes, "max_artifacts": max_artifacts}


def tenant_status(store, tenant, actor):
    with store.engine.connect() as c:
        store._access(c, tenant, actor, {"owner", "admin", "auditor"})
        now = store._now(c)
        statuses = {state: 0 for state in ("queued", "running", "cancelling", "completed", "failed", "cancelled")}
        for row in c.execute(select(s.jobs.c.status, func.count()).where(s.jobs.c.tenant_id == tenant).group_by(s.jobs.c.status)):
            if row[0] in statuses:
                statuses[row[0]] = row[1]
        oldest = c.execute(select(func.min(s.jobs.c.requested_at)).where(s.jobs.c.tenant_id == tenant, s.jobs.c.status == "queued")).scalar_one()
        stale = c.execute(select(func.count()).select_from(s.jobs).where(s.jobs.c.tenant_id == tenant,
            s.jobs.c.status.in_(["running", "cancelling"]), s.jobs.c.lease_until <= now)).scalar_one()
        rate_rows = {row["action"]: row for row in c.execute(select(s.rates).where(s.rates.c.tenant_id == tenant)).mappings()}
        rates = {}
        for action, (maximum, period) in RATES.items():
            record = rate_rows.get(action)
            used = record["used"] if record and record["window"] == now // period else 0
            rates[action] = {"used": used, "limit": maximum, "remaining": max(0, maximum - used), "reset_after_seconds": period - now % period}
        return {**budget(c, tenant), "assessments": statuses, "oldest_queue_age_seconds": max(0, now - oldest) if oldest else 0,
                "expired_leases": stale, "rate_limits": rates}


def touch_worker(store, identifier, busy):
    with store.engine.begin() as c:
        now = store._now(c)
        values = dict(last_seen=now, busy=busy)
        c.execute(pg_insert(s.workers).values(id=identifier, **values).on_conflict_do_update(index_elements=[s.workers.c.id], set_=values))
        c.execute(delete(s.workers).where(s.workers.c.last_seen < now - 7 * 86400))


def operator_status(store, root):
    with store.engine.connect() as c:
        now = store._now(c)
        fresh = s.workers.c.last_seen > now - 30
        available = c.execute(select(func.count()).select_from(s.workers).where(fresh)).scalar_one()
        busy = c.execute(select(func.count()).select_from(s.workers).where(fresh, s.workers.c.busy.is_(True))).scalar_one()
        stale = c.execute(select(func.count()).select_from(s.workers).where(~fresh)).scalar_one()
        statuses = {row[0]: row[1] for row in c.execute(select(s.jobs.c.status, func.count()).group_by(s.jobs.c.status))}
        disk = shutil.disk_usage(root)
        return {"workers_fresh": available, "workers_busy": busy, "workers_stale": stale,
                "queued": statuses.get("queued", 0), "running": statuses.get("running", 0), "failed": statuses.get("failed", 0),
                "disk_free_bytes": disk.free, "disk_pressure": disk.free < MIN_FREE_BYTES,
                "minimum_free_bytes": MIN_FREE_BYTES, "redacted": True}


class ResourceLimit(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__("Worker resource guard reached")


def check_disk(root, *, required_bytes=0):
    if shutil.disk_usage(root).free < MIN_FREE_BYTES + required_bytes:
        raise ResourceLimit("disk_pressure")


def _tree_size(paths, byte_limit, file_limit):
    total, count, seen = 0, 0, set()
    for root in paths:
        if root.is_symlink():
            raise ResourceLimit("staging_limit")
        if not root.exists():
            continue
        for parent, directories, files in os.walk(root, followlinks=False):
            count += len(directories)
            for name in files:
                try:
                    info = (Path(parent) / name).lstat()
                except FileNotFoundError:
                    continue
                identity = (info.st_dev, info.st_ino)
                if identity in seen:
                    continue
                seen.add(identity)
                count += 1
                if stat.S_ISREG(info.st_mode):
                    total += info.st_size
                if total > byte_limit or count > file_limit:
                    raise ResourceLimit("staging_limit")
            if count > file_limit:
                raise ResourceLimit("staging_limit")


@dataclass
class WorkspaceGuard:
    root: Path
    tenant: str
    attempt: Path
    quota_bytes: int
    max_artifacts: int

    def check(self):
        check_disk(self.root)
        _tree_size([self.attempt], STAGING_BYTES, STAGING_FILES)
        _tree_size([self.root / self.tenant, self.root / "retention_quarantine" / self.tenant],
                   self.quota_bytes + STAGING_BYTES, self.max_artifacts + STAGING_FILES)
