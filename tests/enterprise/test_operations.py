from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from cryptography.fernet import Fernet
import pytest
from sqlalchemy import delete, insert, update

from cris_sme.enterprise import operations as op, schema as s
from cris_sme.enterprise.auth import Principal
from cris_sme.enterprise.historical import prepare_import, publish_import
from cris_sme.enterprise.recovery import backup, inspect_backup, restore
from cris_sme.enterprise.store import Rejected, Store
from cris_sme.enterprise.worker import execute_once
from tests.enterprise.conftest import ISSUER, aws_connection, submit
from tests.enterprise.test_historical import source
from tests.enterprise.test_recovery import isolated
from tests.enterprise.test_worker import report_worker


def snapshot(ctx):
    return op.tenant_status(ctx["store"], ctx["tenant"], ctx["principal"])


def test_reservations_prevent_overcommit_and_do_not_charge_idempotent_retry(context, monkeypatch):
    ctx = context
    monkeypatch.setattr(ctx["store"], "_now", lambda c: 1_800_000_001)
    monkeypatch.setattr(op, "DEFAULT_QUOTA_BYTES", op.JOB_BYTES)
    connection = aws_connection(ctx)
    job = submit(ctx, connection)
    assert snapshot(ctx)["reserved_bytes"] == op.JOB_BYTES
    assert submit(ctx, connection)["id"] == job["id"]
    response = ctx["client"].post(f"/api/v1/tenants/{ctx['tenant']}/assessments", headers={"Idempotency-Key": "second"},
        json={"connection_id": connection, "authorization_confirmed": True})
    assert response.status_code == 429 and response.headers["Retry-After"] == "60"
    assert execute_once(ctx["store"], ctx["root"], execute=report_worker)
    assert snapshot(ctx)["reserved_bytes"] == 0
    assert snapshot(ctx)["registered_bytes"] > 0
    assert snapshot(ctx)["rate_limits"]["scan_submission"]["used"] == 1
    artifact = ctx["store"].job(ctx["tenant"], ctx["principal"], job["id"])["artifacts"][0]
    assert ctx["client"].get(f"/api/v1/tenants/{ctx['tenant']}/artifacts/{artifact['id']}").status_code == 200


def test_cancelled_and_failed_jobs_release_reservations(context, monkeypatch):
    ctx = context
    monkeypatch.setattr(op, "DEFAULT_QUOTA_BYTES", op.JOB_BYTES)
    connection = aws_connection(ctx)
    first = submit(ctx, connection, "first")
    ctx["store"].cancel(ctx["tenant"], ctx["principal"], first["id"])
    assert snapshot(ctx)["reserved_bytes"] == 0
    second = submit(ctx, connection, "second")
    execute_once(ctx["store"], ctx["root"], execute=lambda *args, **kwargs: SimpleNamespace(returncode=1))
    assert ctx["store"].job(ctx["tenant"], ctx["principal"], second["id"])["status"] == "failed"
    assert snapshot(ctx)["reserved_bytes"] == 0


def test_import_cannot_spend_capacity_reserved_for_live_jobs(context, tmp_path, monkeypatch):
    ctx = context
    monkeypatch.setattr(op, "DEFAULT_QUOTA_BYTES", 2 * op.JOB_BYTES)
    connection = aws_connection(ctx)
    submit(ctx, connection, "one")
    submit(ctx, connection, "two")
    root, name, _ = source(tmp_path)
    with pytest.raises(Rejected) as error:
        publish_import(ctx["store"], ctx["tenant"], ctx["principal"], prepare_import(root, name), ctx["root"])
    assert error.value.status == 429
    assert len(ctx["store"].job_list(ctx["tenant"], ctx["principal"])) == 2
    assert not (ctx["root"] / ctx["tenant"]).exists()


def test_limits_are_operator_scoped_audited_and_require_drained_jobs(context):
    ctx = context
    connection = aws_connection(ctx)
    job = submit(ctx, connection)
    with pytest.raises(Rejected, match="Drain"):
        op.set_limits(ctx["store"], ctx["tenant"], ctx["principal"], op.JOB_BYTES, 5)
    ctx["store"].cancel(ctx["tenant"], ctx["principal"], job["id"])
    op.set_limits(ctx["store"], ctx["tenant"], ctx["principal"], op.JOB_BYTES, 5)
    assert snapshot(ctx)["quota_bytes"] == op.JOB_BYTES
    assert any(row["action"] == "operations.limits_changed" for row in ctx["store"].audit_list(ctx["tenant"], ctx["principal"]))
    with pytest.raises(Rejected):
        op.set_limits(ctx["store"], ctx["tenant"], Principal(ISSUER, "outsider"), op.JOB_BYTES, 5)
    op.set_limits(ctx["store"], ctx["tenant"], ctx["principal"], 2 * op.JOB_BYTES, 5)
    submit(ctx, connection, "file-budget")
    execute_once(ctx["store"], ctx["root"], execute=report_worker)
    response = ctx["client"].post(f"/api/v1/tenants/{ctx['tenant']}/assessments", headers={"Idempotency-Key": "file-denied"},
        json={"connection_id": connection, "authorization_confirmed": True})
    assert response.status_code == 429 and snapshot(ctx)["registered_artifacts"] == 2


@pytest.mark.parametrize("size,count", [(0, 5), (True, 5), (op.JOB_BYTES, 0), (1024 ** 4 + 1, 5), (op.JOB_BYTES, 1_000_001)])
def test_invalid_limits_are_rejected(context, size, count):
    with pytest.raises(ValueError):
        op.set_limits(context["store"], context["tenant"], context["principal"], size, count)


def test_failed_verification_is_rate_limited_before_provider_calls(context, verifier, token, monkeypatch):
    ctx = context
    monkeypatch.setattr(ctx["store"], "_now", lambda c: 1_800_000_001)
    connection = aws_connection(ctx, verify=False)
    calls = []
    def denied(row):
        calls.append(row["id"])
        raise RuntimeError("private provider credential detail")
    from fastapi.testclient import TestClient
    from cris_sme.enterprise.api import create_app
    with TestClient(create_app(ctx["settings"], ctx["store"], verifier=verifier, cloud_verify=denied)) as client:
        client.headers["Authorization"] = "Bearer " + token()
        url = f"/api/v1/tenants/{ctx['tenant']}/connections/{connection}/verify"
        for _ in range(6):
            assert client.post(url).status_code == 409
        response = client.post(url)
        assert response.status_code == 429 and 1 <= int(response.headers["Retry-After"]) <= 60
        assert len(calls) == 6 and "private provider" not in response.text


def test_rate_limit_is_atomic_across_store_instances_and_isolates_tenants(context, monkeypatch):
    ctx = context
    second = Store(ctx["store"].engine, Fernet.generate_key())
    second.cipher = ctx["store"].cipher
    monkeypatch.setattr(ctx["store"], "_now", lambda c: 1_800_000_001)
    monkeypatch.setattr(second, "_now", lambda c: 1_800_000_001)
    def attempt(index):
        store = ctx["store"] if index % 2 else second
        try:
            with store.engine.begin() as c:
                store._access(c, ctx["tenant"], ctx["principal"], {"owner"}, lock=True)
                op.charge(store, c, ctx["tenant"], "connection_verification")
            return True
        except Rejected:
            return False
    with ThreadPoolExecutor(max_workers=4) as threads:
        assert sum(threads.map(attempt, range(16))) == 6
    other = ctx["store"].bootstrap(ctx["principal"], "Other fixture tenant")
    with ctx["store"].engine.begin() as c:
        ctx["store"]._access(c, other, ctx["principal"], {"owner"}, lock=True)
        op.charge(ctx["store"], c, other, "connection_verification")
    assert op.tenant_status(ctx["store"], other, ctx["principal"])["rate_limits"]["connection_verification"]["used"] == 1


def test_rate_window_resets_without_raw_identity_labels(context):
    ctx = context
    connection = aws_connection(ctx)
    with ctx["store"].engine.begin() as c:
        c.execute(update(s.rates).where(s.rates.c.tenant_id == ctx["tenant"]).values(window=0, used=999))
    ctx["store"].admit_verification(ctx["tenant"], ctx["principal"], connection)
    data = snapshot(ctx)
    assert data["rate_limits"]["connection_verification"]["used"] == 1
    assert ctx["tenant"] not in json.dumps(data) and "secret" not in json.dumps(data)


def test_disk_pressure_blocks_new_work_but_not_retry_or_reads(context, monkeypatch):
    ctx = context
    connection = aws_connection(ctx)
    job = submit(ctx, connection)
    monkeypatch.setattr(op.shutil, "disk_usage", lambda root: SimpleNamespace(free=0))
    assert submit(ctx, connection)["id"] == job["id"]
    url = f"/api/v1/tenants/{ctx['tenant']}/assessments"
    assert ctx["client"].post(url, json={"connection_id": connection, "authorization_confirmed": True},
        headers={"Idempotency-Key": "new"}).status_code == 503
    assert ctx["client"].get(url).status_code == 200
    assert ctx["client"].get("/ready").json() == {"status": "not_ready"}


@pytest.mark.parametrize("pressure", ["disk", "staging", "namespace"])
def test_worker_resource_pressure_cancels_without_publication(context, monkeypatch, pressure):
    ctx = context
    job = submit(ctx, aws_connection(ctx))
    called = []
    if pressure == "disk":
        monkeypatch.setattr(op.shutil, "disk_usage", lambda root: SimpleNamespace(free=0))
    elif pressure == "namespace":
        root = ctx["root"] / ctx["tenant"]
        root.mkdir()
        with (root / "old-orphan.bin").open("wb") as stream:
            stream.truncate(op.DEFAULT_QUOTA_BYTES + op.STAGING_BYTES + 1)
    def execute(command, **kwargs):
        called.append(True)
        if pressure == "staging":
            path = Path(kwargs["env"]["CRIS_SME_OUTPUT_DIR"]) / "oversize.bin"
            with path.open("wb") as stream:
                stream.truncate(op.STAGING_BYTES + 1)
            assert kwargs["cancel"].wait(5), "Guard must interrupt the running process"
            return SimpleNamespace(returncode=1)
        return report_worker(command, **kwargs)
    execute_once(ctx["store"], ctx["root"], execute=execute)
    result = ctx["store"].job(ctx["tenant"], ctx["principal"], job["id"])
    assert result["status"] == "failed" and result["artifacts"] == []
    assert result["error_code"] == ("disk_pressure" if pressure == "disk" else "staging_limit")
    if pressure != "staging":
        assert called == []
    assert snapshot(ctx)["reserved_bytes"] == 0


def test_guard_handles_hardlinks_and_rejects_symlinked_namespace(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / "file").write_bytes(b"12345")
    import os
    os.link(first / "file", second / "copy")
    op._tree_size([first, second], 5, 5)
    link = tmp_path / "link"
    link.symlink_to(first, target_is_directory=True)
    with pytest.raises(op.ResourceLimit):
        op._tree_size([link], 5, 5)


def test_health_snapshots_redact_ids_and_stale_workers(context):
    ctx = context
    identifier = str(uuid4())
    op.touch_worker(ctx["store"], identifier, True)
    status = op.operator_status(ctx["store"], ctx["root"])
    assert status["workers_fresh"] == 1 and status["workers_busy"] == 1
    assert identifier not in json.dumps(status) and ctx["tenant"] not in json.dumps(status)
    with ctx["store"].engine.begin() as c:
        c.execute(update(s.workers).where(s.workers.c.id == identifier).values(last_seen=1))
    status = op.operator_status(ctx["store"], ctx["root"])
    assert status["workers_stale"] == 1 and status["workers_fresh"] == 0


def test_metrics_scope_and_quotas_survive_recovery_but_counters_do_not(context, tmp_path):
    ctx = context
    op.set_limits(ctx["store"], ctx["tenant"], ctx["principal"], 2 * op.JOB_BYTES, 100)
    aws_connection(ctx)
    op.touch_worker(ctx["store"], str(uuid4()), False)
    path = tmp_path.parent / ("operations-backup-" + uuid4().hex)
    try:
        backup(ctx["store"], ctx["root"], path)
        tables = inspect_backup(ctx["store"], path)
        assert s.workers.name not in tables and s.rates.name not in tables
        with isolated(ctx["store"]) as target:
            restore(target, path, tmp_path / "restored")
            status = op.tenant_status(target, ctx["tenant"], ctx["principal"])
            assert status["quota_bytes"] == 2 * op.JOB_BYTES
            assert status["rate_limits"]["connection_creation"]["used"] == 0
    finally:
        import shutil
        shutil.rmtree(path)
    url = f"/api/v1/tenants/{ctx['tenant']}/operations"
    assert ctx["client"].get(url).status_code == 200
    with ctx["store"].engine.begin() as c:
        c.execute(update(s.memberships).where(s.memberships.c.tenant_id == ctx["tenant"]).values(role="analyst"))
    assert ctx["client"].get(url).status_code == 403
    assert ctx["client"].get(f"/api/v1/tenants/{uuid4()}/operations").status_code == 404


def test_ten_organization_twenty_scan_fixture_load(context):
    ctx = context
    tenants = []
    for index in range(10):
        tenant = ctx["store"].bootstrap(ctx["principal"], f"Synthetic load tenant {index}")
        connection = ctx["store"].add_connection(tenant, ctx["principal"], "Fixture", "aws", "123456789012",
            {"role_arn": "arn:aws:iam::123456789012:role/fixture"}, {"external_id": "fixture-only"})
        ctx["store"].verified(tenant, ctx["principal"], connection)
        for number in range(2):
            ctx["store"].submit(tenant, ctx["principal"], connection, f"load-{number}")
        tenants.append(tenant)
    assert op.operator_status(ctx["store"], ctx["root"])["queued"] == 20
    def execute(_):
        return execute_once(ctx["store"], ctx["root"], execute=report_worker)
    with ThreadPoolExecutor(max_workers=4) as threads:
        assert all(threads.map(execute, range(20)))
    for tenant in tenants:
        data = op.tenant_status(ctx["store"], tenant, ctx["principal"])
        assert data["assessments"]["completed"] == 2 and data["reserved_bytes"] == 0
        assert data["registered_artifacts"] == 4


def test_admission_database_failure_never_reaches_provider(context, monkeypatch):
    ctx = context
    connection = aws_connection(ctx, verify=False)
    def unavailable(*args):
        raise RuntimeError("private database credential")
    with monkeypatch.context() as patch:
        patch.setattr(ctx["store"], "admit_verification", unavailable)
        response = ctx["client"].post(f"/api/v1/tenants/{ctx['tenant']}/connections/{connection}/verify")
    assert response.status_code == 503 and "private database" not in response.text
    assert ctx["verified"] == []
    assert ctx["client"].post(f"/api/v1/tenants/{ctx['tenant']}/connections/{connection}/verify").status_code == 200


def test_v3_upgrade_preserves_records_and_has_default_limits(context):
    ctx = context
    with ctx["store"].engine.begin() as c:
        s.job_tenant_index.drop(c)
        s.artifact_tenant_index.drop(c)
        for table in (s.rates, s.workers, s.limits):
            table.drop(c)
        c.execute(delete(s.versions))
        c.execute(insert(s.versions).values(version=3))
    s.migrate(ctx["store"].engine)
    ctx["store"].check_schema()
    assert snapshot(ctx)["quota_bytes"] == op.DEFAULT_QUOTA_BYTES
    assert ctx["store"].tenants(ctx["principal"])[0]["id"] == ctx["tenant"]
