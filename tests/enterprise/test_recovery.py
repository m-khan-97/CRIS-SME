from contextlib import contextmanager
import hashlib
import json
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
import pytest
from sqlalchemy import insert, select, update

from cris_sme.enterprise import schema as s
from cris_sme.enterprise.historical import prepare_import, publish_import
from cris_sme.enterprise.recovery import backup, inspect_backup, restore
from cris_sme.enterprise.store import Store, Rejected
from tests.enterprise.conftest import aws_connection, submit
from tests.enterprise.test_historical import source


@pytest.fixture(autouse=True)
def recovery_storage(context, tmp_path):
    context["root"] = tmp_path / "artifacts"
    context["root"].mkdir()


@contextmanager
def isolated(store):
    name = "restore_" + uuid4().hex
    with store.engine.begin() as c:
        c.exec_driver_sql(f'CREATE SCHEMA "{name}"')
    engine = store.engine.execution_options(schema_translate_map={None: name})
    s.migrate(engine)
    target = Store(engine, Fernet.generate_key())
    target.cipher = store.cipher
    try:
        yield target
    finally:
        with store.engine.begin() as c:
            c.exec_driver_sql(f'DROP SCHEMA "{name}" CASCADE')


def populated(ctx, tmp_path):
    root, name, raw = source(tmp_path, exports=True)
    job = publish_import(ctx["store"], ctx["tenant"], ctx["principal"],
                         prepare_import(root, name, include_exports=True), ctx["root"])
    return job["job_id"], raw


def test_roundtrip_preserves_tenants_memberships_history_and_bytes_but_disables_connections(context, tmp_path):
    ctx = context
    job, raw = populated(ctx, tmp_path)
    aws_connection(ctx)
    destination = tmp_path / "backup"
    result = backup(ctx["store"], ctx["root"], destination)
    assert result == {"artifacts": 3, "tenants": 1, "schema_version": s.SCHEMA_VERSION}
    assert destination.stat().st_mode & 0o777 == 0o700
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in destination.rglob("*") if p.is_file())
    tables = inspect_backup(ctx["store"], destination)
    assert any(r["enabled"] for r in tables[s.connections.name])
    with isolated(ctx["store"]) as target:
        output = tmp_path / "restored"
        assert restore(target, destination, output)["connections_disabled"] is True
        assert target.tenants(ctx["principal"]) == ctx["store"].tenants(ctx["principal"])
        original = ctx["store"].job(ctx["tenant"], ctx["principal"], job)
        assert target.job(ctx["tenant"], ctx["principal"], job) == original
        assert target.audit_list(ctx["tenant"], ctx["principal"]) == ctx["store"].audit_list(ctx["tenant"], ctx["principal"])
        assert all(not r["enabled"] and r["verified_until"] == 0 for r in target.connection_list(ctx["tenant"], ctx["principal"]))
        for artifact in original["artifacts"]:
            row = target.artifact(ctx["tenant"], ctx["principal"], artifact["id"])
            assert hashlib.sha256((output / row["key"]).read_bytes()).hexdigest() == artifact["sha256"]
            if artifact["name"] == "cris_sme_report.json":
                assert (output / row["key"]).read_bytes() == raw
        assert target.claim() is None
        with pytest.raises(Rejected):
            target.job(str(uuid4()), ctx["principal"], job)
        with pytest.raises(ValueError, match="empty isolated"):
            restore(target, destination, tmp_path / "retry")
    assert ctx["store"].job(ctx["tenant"], ctx["principal"], job) == original
    assert any(r["enabled"] for r in ctx["store"].connection_list(ctx["tenant"], ctx["principal"]))


@pytest.mark.parametrize("status", ["queued", "running", "cancelling"])
def test_backup_rejects_pending_work_without_creating_output(context, tmp_path, status):
    ctx = context
    job = submit(ctx, aws_connection(ctx))
    with ctx["store"].engine.begin() as c:
        c.execute(update(s.jobs).where(s.jobs.c.id == job["id"]).values(status=status))
    with pytest.raises(ValueError, match="terminal"):
        backup(ctx["store"], ctx["root"], tmp_path / "backup")
    assert not (tmp_path / "backup").exists()


@pytest.mark.parametrize("problem", ["missing", "corrupt", "symlink"])
def test_corrupt_source_artifact_never_completes_backup(context, tmp_path, problem):
    ctx = context
    job, _ = populated(ctx, tmp_path)
    artifact = ctx["store"].job(ctx["tenant"], ctx["principal"], job)["artifacts"][0]
    row = ctx["store"].artifact(ctx["tenant"], ctx["principal"], artifact["id"])
    path = ctx["root"] / row["key"]
    path.unlink()
    if problem == "corrupt":
        path.write_bytes(b"changed")
    elif problem == "symlink":
        path.symlink_to(tmp_path / "source" / "cris_sme_report.json")
    with pytest.raises((ValueError, OSError)):
        backup(ctx["store"], ctx["root"], tmp_path / "backup")
    assert not (tmp_path / "backup" / "complete.json").exists()


def rewrite(destination, mutate):
    payload = json.loads((destination / "metadata.json").read_bytes())
    mutate(payload)
    raw = json.dumps(payload).encode()
    (destination / "metadata.json").write_bytes(raw)
    (destination / "complete.json").write_text(json.dumps({"format": 1, "metadata_sha256": hashlib.sha256(raw).hexdigest()}))


@pytest.mark.parametrize("problem", ["digest", "artifact", "schema", "traversal", "namespace", "duplicate", "active", "unknown_table", "wrong_key", "symlink"])
def test_restore_rejects_damage_and_unsupported_inputs_before_publication(context, tmp_path, problem):
    ctx = context
    populated(ctx, tmp_path)
    destination = tmp_path / "backup"
    backup(ctx["store"], ctx["root"], destination)
    metadata = json.loads((destination / "metadata.json").read_bytes())
    file = destination / "artifacts" / metadata["tables"][s.artifacts.name][0]["id"]
    if problem == "digest":
        (destination / "metadata.json").write_bytes(b"{}")
    elif problem == "artifact":
        file.write_bytes(b"tampered")
    elif problem == "symlink":
        file.unlink()
        file.symlink_to(tmp_path / "source" / "cris_sme_report.json")
    elif problem == "schema":
        rewrite(destination, lambda p: p.update(schema_version=99))
    elif problem in {"traversal", "namespace"}:
        rewrite(destination, lambda p: p["tables"][s.artifacts.name][0].update(key="../escape" if problem == "traversal" else str(uuid4()) + "/job/report"))
    elif problem == "duplicate":
        rewrite(destination, lambda p: p["tables"][s.artifacts.name].append(p["tables"][s.artifacts.name][0]))
    elif problem == "active":
        rewrite(destination, lambda p: p["tables"][s.jobs.name][0].update(status="queued"))
    elif problem == "unknown_table":
        rewrite(destination, lambda p: p["tables"].update(unknown=[]))
    with isolated(ctx["store"]) as target:
        if problem == "wrong_key":
            target.cipher = Fernet(Fernet.generate_key())
        with pytest.raises((ValueError, OSError, InvalidToken)):
            restore(target, destination, tmp_path / "restored")
        assert not (tmp_path / "restored").exists()
        assert target.tenants(ctx["principal"]) == []


def test_restore_database_constraint_failure_is_atomic(context, tmp_path):
    ctx = context
    populated(ctx, tmp_path)
    destination = tmp_path / "backup"
    backup(ctx["store"], ctx["root"], destination)
    rewrite(destination, lambda p: p["tables"][s.memberships.name][0].update(tenant_id=str(uuid4())))
    from sqlalchemy.exc import IntegrityError
    with isolated(ctx["store"]) as target:
        with pytest.raises(IntegrityError):
            restore(target, destination, tmp_path / "restored")
        assert target.tenants(ctx["principal"]) == []
        with target.engine.connect() as c:
            assert list(c.execute(select(s.artifacts))) == []


def test_never_overwrites_backup_or_existing_artifact_storage(context, tmp_path):
    ctx = context
    populated(ctx, tmp_path)
    destination = tmp_path / "backup"
    backup(ctx["store"], ctx["root"], destination)
    with pytest.raises(FileExistsError):
        backup(ctx["store"], ctx["root"], destination)
    with pytest.raises(ValueError, match="outside"):
        backup(ctx["store"], ctx["root"], ctx["root"] / "nested")
    with isolated(ctx["store"]) as target:
        output = tmp_path / "existing"
        output.mkdir()
        with pytest.raises(FileExistsError):
            restore(target, destination, output)
        assert target.tenants(ctx["principal"]) == []


def test_backup_refuses_concurrent_writes(context, tmp_path):
    ctx = context
    from sqlalchemy.exc import OperationalError
    with ctx["store"].engine.begin() as c:
        c.execute(insert(s.tenants).values(id=str(uuid4()), name="Concurrent uncommitted tenant"))
        with pytest.raises(OperationalError):
            backup(ctx["store"], ctx["root"], tmp_path / "backup")
    assert not (tmp_path / "backup").exists()
