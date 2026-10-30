"""Two-person retention authorization and recoverable local quarantine, never erasure."""
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, insert, select, update

from cris_sme.api.artifact_access import read_regular_file
from cris_sme.enterprise import schema as s
from cris_sme.enterprise.auth import Principal
from cris_sme.enterprise.storage import LocalStorage
from cris_sme.enterprise.storage_operations import retention_plan
from cris_sme.enterprise.store import ADMIN, Rejected, new_id
from cris_sme.enterprise.operations import charge

COOLING_SECONDS = 86400
PLAN_LIFETIME = 7 * 86400


def _job(c, tenant, job):
    row = c.execute(select(s.jobs).where(s.jobs.c.tenant_id == tenant, s.jobs.c.id == job)).mappings().first()
    if row is None:
        raise Rejected()
    return row


def _plan(c, tenant, plan):
    row = c.execute(select(s.retention_plans).where(s.retention_plans.c.tenant_id == tenant,
                    s.retention_plans.c.id == plan).with_for_update()).mappings().first()
    if row is None:
        raise Rejected()
    result = dict(row)
    if hashlib.sha256(result["snapshot"].encode()).hexdigest() != result["sha256"]:
        raise Rejected("Proposal integrity check failed", 409)
    return result


def hold(store, tenant, actor, job, reason, *, active=True):
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
        raise ValueError("A reason of 1-500 characters is required")
    with store.engine.begin() as c:
        store._access(c, tenant, actor, ADMIN if active else {"owner"}, lock=True)
        _job(c, tenant, job)
        old = c.execute(select(s.holds).where(s.holds.c.tenant_id == tenant, s.holds.c.job_id == job)).first()
        values = dict(active=active, reason=reason.strip(), issuer=actor.issuer, subject=actor.subject, updated_at=store._now(c))
        if old:
            c.execute(update(s.holds).where(s.holds.c.tenant_id == tenant, s.holds.c.job_id == job).values(**values))
        else:
            c.execute(insert(s.holds).values(tenant_id=tenant, job_id=job, **values))
        c.execute(insert(s.hold_events).values(id=new_id(), tenant_id=tenant, job_id=job, **values))
        store._audit(c, tenant, actor.subject, "retention.hold_set" if active else "retention.hold_released", job)
        return {"job_id": job, **values}


def list_state(store, tenant, actor):
    with store.engine.connect() as c:
        store._access(c, tenant, actor, ADMIN)
        plans = [dict(row) for row in c.execute(select(s.retention_plans).where(s.retention_plans.c.tenant_id == tenant)
                 .order_by(s.retention_plans.c.created_at.desc(), s.retention_plans.c.id).limit(100)).mappings()]
        for row in plans:
            row["snapshot"] = None
        holds = [dict(row) for row in c.execute(select(s.holds).where(s.holds.c.tenant_id == tenant).limit(1000)).mappings()]
        return {"plans": plans, "holds": holds, "permanent_erasure": False}


def get_plan(store, tenant, actor, plan):
    with store.engine.connect() as c:
        store._access(c, tenant, actor, ADMIN)
        row = _plan(c, tenant, plan)
        row["snapshot"] = json.loads(row["snapshot"])
        return row


def _artifacts(c, tenant, jobs):
    return [dict(row) for row in c.execute(select(s.artifacts).where(s.artifacts.c.tenant_id == tenant,
        s.artifacts.c.job_id.in_(jobs)).order_by(s.artifacts.c.id)).mappings()]


def propose(store, tenant, actor, days, reason, *, exclude=(), include_historical=False):
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
        raise ValueError("A reason of 1-500 characters is required")
    with store.engine.begin() as c:
        store._access(c, tenant, actor, ADMIN, lock=True)
        charge(store, c, tenant, "retention_proposal")
    preview = retention_plan(store, tenant, actor, days, exclude=exclude, include_historical=include_historical)
    jobs = [row["assessment_id"] for row in preview["candidates"]]
    if not jobs:
        raise Rejected("No eligible assessments", 409)
    with store.engine.begin() as c:
        store._access(c, tenant, actor, ADMIN, lock=True)
        if c.execute(select(s.holds.c.job_id).where(s.holds.c.tenant_id == tenant,
                     s.holds.c.job_id.in_(jobs), s.holds.c.active.is_(True))).first():
            raise Rejected("A selected assessment is held", 409)
        rows = _artifacts(c, tenant, jobs)
        snapshot = json.dumps({"preview": preview, "artifacts": rows}, sort_keys=True)
        if len(snapshot.encode()) > 2 * 1024 * 1024 or len(rows) > 1000:
            raise Rejected("Retention proposal exceeds batch limits", 409)
        now, identifier = store._now(c), new_id()
        values = dict(id=identifier, tenant_id=tenant, state="proposed", reason=reason.strip(), issuer=actor.issuer,
            subject=actor.subject, created_at=now, expires_at=now + PLAN_LIFETIME, execute_after=0,
            approver_issuer="", approver_subject="", snapshot=snapshot, sha256=hashlib.sha256(snapshot.encode()).hexdigest())
        c.execute(insert(s.retention_plans).values(**values))
        store._audit(c, tenant, actor.subject, "retention.proposed", identifier)
        return {**values, "snapshot": json.loads(snapshot)}


def decide(store, tenant, actor, plan, digest, *, approve=True):
    with store.engine.begin() as c:
        store._access(c, tenant, actor, {"owner"}, lock=True)
        row = _plan(c, tenant, plan)
        if row["sha256"] != digest or row["state"] not in {"proposed", "approved"} or store._now(c) >= row["expires_at"]:
            raise Rejected("Proposal is stale or unavailable", 409)
        if approve:
            if (row["issuer"], row["subject"]) == (actor.issuer, actor.subject):
                raise Rejected("A different owner must approve the proposal", 403)
            if row["state"] == "approved":
                return {"id": plan, "state": "approved", "execute_after": row["execute_after"]}
            values = dict(state="approved", approver_issuer=actor.issuer, approver_subject=actor.subject,
                          execute_after=store._now(c) + COOLING_SECONDS)
        else:
            values = dict(state="withdrawn")
        c.execute(update(s.retention_plans).where(s.retention_plans.c.id == plan).values(**values))
        store._audit(c, tenant, actor.subject, "retention.approved" if approve else "retention.withdrawn", plan)
        return {"id": plan, **values}


def expire(store, tenant, actor, plan, digest, storage):
    if not isinstance(storage, LocalStorage):
        raise Rejected("Retention execution is restricted to local quarantine; S3 cleanup is not qualified", 409)
    with store.engine.begin() as c:
        store._access(c, tenant, actor, {"owner"}, lock=True)
        row = _plan(c, tenant, plan)
        if row["sha256"] != digest:
            raise Rejected("Proposal digest mismatch", 409)
        if row["state"] == "expired":
            return {"id": plan, "state": "expired"}
        now = store._now(c)
        if row["state"] != "approved" or not row["execute_after"] <= now < row["expires_at"]:
            raise Rejected("Approval is unavailable or cooling period has not elapsed", 409)
        store._access(c, tenant, Principal(row["issuer"], row["subject"]), ADMIN)
        store._access(c, tenant, Principal(row["approver_issuer"], row["approver_subject"]), {"owner"})
        snapshot = json.loads(row["snapshot"])
        jobs = [item["assessment_id"] for item in snapshot["preview"]["candidates"]]
        if c.execute(select(s.holds.c.job_id).where(s.holds.c.tenant_id == tenant,
                     s.holds.c.job_id.in_(jobs), s.holds.c.active.is_(True))).first():
            raise Rejected("A selected assessment is held", 409)
        if any(_job(c, tenant, job)["status"] != "completed" for job in jobs):
            raise Rejected("Assessment state changed", 409)
        if _artifacts(c, tenant, jobs) != snapshot["artifacts"]:
            raise Rejected("Artifact inventory changed; propose again", 409)
        # Recheck current scope/latest/exclusion guards, not just the old preview.
        preview = retention_plan(store, tenant, actor, snapshot["preview"]["retention_days"],
            exclude=snapshot["preview"]["excluded_assessments"], include_historical=snapshot["preview"]["include_historical"])
        if not set(jobs).issubset({item["assessment_id"] for item in preview["candidates"]}):
            raise Rejected("Retention eligibility changed; propose again", 409)
        for job in jobs:
            c.execute(insert(s.retirements).values(tenant_id=tenant, job_id=job, plan_id=plan, expired_at=now))
        for artifact in snapshot["artifacts"]:
            c.execute(insert(s.cleanup).values(artifact_id=artifact["id"], tenant_id=tenant, job_id=artifact["job_id"],
                                             state="pending", attempts=0, error_code=""))
        c.execute(update(s.retention_plans).where(s.retention_plans.c.id == plan).values(state="expired"))
        store._audit(c, tenant, actor.subject, "retention.expired", plan)
        return {"id": plan, "state": "expired", "assessments": len(jobs), "artifacts": len(snapshot["artifacts"])}


def _directory(root, parts, *, create=False):
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts:
            if create:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _quarantine(root, artifact, plan):
    for identifier in (artifact["tenant_id"], artifact["job_id"], artifact["id"], plan):
        if str(UUID(identifier)) != identifier:
            raise ValueError("Invalid quarantine identifier")
    relative = Path(artifact["key"])
    if relative.is_absolute() or str(relative) != artifact["key"] or relative.parts[:2] != (artifact["tenant_id"], artifact["job_id"]) or any(p.startswith(".") for p in relative.parts):
        raise ValueError("Invalid quarantine source namespace")
    target = Path("retention_quarantine") / artifact["tenant_id"] / plan / artifact["id"]
    def verify(path):
        raw = read_regular_file(root, path)
        if len(raw) != artifact["size"] or hashlib.sha256(raw).hexdigest() != artifact["sha256"]:
            raise ValueError("Quarantine integrity check failed")
    try:
        verify(relative)
    except FileNotFoundError:
        verify(target)
        return
    source_fd = _directory(root, relative.parts[:-1])
    try:
        destination_fd = _directory(root, target.parts[:-1], create=True)
        try:
            try:
                os.link(relative.name, target.name, src_dir_fd=source_fd, dst_dir_fd=destination_fd, follow_symlinks=False)
            except FileExistsError:
                pass
            verify(target)
            verify(relative)
            content_fd = os.open(target.name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=destination_fd)
            try:
                os.fsync(content_fd)
            finally:
                os.close(content_fd)
            os.fsync(destination_fd)
            os.unlink(relative.name, dir_fd=source_fd)
            os.fsync(source_fd)
        finally:
            os.close(destination_fd)
    finally:
        os.close(source_fd)


def cleanup_local(store, tenant, actor, plan, storage, *, limit=20):
    if not isinstance(storage, LocalStorage) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise ValueError("Cleanup requires local storage and a batch limit of 1-100")
    result = {"quarantined": 0, "held": 0, "failed": 0, "permanent_erasure": False}
    with store.engine.begin() as c:
        store._access(c, tenant, actor, {"owner"}, lock=True)
        if _plan(c, tenant, plan)["state"] != "expired":
            raise Rejected("Assessment expiry is required before cleanup", 409)
        held_jobs = select(s.holds.c.job_id).where(s.holds.c.tenant_id == tenant, s.holds.c.active.is_(True))
        result["held"] = c.execute(select(func.count()).select_from(s.cleanup).join(s.retirements,
            s.retirements.c.job_id == s.cleanup.c.job_id).where(s.cleanup.c.tenant_id == tenant,
            s.retirements.c.plan_id == plan, s.cleanup.c.state.in_(["pending", "error"]),
            s.cleanup.c.job_id.in_(held_jobs))).scalar_one()
        rows = c.execute(select(s.cleanup, s.artifacts.c.name, s.artifacts.c.key, s.artifacts.c.sha256,
                                s.artifacts.c.size, s.artifacts.c.id)
            .join(s.artifacts, s.artifacts.c.id == s.cleanup.c.artifact_id)
            .join(s.retirements, s.retirements.c.job_id == s.cleanup.c.job_id)
            .where(s.cleanup.c.tenant_id == tenant, s.retirements.c.tenant_id == tenant,
                   s.retirements.c.plan_id == plan, s.cleanup.c.state.in_(["pending", "error"]))
            .where(~s.cleanup.c.job_id.in_(held_jobs))
            .order_by(s.cleanup.c.artifact_id).limit(limit)).mappings().all()
        for row in rows:
            if c.execute(select(s.holds.c.job_id).where(s.holds.c.tenant_id == tenant,
                         s.holds.c.job_id == row["job_id"], s.holds.c.active.is_(True))).first():
                result["held"] += 1
                continue
            try:
                _quarantine(storage.root, row, plan)
                state, error = "quarantined", ""
                result["quarantined"] += 1
            except (OSError, ValueError):
                state, error = "error", "quarantine_unavailable"
                result["failed"] += 1
            c.execute(update(s.cleanup).where(s.cleanup.c.artifact_id == row["artifact_id"]).values(
                state=state, error_code=error, attempts=row["attempts"] + 1))
            store._audit(c, tenant, actor.subject, "retention." + state, row["artifact_id"])
    return result
