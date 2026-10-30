from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import json
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, insert, select, update

from cris_sme.enterprise import schema as s
from cris_sme.enterprise.api import create_app
from cris_sme.enterprise.auth import Principal
from cris_sme.enterprise import retention as r
from cris_sme.enterprise.recovery import backup, inspect_backup, restore
from cris_sme.enterprise.storage import LocalStorage
from cris_sme.enterprise.store import Rejected
from cris_sme.enterprise.worker import execute_once
from tests.enterprise.conftest import ISSUER, aws_connection, submit
from tests.enterprise.test_recovery import isolated
from tests.enterprise.test_storage import remote
from tests.enterprise.test_worker import report_worker


def eligible(ctx):
    connection = aws_connection(ctx)
    jobs = []
    for index in range(2):
        job = submit(ctx, connection, f"retention-{index}")
        execute_once(ctx["store"], ctx["root"], execute=report_worker)
        jobs.append(job["id"])
        with ctx["store"].engine.begin() as c:
            c.execute(update(s.jobs).where(s.jobs.c.id == job["id"]).values(requested_at=100 + index))
    return jobs


def approval(ctx):
    jobs = eligible(ctx)
    ctx["store"].member(ctx["tenant"], ctx["principal"], "second-owner", "owner")
    reviewer = Principal(ISSUER, "second-owner")
    plan = r.propose(ctx["store"], ctx["tenant"], ctx["principal"], 30, "Approved test retention")
    r.decide(ctx["store"], ctx["tenant"], reviewer, plan["id"], plan["sha256"])
    return jobs, reviewer, plan


def cooled(ctx, plan):
    with ctx["store"].engine.begin() as c:
        c.execute(update(s.retention_plans).where(s.retention_plans.c.id == plan["id"]).values(execute_after=1))


def test_two_person_expiry_quarantine_and_history_preservation(context):
    ctx = context
    jobs, reviewer, plan = approval(ctx)
    old = ctx["store"].job(ctx["tenant"], ctx["principal"], jobs[0])
    records = [ctx["store"].artifact(ctx["tenant"], ctx["principal"], a["id"]) for a in old["artifacts"]]
    storage = LocalStorage(ctx["root"])
    with pytest.raises(Rejected, match="cooling"):
        r.expire(ctx["store"], ctx["tenant"], reviewer, plan["id"], plan["sha256"], storage)
    cooled(ctx, plan)
    result = r.expire(ctx["store"], ctx["tenant"], reviewer, plan["id"], plan["sha256"], storage)
    assert result["assessments"] == 1 and result["artifacts"] == 2
    assert r.expire(ctx["store"], ctx["tenant"], reviewer, plan["id"], plan["sha256"], storage)["state"] == "expired"
    current = ctx["store"].job(ctx["tenant"], ctx["principal"], jobs[0])
    assert current["status"] == "completed" and current["report_state"] == "expired" and current["artifacts"] == []
    assert ctx["store"].job(ctx["tenant"], ctx["principal"], jobs[1])["report_state"] == "available"
    for record in records:
        response = ctx["client"].get(f"/api/v1/tenants/{ctx['tenant']}/artifacts/{record['id']}")
        assert response.status_code == 410
    result = r.cleanup_local(ctx["store"], ctx["tenant"], reviewer, plan["id"], storage)
    assert result == {"quarantined": 2, "held": 0, "failed": 0, "permanent_erasure": False}
    for row in records:
        assert not (ctx["root"] / row["key"]).exists()
        path = ctx["root"] / "retention_quarantine" / ctx["tenant"] / plan["id"] / row["id"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]
    assert r.cleanup_local(ctx["store"], ctx["tenant"], reviewer, plan["id"], storage)["quarantined"] == 0
    actions = {row["action"] for row in ctx["store"].audit_list(ctx["tenant"], ctx["principal"])}
    assert {"retention.proposed", "retention.approved", "retention.expired", "retention.quarantined"} <= actions


def test_self_approval_digest_and_withdrawal_guards(context):
    ctx = context
    jobs = eligible(ctx)
    plan = r.propose(ctx["store"], ctx["tenant"], ctx["principal"], 30, "Reviewed retention")
    with pytest.raises(Rejected, match="different owner"):
        r.decide(ctx["store"], ctx["tenant"], ctx["principal"], plan["id"], plan["sha256"])
    with pytest.raises(Rejected):
        r.decide(ctx["store"], ctx["tenant"], ctx["principal"], plan["id"], "f" * 64)
    r.decide(ctx["store"], ctx["tenant"], ctx["principal"], plan["id"], plan["sha256"], approve=False)
    with pytest.raises(Rejected):
        r.expire(ctx["store"], ctx["tenant"], ctx["principal"], plan["id"], plan["sha256"], LocalStorage(ctx["root"]))
    assert ctx["store"].job(ctx["tenant"], ctx["principal"], jobs[0])["report_state"] == "available"


@pytest.mark.parametrize("change", ["hold", "proposer_revoked", "approver_revoked", "inventory", "deadline", "withdraw", "latest"])
def test_execution_rechecks_current_authority_and_inventory(context, change):
    ctx = context
    jobs, reviewer, plan = approval(ctx)
    cooled(ctx, plan)
    if change == "hold":
        r.hold(ctx["store"], ctx["tenant"], ctx["principal"], jobs[0], "Evidence preservation")
    elif change == "proposer_revoked":
        ctx["store"].member(ctx["tenant"], reviewer, "owner", None)
    elif change == "approver_revoked":
        ctx["store"].member(ctx["tenant"], ctx["principal"], reviewer.subject, "analyst")
    elif change == "withdraw":
        r.decide(ctx["store"], ctx["tenant"], reviewer, plan["id"], plan["sha256"], approve=False)
    else:
        with ctx["store"].engine.begin() as c:
            if change == "inventory":
                c.execute(update(s.artifacts).where(s.artifacts.c.job_id == jobs[0]).values(size=99))
            elif change == "deadline":
                c.execute(update(s.retention_plans).where(s.retention_plans.c.id == plan["id"]).values(expires_at=1))
            else:
                c.execute(update(s.jobs).where(s.jobs.c.id == jobs[0]).values(requested_at=999))
    with pytest.raises(Rejected):
        r.expire(ctx["store"], ctx["tenant"], ctx["principal"] if change == "approver_revoked" else reviewer,
                 plan["id"], plan["sha256"], LocalStorage(ctx["root"]))
    with ctx["store"].engine.connect() as c:
        assert list(c.execute(select(s.retirements))) == []


def test_hold_reasons_are_durable_and_cleanup_stops_for_late_hold(context):
    ctx = context
    jobs, reviewer, plan = approval(ctx)
    cooled(ctx, plan)
    storage = LocalStorage(ctx["root"])
    r.expire(ctx["store"], ctx["tenant"], reviewer, plan["id"], plan["sha256"], storage)
    r.hold(ctx["store"], ctx["tenant"], reviewer, jobs[0], "Retain evidence for investigation")
    assert r.cleanup_local(ctx["store"], ctx["tenant"], reviewer, plan["id"], storage)["held"] == 2
    r.hold(ctx["store"], ctx["tenant"], reviewer, jobs[0], "Investigation closed", active=False)
    assert r.cleanup_local(ctx["store"], ctx["tenant"], reviewer, plan["id"], storage)["quarantined"] == 2
    with ctx["store"].engine.connect() as c:
        reasons = {row.reason for row in c.execute(select(s.hold_events))}
    assert reasons == {"Retain evidence for investigation", "Investigation closed"}


@pytest.mark.parametrize("damage", ["symlink", "corrupt", "missing", "target"])
def test_cleanup_failure_does_not_destroy_evidence_and_can_retry(context, damage):
    ctx = context
    jobs, reviewer, plan = approval(ctx)
    cooled(ctx, plan)
    with ctx["store"].engine.connect() as c:
        row = dict(c.execute(select(s.artifacts).where(s.artifacts.c.job_id == jobs[0])).mappings().first())
    storage = LocalStorage(ctx["root"])
    original = (ctx["root"] / row["key"]).read_bytes()
    r.expire(ctx["store"], ctx["tenant"], reviewer, plan["id"], plan["sha256"], storage)
    path = ctx["root"] / row["key"]
    destination = ctx["root"] / "retention_quarantine" / ctx["tenant"] / plan["id"] / row["id"]
    path.unlink()
    if damage == "symlink":
        path.symlink_to("/etc/passwd")
    elif damage == "corrupt":
        path.write_bytes(b"changed")
    elif damage == "target":
        path.write_bytes(original)
        destination.parent.mkdir(parents=True)
        destination.write_bytes(b"do not replace")
    result = r.cleanup_local(ctx["store"], ctx["tenant"], reviewer, plan["id"], storage)
    assert result["failed"] == 1
    if damage == "target":
        assert destination.read_bytes() == b"do not replace" and path.read_bytes() == original
        destination.unlink()
    path.unlink(missing_ok=True)
    path.write_bytes(original)
    assert r.cleanup_local(ctx["store"], ctx["tenant"], reviewer, plan["id"], storage)["quarantined"] == 1


def test_retry_after_filesystem_commit_and_database_rollback(context):
    ctx = context
    jobs, reviewer, plan = approval(ctx)
    cooled(ctx, plan)
    storage = LocalStorage(ctx["root"])
    r.expire(ctx["store"], ctx["tenant"], reviewer, plan["id"], plan["sha256"], storage)
    with ctx["store"].engine.connect() as c:
        row = c.execute(select(s.artifacts).where(s.artifacts.c.job_id == jobs[0])).mappings().first()
    r._quarantine(ctx["root"], row, plan["id"])
    assert r.cleanup_local(ctx["store"], ctx["tenant"], reviewer, plan["id"], storage)["quarantined"] == 2


def test_parallel_cleanup_is_idempotent(context):
    ctx = context
    _, reviewer, plan = approval(ctx)
    cooled(ctx, plan)
    storage = LocalStorage(ctx["root"])
    r.expire(ctx["store"], ctx["tenant"], reviewer, plan["id"], plan["sha256"], storage)
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _: r.cleanup_local(ctx["store"], ctx["tenant"], reviewer, plan["id"], storage), range(2)))
    assert sum(row["quarantined"] for row in results) == 2


def test_remote_execution_and_foreign_tenant_are_rejected(context):
    ctx = context
    jobs, reviewer, plan = approval(ctx)
    cooled(ctx, plan)
    with pytest.raises(Rejected):
        r.expire(ctx["store"], ctx["tenant"], reviewer, plan["id"], plan["sha256"], remote())
    with pytest.raises(Rejected):
        r.hold(ctx["store"], str(uuid4()), reviewer, jobs[0], "Foreign request")
    with pytest.raises(Rejected):
        r.list_state(ctx["store"], ctx["tenant"], Principal(ISSUER, "outsider"))


def test_api_defaults_disabled_but_holds_and_state_are_available(context, verifier, token):
    ctx = context
    jobs = eligible(ctx)
    base = f"/api/v1/tenants/{ctx['tenant']}"
    proposal = {"days": 30, "reason": "Reviewed request"}
    assert ctx["client"].post(base + "/retention/plans", json=proposal).status_code == 409
    assert ctx["client"].put(base + f"/assessments/{jobs[0]}/hold", json={"active": True, "reason": "Preserve"}).status_code == 200
    assert ctx["client"].get(base + "/retention").json()["holds"][0]["active"] is True
    assert ctx["client"].put(base + f"/assessments/{jobs[0]}/hold", json={"active": False, "reason": "Released"}).status_code == 200
    with TestClient(create_app(replace(ctx["settings"], retention_enabled=True), ctx["store"], verifier=verifier)) as client:
        client.headers["Authorization"] = "Bearer " + token()
        response = client.post(base + "/retention/plans", json=proposal)
        assert response.status_code == 201, response.text
        plan = response.json()
        assert client.get(base + f"/retention/plans/{plan['id']}").json()["snapshot"] == plan["snapshot"]
        assert client.get(base + "/retention").json()["plans"][0]["snapshot"] is None
        approve = base + f"/retention/plans/{plan['id']}/approve"
        assert client.post(approve, json={"sha256": plan["sha256"], "confirmed": True}).status_code == 403
        ctx["store"].member(ctx["tenant"], ctx["principal"], "second-owner", "owner")
        client.headers["Authorization"] = "Bearer " + token("second-owner")
        assert client.post(approve, json={"sha256": plan["sha256"], "confirmed": False}).status_code == 409
        assert client.post(approve, json={"sha256": plan["sha256"], "confirmed": True}).status_code == 200


def test_recovery_preserves_held_bytes_without_republishing_expired_reports(context, tmp_path):
    ctx = context
    jobs, reviewer, plan = approval(ctx)
    cooled(ctx, plan)
    storage = LocalStorage(ctx["root"])
    r.expire(ctx["store"], ctx["tenant"], reviewer, plan["id"], plan["sha256"], storage)
    r.cleanup_local(ctx["store"], ctx["tenant"], reviewer, plan["id"], storage)
    r.hold(ctx["store"], ctx["tenant"], reviewer, jobs[0], "Expired evidence under hold")
    destination = tmp_path.parent / ("retention-backup-" + uuid4().hex)
    try:
        assert backup(ctx["store"], ctx["root"], destination)["artifacts"] == 4
        assert len(inspect_backup(ctx["store"], destination)[s.retirements.name]) == 1
        with isolated(ctx["store"]) as target:
            output = tmp_path / "restored"
            restore(target, destination, output)
            assert target.job(ctx["tenant"], reviewer, jobs[0])["report_state"] == "expired"
            assert target.job(ctx["tenant"], reviewer, jobs[0])["artifacts"] == []
            assert r.list_state(target, ctx["tenant"], reviewer)["holds"][0]["active"] is True
            assert not (output / ctx["tenant"] / jobs[0]).exists()
            assert len(list((output / "retention_quarantine" / ctx["tenant"] / plan["id"]).iterdir())) == 2
        document = json.loads((destination / "metadata.json").read_bytes())
        document["tables"][s.retirements.name][0]["plan_id"] = "../../escape"
        raw = json.dumps(document).encode()
        (destination / "metadata.json").write_bytes(raw)
        (destination / "complete.json").write_text(json.dumps({"format": 1, "metadata_sha256": hashlib.sha256(raw).hexdigest()}))
        with pytest.raises(ValueError):
            inspect_backup(ctx["store"], destination)
    finally:
        import shutil
        shutil.rmtree(destination)


def test_v2_upgrade_and_legacy_bundle_remain_supported(context, tmp_path):
    ctx = context
    eligible(ctx)
    destination = tmp_path.parent / ("legacy-backup-" + uuid4().hex)
    try:
        backup(ctx["store"], ctx["root"], destination)
        document = json.loads((destination / "metadata.json").read_bytes())
        document["schema_version"] = 2
        for table in (s.holds, s.hold_events, s.retention_plans, s.retirements, s.cleanup):
            document["tables"].pop(table.name)
        raw = json.dumps(document).encode()
        (destination / "metadata.json").write_bytes(raw)
        (destination / "complete.json").write_text(json.dumps({"format": 1, "metadata_sha256": hashlib.sha256(raw).hexdigest()}))
        assert inspect_backup(ctx["store"], destination)[s.retirements.name] == []
        with ctx["store"].engine.begin() as c:
            for table in (s.cleanup, s.retirements, s.retention_plans, s.hold_events, s.holds):
                table.drop(c)
            c.execute(delete(s.versions))
            c.execute(insert(s.versions).values(version=2))
        s.migrate(ctx["store"].engine)
        ctx["store"].check_schema()
        assert len(ctx["store"].job_list(ctx["tenant"], ctx["principal"])) == 2
    finally:
        import shutil
        shutil.rmtree(destination)


def test_tampered_plan_is_not_approved(context):
    ctx = context
    _, reviewer, plan = approval(ctx)
    with ctx["store"].engine.begin() as c:
        c.execute(update(s.retention_plans).where(s.retention_plans.c.id == plan["id"]).values(snapshot="{}"))
    with pytest.raises(Rejected, match="integrity"):
        r.decide(ctx["store"], ctx["tenant"], reviewer, plan["id"], plan["sha256"])
