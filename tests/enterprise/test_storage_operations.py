from dataclasses import replace
import hashlib
import json
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select, update

from cris_sme.enterprise import schema as s
from cris_sme.enterprise.api import create_app
from cris_sme.enterprise.auth import Principal
from cris_sme.enterprise.historical import prepare_import, publish_import
from cris_sme.enterprise.recovery import backup, inspect_backup, restore
from cris_sme.enterprise.storage_operations import copy_registered, retention_plan, usage
from cris_sme.enterprise.store import Rejected
from cris_sme.enterprise.worker import execute_once
from tests.enterprise.conftest import ISSUER, aws_connection, submit
from tests.enterprise.test_historical import source
from tests.enterprise.test_recovery import isolated
from tests.enterprise.test_storage import remote
from tests.enterprise.test_worker import report_worker


def test_remote_worker_api_and_tenant_denial(context, verifier, token):
    ctx, storage = context, remote()
    job = submit(ctx, aws_connection(ctx))
    execute_once(ctx["store"], ctx["root"], execute=report_worker, storage=storage)
    details = ctx["store"].job(ctx["tenant"], ctx["principal"], job["id"])
    artifact = details["artifacts"][0]
    record = ctx["store"].artifact(ctx["tenant"], ctx["principal"], artifact["id"])
    (ctx["root"] / record["key"]).unlink()
    settings = replace(ctx["settings"], artifact_storage=storage)
    with TestClient(create_app(settings, ctx["store"], verifier=verifier)) as client:
        client.headers["Authorization"] = "Bearer " + token()
        url = f"/api/v1/tenants/{ctx['tenant']}/artifacts/{artifact['id']}"
        response = client.get(url)
        assert response.status_code == 200
        assert hashlib.sha256(response.content).hexdigest() == artifact["sha256"]
        assert client.get("/ready").status_code == 200
        assert client.get(f"/api/v1/tenants/{uuid4()}/artifacts/{artifact['id']}").status_code == 404
        client.headers["Authorization"] = "Bearer " + token("outsider")
        assert client.get(url).status_code == 404
        client.headers["Authorization"] = "Bearer " + token()
        storage.client.objects[storage._key(record["key"])] = b"tampered"
        assert client.get(url).status_code == 409
        storage.client.public = True
        assert client.get("/ready").status_code == 503


def test_remote_failure_never_publishes_completed_job(context):
    ctx, storage = context, remote()
    storage.client.fail = True
    job = submit(ctx, aws_connection(ctx))
    execute_once(ctx["store"], ctx["root"], execute=report_worker, storage=storage)
    details = ctx["store"].job(ctx["tenant"], ctx["principal"], job["id"])
    assert details["status"] == "failed" and details["artifacts"] == []


def test_disconnect_during_remote_copy_fences_publication(context):
    ctx, storage = context, remote()
    connection = aws_connection(ctx)
    job = submit(ctx, connection)
    publish = storage.publish
    def disconnect(key, content):
        publish(key, content)
        ctx["store"].disconnect(ctx["tenant"], ctx["principal"], connection)
    storage.publish = disconnect
    execute_once(ctx["store"], ctx["root"], execute=report_worker, storage=storage)
    details = ctx["store"].job(ctx["tenant"], ctx["principal"], job["id"])
    assert details["status"] == "cancelled" and details["artifacts"] == []


def test_remote_import_failure_keeps_database_empty(context, tmp_path):
    ctx, storage = context, remote()
    storage.client.fail = True
    root, name, _ = source(tmp_path)
    from botocore.exceptions import ClientError
    with pytest.raises(ClientError):
        publish_import(ctx["store"], ctx["tenant"], ctx["principal"], prepare_import(root, name), ctx["root"], storage=storage)
    assert ctx["store"].job_list(ctx["tenant"], ctx["principal"]) == []


def test_remote_import_and_recovery_roundtrip(context, tmp_path):
    ctx, storage = context, remote()
    root, name, raw = source(tmp_path)
    job = publish_import(ctx["store"], ctx["tenant"], ctx["principal"], prepare_import(root, name), ctx["root"], storage=storage)
    assert not publish_import(ctx["store"], ctx["tenant"], ctx["principal"], prepare_import(root, name), ctx["root"], storage=storage)["created"]
    destination = tmp_path.parent / ("bundle-" + uuid4().hex)
    try:
        backup(ctx["store"], ctx["root"], destination, storage=storage)
        assert len(inspect_backup(ctx["store"], destination)[s.artifacts.name]) == 2
        with isolated(ctx["store"]) as target:
            recovered = remote()
            restore(target, destination, tmp_path / "restored", storage=recovered)
            artifacts = target.job(ctx["tenant"], ctx["principal"], job["job_id"])["artifacts"]
            artifact = next(row for row in artifacts if row["name"] == "cris_sme_report.json")
            record = target.artifact(ctx["tenant"], ctx["principal"], artifact["id"])
            assert recovered.read(record["key"]) == raw
        with isolated(ctx["store"]) as target:
            with pytest.raises(ValueError, match="unused S3"):
                restore(target, destination, tmp_path / "reused-prefix", storage=recovered)
    finally:
        import shutil
        shutil.rmtree(destination)


def test_storage_migration_preview_apply_and_idempotence(context, tmp_path):
    ctx, storage = context, remote()
    submit(ctx, aws_connection(ctx))
    with pytest.raises(ValueError, match="Drain"):
        copy_registered(ctx["store"], ctx["root"], storage)
    execute_once(ctx["store"], ctx["root"], execute=report_worker)
    assert copy_registered(ctx["store"], ctx["root"], storage)["dry_run"] is True
    assert storage.client.calls == []
    assert copy_registered(ctx["store"], ctx["root"], storage, apply=True)["registered_artifacts"] == 2
    copy_registered(ctx["store"], ctx["root"], storage, apply=True)
    assert len(storage.client.objects) == 2
    assert usage(ctx["store"], ctx["tenant"], ctx["principal"])["registered_artifacts"] == 2
    with ctx["store"].engine.connect() as c:
        row = c.execute(select(s.artifacts)).mappings().first()
    (ctx["root"] / row["key"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="integrity"):
        copy_registered(ctx["store"], ctx["root"], remote(), apply=True)


def test_retention_is_read_only_keeps_latest_and_protects_imports(context, tmp_path):
    ctx = context
    jobs = []
    for index in range(3):
        root, name, _ = source(tmp_path)
        payload = json.loads((root / name).read_bytes())
        payload["run_metadata"]["run_id"] = f"archive-{index}"
        (root / name).write_text(json.dumps(payload))
        result = publish_import(ctx["store"], ctx["tenant"], ctx["principal"], prepare_import(root, name), ctx["root"])
        jobs.append(result["job_id"])
        with ctx["store"].engine.begin() as c:
            c.execute(update(s.jobs).where(s.jobs.c.id == jobs[-1]).values(requested_at=100 + index))
            c.execute(update(s.historical_imports).where(s.historical_imports.c.job_id == jobs[-1]).values(imported_at=100))
    assert retention_plan(ctx["store"], ctx["tenant"], ctx["principal"], 30)["candidates"] == []
    plan = retention_plan(ctx["store"], ctx["tenant"], ctx["principal"], 30, include_historical=True, exclude=[jobs[0]])
    assert [row["assessment_id"] for row in plan["candidates"]] == [jobs[1]]
    assert plan["deletion_executed"] is False and plan["legal_hold_checked"] is True
    assert plan["candidates"][0]["age_basis"] == "imported_at"
    assert len(ctx["store"].job_list(ctx["tenant"], ctx["principal"])) == 3
    for job in jobs:
        assert len(ctx["store"].job(ctx["tenant"], ctx["principal"], job)["artifacts"]) == 2
    with ctx["store"].engine.begin() as c:
        c.execute(update(s.historical_imports).where(s.historical_imports.c.job_id == jobs[1]).values(imported_at=ctx["store"]._now(c)))
    assert retention_plan(ctx["store"], ctx["tenant"], ctx["principal"], 30, include_historical=True, exclude=[jobs[0]])["candidates"] == []


def test_native_retention_uses_recorded_request_age_and_keeps_latest(context):
    ctx = context
    connection = aws_connection(ctx)
    jobs = []
    for index in range(2):
        job = submit(ctx, connection, f"native-{index}")
        execute_once(ctx["store"], ctx["root"], execute=report_worker)
        jobs.append(job["id"])
        with ctx["store"].engine.begin() as c:
            c.execute(update(s.jobs).where(s.jobs.c.id == job["id"]).values(requested_at=100 + index))
    plan = retention_plan(ctx["store"], ctx["tenant"], ctx["principal"], 30)
    assert [row["assessment_id"] for row in plan["candidates"]] == [jobs[0]]
    assert plan["candidates"][0]["age_basis"] == "requested_at"


@pytest.mark.parametrize("days", [0, -1, True, 36501])
def test_retention_invalid_age_rejected(context, days):
    with pytest.raises(ValueError):
        retention_plan(context["store"], context["tenant"], context["principal"], days)


def test_storage_inventory_and_planning_require_tenant_admin(context):
    ctx = context
    with pytest.raises(Rejected):
        usage(ctx["store"], str(uuid4()), ctx["principal"])
    with pytest.raises(Rejected):
        retention_plan(ctx["store"], ctx["tenant"], Principal(ISSUER, "outsider"), 30)
    url = f"/api/v1/tenants/{ctx['tenant']}/storage"
    assert ctx["client"].get(url).json()["registered_bytes"] == 0
    with ctx["store"].engine.begin() as c:
        c.execute(update(s.memberships).where(s.memberships.c.tenant_id == ctx["tenant"]).values(role="analyst"))
    assert ctx["client"].get(url).status_code == 403
