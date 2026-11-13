from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
import hashlib
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select, update
from sqlalchemy.exc import DBAPIError

from cris_sme.enterprise import database_security as security
from cris_sme.enterprise import operations, schema as s
from cris_sme.enterprise.api import Settings, create_app
from cris_sme.enterprise.auth import Principal
from cris_sme.enterprise.store import Rejected, Store
from cris_sme.enterprise.worker import execute_once
from tests.enterprise.conftest import ISSUER
from tests.enterprise.test_worker import report_worker


@pytest.fixture
def roles(store):
    names = {profile: "cris_" + profile + "_" + uuid.uuid4().hex for profile in ("api", "worker")}
    schema = store.engine.get_execution_options()["schema_translate_map"][None]
    with store.engine.begin() as c:
        for name in names.values():
            c.exec_driver_sql(f'CREATE ROLE "{name}" LOGIN PASSWORD \'cris_test_runtime_only\' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS')
    try:
        yield names
    finally:
        with store.engine.begin() as c:
            c.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
            c.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            for name in names.values():
                c.exec_driver_sql(f'DROP OWNED BY "{name}"')
                c.exec_driver_sql(f'DROP ROLE "{name}"')


@contextmanager
def runtime(store, role, profile):
    # Real non-superuser connection, never SET ROLE from a privileged session.
    url = store.engine.url.set(username=role, password="cris_test_runtime_only")
    schema = store.engine.get_execution_options()["schema_translate_map"][None]
    engine = create_engine(url, pool_size=1, max_overflow=0, hide_parameters=True,
                           connect_args={"options": "-c statement_timeout=5000 -c lock_timeout=1000"})
    try:
        yield Store(engine.execution_options(schema_translate_map={None: schema}),
                    encryption_key(store), database_profile=profile)
    finally:
        engine.dispose()


def encryption_key(store):
    import base64
    return base64.urlsafe_b64encode(store.cipher._signing_key + store.cipher._encryption_key)


def seed(store):
    owner = Principal(ISSUER, "owner")
    other = Principal(ISSUER, "other")
    tenants = [store.bootstrap(owner, "Same label"), store.bootstrap(other, "Same label")]
    jobs = []
    for tenant, actor in zip(tenants, [owner, other]):
        connection = store.add_connection(tenant, actor, "AWS", "aws", "123456789012",
            {"role_arn": "arn:aws:iam::123456789012:role/cris-reader"}, {"external_id": "fixture-external-id"})
        store.verified(tenant, actor, connection)
        jobs.append(store.submit(tenant, actor, connection, "same-key"))
    return owner, other, tenants, jobs


def test_preview_is_non_mutating_and_hardening_is_idempotent(store, roles):
    preview = security.harden(store.engine, roles["api"], roles["worker"])
    assert preview == {"applied": False, "schema": store.engine.get_execution_options()["schema_translate_map"][None],
                       "api_role": roles["api"], "worker_role": roles["worker"], "tables": len(s.metadata.tables),
                       "row_policy_tables": len(s.metadata.tables) - 1, "schema_version": s.SCHEMA_VERSION}
    with store.engine.connect() as c:
        assert not any(row["relrowsecurity"] for row in security._relations(c, security.namespace(c)).values())
    for _ in range(2):
        assert security.harden(store.engine, roles["api"], roles["worker"], apply=True)["applied"]
        for profile in roles:
            with runtime(store, roles[profile], profile) as app:
                assert security.check_runtime(app.engine, profile)["verified"]
                app.check_schema()


def test_api_missing_filters_fail_closed_and_pool_context_does_not_leak(store, roles):
    owner, other, tenants, jobs = seed(store)
    security.harden(store.engine, roles["api"], roles["worker"], apply=True)
    with runtime(store, roles["api"], "api") as app:
        assert app.tenants(owner)[0]["id"] == tenants[0]
        assert app.tenants(other)[0]["id"] == tenants[1]
        assert app.tenants(Principal(ISSUER, "absent")) == []
        assert app.job_list(tenants[0], owner)[0]["id"] == jobs[0]["id"]
        with pytest.raises(Rejected):
            app.job_list(tenants[1], owner)
        for tenant, actor, job in zip(tenants, [owner, other], jobs):
            with app.engine.begin() as c:
                app._access(c, tenant, actor)
                assert c.execute(select(s.jobs.c.id)).scalars().all() == [job["id"]]
                assert c.execute(update(s.jobs).values(error_code="bounded")).rowcount == 1
                assert c.execute(update(s.jobs).where(s.jobs.c.id == jobs[1 if tenant == tenants[0] else 0]["id"])
                                 .values(error_code="wrong")).rowcount == 0
            with app.engine.connect() as c:
                assert c.execute(select(s.jobs)).all() == []
        with app.engine.connect() as c:
            with pytest.raises(RuntimeError):
                with c.begin():
                    app._access(c, tenants[0], owner)
                    raise RuntimeError("rollback fixture")
            assert c.execute(select(s.jobs)).all() == []
        with app.engine.begin() as c:
            app._access(c, tenants[0], owner)
            with pytest.raises(DBAPIError):
                c.execute(update(s.jobs).where(s.jobs.c.id == jobs[0]["id"]).values(tenant_id=tenants[1]))


@pytest.mark.parametrize("statement", [
    "CREATE TABLE {schema}.forbidden (id integer)", "ALTER TABLE {schema}.cris_jobs DISABLE ROW LEVEL SECURITY",
    "TRUNCATE {schema}.cris_jobs CASCADE", "DELETE FROM {schema}.cris_artifacts",
    "UPDATE {schema}.cris_schema_version SET version=99", "UPDATE {schema}.cris_audit SET action='changed'",
    "INSERT INTO {schema}.cris_tenants (id,name) VALUES ('new','forbidden')",
    "UPDATE {schema}.cris_tenant_limits SET quota_bytes=999999999999", "SELECT * FROM {schema}.cris_worker_health",
])
def test_api_cannot_migrate_erase_evidence_raise_quota_or_inspect_workers(store, roles, statement):
    security.harden(store.engine, roles["api"], roles["worker"], apply=True)
    schema = store.engine.get_execution_options()["schema_translate_map"][None]
    with runtime(store, roles["api"], "api") as app, app.engine.begin() as c:
        with pytest.raises(DBAPIError):
            c.exec_driver_sql(statement.format(schema='"' + schema + '"'))


def test_restricted_worker_claims_across_tenants_and_fences_publication(store, roles):
    owner, other, tenants, jobs = seed(store)
    security.harden(store.engine, roles["api"], roles["worker"], apply=True)
    with runtime(store, roles["worker"], "worker") as worker:
        security.check_runtime(worker.engine, "worker")
        operations.touch_worker(worker, "fixture-worker", False)
        claims = [worker.claim(), worker.claim()]
        assert {row["tenant_id"] for row in claims} == set(tenants)
        for lease in claims:
            assert worker.heartbeat(lease)
            worker.publication_budget(lease, 1, 1)
            assert worker.finish(lease, "completed", [{"id": str(uuid.uuid4()), "name": "report.json", "key": "fixture",
                                                      "sha256": "0" * 64, "size": 1}])
            assert not worker.finish(lease, "completed")
        with worker.engine.begin() as c:
            with pytest.raises(DBAPIError):
                c.execute(update(s.memberships).values(role="owner"))
        with worker.engine.begin() as c:
            with pytest.raises(DBAPIError):
                c.execute(update(s.connections).values(enabled=False))


def test_real_restricted_api_routes_and_role_revocation(store, roles, verifier, token, tmp_path):
    owner, other, tenants, jobs = seed(store)
    security.harden(store.engine, roles["api"], roles["worker"], apply=True)
    settings = Settings(ISSUER, "cris-api", ISSUER + "/keys", "browser", ISSUER + "/authorize", ISSUER + "/token", tmp_path,
                        allowed_hosts=("testserver",))
    with runtime(store, roles["api"], "api") as app:
        with TestClient(create_app(settings, app, verifier=verifier, cloud_verify=lambda row: None),
                        raise_server_exceptions=False) as client:
            client.headers["Authorization"] = "Bearer " + token()
            assert client.get("/ready").status_code == 200
            assert client.get("/api/v1/tenants").json()["tenants"][0]["id"] == tenants[0]
            assert client.get(f"/api/v1/tenants/{tenants[0]}/assessments").status_code == 200
            assert client.get(f"/api/v1/tenants/{tenants[1]}/assessments").status_code == 404
            assert client.get(f"/api/v1/tenants/{tenants[0]}/operations").status_code == 200
            response = client.post(f"/api/v1/tenants/{tenants[0]}/connections", json={"name": "Restricted AWS", "provider": "aws",
                "scope_id": "123456789012", "role_arn": "arn:aws:iam::123456789012:role/cris-reader"})
            assert response.status_code == 201, response.text
            connection = response.json()["id"]
            assert client.post(f"/api/v1/tenants/{tenants[0]}/connections/{connection}/verify").status_code == 200
            assert client.post(f"/api/v1/tenants/{tenants[0]}/connections/{connection}/disconnect").status_code == 200
            assert client.put(f"/api/v1/tenants/{tenants[0]}/members/analyst", json={"role": "analyst"}).status_code == 200
            assert len(client.get(f"/api/v1/tenants/{tenants[0]}/members").json()["members"]) == 2
            store.member(tenants[0], owner, "analyst", None)
            client.headers["Authorization"] = "Bearer " + token("analyst")
            assert client.get(f"/api/v1/tenants/{tenants[0]}/assessments").status_code == 404


def test_runtime_guard_rejects_owner_wrong_profile_and_disabled_rls(store, roles):
    with pytest.raises(ValueError, match="unprivileged"):
        security.check_runtime(store.engine, "api")
    security.harden(store.engine, roles["api"], roles["worker"], apply=True)
    with runtime(store, roles["api"], "api") as app:
        with pytest.raises(ValueError, match="profile"):
            app.check_database_profile("worker")
        with store.engine.begin() as c:
            c.exec_driver_sql(f'ALTER TABLE "{security.namespace(c)}".cris_jobs DISABLE ROW LEVEL SECURITY')
        with pytest.raises(ValueError, match="row security"):
            security.check_runtime(app.engine, "api")


def test_restricted_end_to_end_worker_artifacts_holds_and_cancel(store, roles, verifier, token, tmp_path):
    from cris_sme.enterprise import retention
    owner, other, tenants, jobs = seed(store)
    security.harden(store.engine, roles["api"], roles["worker"], apply=True)
    settings = Settings(ISSUER, "cris-api", ISSUER + "/keys", "browser", ISSUER + "/authorize", ISSUER + "/token", tmp_path,
                        allowed_hosts=("testserver",))
    with runtime(store, roles["worker"], "worker") as worker, runtime(store, roles["api"], "api") as api:
        assert execute_once(worker, tmp_path, execute=report_worker)
        assert execute_once(worker, tmp_path, execute=report_worker)
        for tenant, actor, job in zip(tenants, [owner, other], jobs):
            item = api.job(tenant, actor, job["id"])
            assert item["status"] == "completed" and len(item["artifacts"]) == 2
            retention.hold(api, tenant, actor, job["id"], "Fixture hold")
            retention.hold(api, tenant, actor, job["id"], "Fixture release", active=False)
            assert retention.list_state(api, tenant, actor)["holds"][0]["active"] is False
        with TestClient(create_app(settings, api, verifier=verifier), raise_server_exceptions=False) as client:
            client.headers["Authorization"] = "Bearer " + token()
            for job, tenant in zip(jobs, tenants):
                for artifact in api.job(tenant, owner if tenant == tenants[0] else other, job["id"])["artifacts"]:
                    response = client.get(f"/api/v1/tenants/{tenant}/artifacts/{artifact['id']}")
                    assert response.status_code == (200 if tenant == tenants[0] else 404)
                    if response.status_code == 200:
                        assert hashlib.sha256(response.content).hexdigest() == artifact["sha256"]
            connection = api.connection_list(tenants[0], owner)[0]["id"]
            queued = api.submit(tenants[0], owner, connection, "cancel-fixture")
            api.cancel(tenants[0], owner, queued["id"])
            assert worker.claim() is None


@pytest.mark.parametrize("privilege", ["BYPASSRLS", "SUPERUSER", "CREATEDB", "CREATEROLE", "REPLICATION"])
def test_hardening_refuses_privileged_runtime_roles_without_changes(store, roles, privilege):
    with store.engine.begin() as c:
        c.exec_driver_sql(f'ALTER ROLE "{roles["api"]}" {privilege}')
    with pytest.raises(ValueError, match="unprivileged"):
        security.harden(store.engine, roles["api"], roles["worker"], apply=True)
    with store.engine.connect() as c:
        assert not security._relations(c, security.namespace(c))["cris_jobs"]["relrowsecurity"]


def test_hardening_and_guard_refuse_extra_policies_and_inherited_roles(store, roles):
    security.harden(store.engine, roles["api"], roles["worker"], apply=True)
    with store.engine.begin() as c:
        c.exec_driver_sql(f'CREATE POLICY extra ON "{security.namespace(c)}".cris_jobs TO PUBLIC USING (true)')
    with pytest.raises(ValueError, match="Unexpected row policies"):
        security.harden(store.engine, roles["api"], roles["worker"], apply=True)
    with runtime(store, roles["api"], "api") as app:
        with pytest.raises(ValueError, match="row policies"):
            security.check_runtime(app.engine, "api")
    with store.engine.begin() as c:
        c.exec_driver_sql(f'GRANT "{roles["worker"]}" TO "{roles["api"]}"')
    with pytest.raises(ValueError, match="memberships"):
        security.harden(store.engine, roles["api"], roles["worker"])


def test_guard_detects_column_grant_drift_and_rehardening_removes_it(store, roles):
    security.harden(store.engine, roles["api"], roles["worker"], apply=True)
    with store.engine.begin() as c:
        c.exec_driver_sql(f'GRANT UPDATE (quota_bytes) ON "{security.namespace(c)}".cris_tenant_limits TO "{roles["api"]}"')
    with runtime(store, roles["api"], "api") as app:
        with pytest.raises(ValueError, match="column privileges"):
            security.check_runtime(app.engine, "api")
        security.harden(store.engine, roles["api"], roles["worker"], apply=True)
        assert security.check_runtime(app.engine, "api")["verified"]


def test_parallel_api_transactions_keep_tenants_separate(store, roles):
    owner, other, tenants, jobs = seed(store)
    security.harden(store.engine, roles["api"], roles["worker"], apply=True)
    def inspect(index):
        with runtime(store, roles["api"], "api") as api:
            for _ in range(5):
                with api.engine.begin() as c:
                    api._access(c, tenants[index], [owner, other][index])
                    assert c.execute(select(s.jobs.c.id)).scalars().all() == [jobs[index]["id"]]
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(inspect, [0, 1]))


@pytest.mark.parametrize("identifier", ["public; DROP TABLE cris_jobs", "MixedCase", "x" * 64, "a-b", ""])
def test_database_identifiers_cannot_inject_ddl(identifier):
    with pytest.raises(ValueError, match="identifier"):
        security.identifier(identifier)
