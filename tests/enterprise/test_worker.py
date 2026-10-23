from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import threading

import pytest
from sqlalchemy import update

from cris_sme.enterprise import schema as s
from cris_sme.enterprise.worker import execute_once
from tests.enterprise.conftest import aws_connection, submit


def expire(store, job_id, *, attempt=None):
    with store.engine.begin() as c:
        values = {"lease_until": 1}
        if attempt is not None:
            values["attempt"] = attempt
        c.execute(update(s.jobs).where(s.jobs.c.id == job_id).values(**values))


def report_worker(command, **kwargs):
    output = Path(kwargs["env"]["CRIS_SME_OUTPUT_DIR"])
    provider = kwargs["env"]["CRIS_SME_COLLECTOR"]
    report = {"run_metadata": {"run_id": "fixture", "providers_in_scope": [provider]},
              "organizations": [{"organization_id": kwargs["env"][f"CRIS_SME_{provider.upper()}_ORGANIZATION_ID"]}]}
    (output / "cris_sme_report.json").write_text(json.dumps(report))
    (output / "cris_sme_summary.txt").write_text("Fixture result")
    return subprocess.CompletedProcess(command, 0, stdout="private output", stderr="")


def test_completed_run_and_tenant_scoped_immutable_download(context):
    connection = aws_connection(context)
    job = submit(context, connection)
    assert execute_once(context["store"], context["root"], execute=report_worker)
    prefix = f"/api/v1/tenants/{context['tenant']}"
    result = context["client"].get(prefix + f"/assessments/{job['id']}").json()
    assert result["status"] == "completed" and len(result["artifacts"]) == 2
    artifact = result["artifacts"][0]
    response = context["client"].get(prefix + f"/artifacts/{artifact['id']}")
    assert response.status_code == 200
    assert hashlib.sha256(response.content).hexdigest() == artifact["sha256"]
    assert "attachment" in response.headers["Content-Disposition"]
    record = context["store"].artifact(context["tenant"], context["principal"], artifact["id"])
    path = context["root"] / record["key"]
    assert context["tenant"] in path.parts and job["id"] in path.parts
    path.write_bytes(b"tampered")
    assert context["client"].get(prefix + f"/artifacts/{artifact['id']}").status_code == 409


def test_symlink_artifact_is_rejected(context):
    connection = aws_connection(context)
    submit(context, connection)
    assert execute_once(context["store"], context["root"], execute=report_worker)
    job = context["store"].job_list(context["tenant"], context["principal"])[0]
    artifact = context["store"].job(context["tenant"], context["principal"], job["id"])["artifacts"][0]
    record = context["store"].artifact(context["tenant"], context["principal"], artifact["id"])
    path = context["root"] / record["key"]
    path.unlink()
    path.symlink_to("/etc/passwd")
    response = context["client"].get(f"/api/v1/tenants/{context['tenant']}/artifacts/{artifact['id']}")
    assert response.status_code == 503 and "root:" not in response.text


def test_stale_worker_cannot_publish_after_reclaim(context):
    connection = aws_connection(context)
    job = submit(context, connection)
    store = context["store"]
    old = store.claim()
    assert old["organization_name"] == "Fixture organization"
    assert old["attempt"] == 1 and store.heartbeat(old)
    expire(store, job["id"])
    assert not store.heartbeat(old)
    new = store.claim()
    assert new["attempt"] == 2 and new["lease_token"] != old["lease_token"]
    assert not store.finish(old, "completed")
    assert store.finish(new, "completed")
    assert not store.finish(new, "completed")


def test_parallel_claims_do_not_duplicate_work(context):
    connection = aws_connection(context)
    submit(context, connection, "one")
    submit(context, connection, "two")
    barrier = threading.Barrier(4)
    def claim():
        barrier.wait(timeout=5)
        return context["store"].claim()
    with ThreadPoolExecutor(max_workers=4) as workers:
        leases = list(workers.map(lambda _: claim(), range(4)))
    leases = [lease for lease in leases if lease]
    assert len(leases) == 2 and len({lease["id"] for lease in leases}) == 2


def test_disconnect_fences_active_worker_and_queued_scans(context):
    connection = aws_connection(context)
    first = submit(context, connection, "one")
    second = submit(context, connection, "two")
    store = context["store"]
    active = store.claim()
    store.disconnect(context["tenant"], context["principal"], connection)
    assert not store.heartbeat(active)
    assert store.finish(active, "completed")
    assert {row["status"] for row in store.job_list(context["tenant"], context["principal"])} == {"cancelled"}
    assert store.claim() is None
    assert {first["id"], second["id"]} == {row["id"] for row in store.job_list(context["tenant"], context["principal"])}


def test_cancel_queued_running_and_expired_cancelling(context):
    connection = aws_connection(context)
    job = submit(context, connection)
    store = context["store"]
    active = store.claim()
    store.cancel(context["tenant"], context["principal"], job["id"])
    assert not store.heartbeat(active)
    expire(store, job["id"])
    assert store.claim() is None
    assert store.job(context["tenant"], context["principal"], job["id"])["status"] == "cancelled"
    assert not store.finish(active, "completed")


def test_attempt_exhaustion_and_connection_expiry(context):
    connection = aws_connection(context)
    job = submit(context, connection)
    store = context["store"]
    store.claim()
    expire(store, job["id"], attempt=3)
    assert store.claim() is None
    assert store.job(context["tenant"], context["principal"], job["id"])["error_code"] == "attempts_exhausted"
    pending = submit(context, connection, "expired-connection")
    with store.engine.begin() as c:
        c.execute(update(s.connections).where(s.connections.c.id == connection).values(verified_until=1))
    assert store.claim() is None
    assert store.job(context["tenant"], context["principal"], pending["id"])["error_code"] == "connection_unavailable"


@pytest.mark.parametrize("mode", ["nonzero", "exception", "invalid-report", "cancel"])
def test_worker_failure_never_publishes_partial_output(context, mode):
    connection = aws_connection(context)
    job = submit(context, connection)
    def execute(command, **kwargs):
        report_worker(command, **kwargs)
        if mode == "nonzero": return subprocess.CompletedProcess(command, 1)
        if mode == "exception": raise RuntimeError("private worker error")
        if mode == "invalid-report":
            (Path(kwargs["env"]["CRIS_SME_OUTPUT_DIR"]) / "cris_sme_report.json").write_text("{}")
        if mode == "cancel":
            context["store"].cancel(context["tenant"], context["principal"], job["id"])
        return subprocess.CompletedProcess(command, 0)
    assert execute_once(context["store"], context["root"], execute=execute)
    result = context["store"].job(context["tenant"], context["principal"], job["id"])
    assert result["status"] == ("cancelled" if mode == "cancel" else "failed")
    assert result["artifacts"] == [] and "private" not in str(result)


def test_real_heartbeat_detects_revocation_while_task_runs(context):
    connection = aws_connection(context)
    job = submit(context, connection)
    def execute(command, **kwargs):
        context["store"].disconnect(context["tenant"], context["principal"], connection)
        assert kwargs["cancel"].wait(4)
        from cris_sme.api.managed_worker import WorkerCancelled
        raise WorkerCancelled()
    assert execute_once(context["store"], context["root"], lease_seconds=3, execute=execute)
    assert context["store"].job(context["tenant"], context["principal"], job["id"])["status"] == "cancelled"


def test_unexpired_worker_claim_exclusion(context):
    connection = aws_connection(context)
    submit(context, connection)
    assert context["store"].claim() is not None
    assert context["store"].claim() is None


@pytest.mark.parametrize("active", [False, True])
def test_operator_revocation_cancels_their_jobs(context, token, active):
    store = context["store"]
    store.member(context["tenant"], context["principal"], "operator", "operator")
    connection = aws_connection(context)
    context["client"].headers["Authorization"] = "Bearer " + token("operator")
    job = submit(context, connection)
    lease = store.claim() if active else None
    store.member(context["tenant"], context["principal"], "operator", "analyst")
    if active:
        assert not store.heartbeat(lease)
        store.finish(lease, "completed")
    else:
        assert store.claim() is None
    assert store.job(context["tenant"], context["principal"], job["id"])["status"] == "cancelled"


def test_real_managed_subprocess_uses_attempt_namespace(context):
    import sys
    from cris_sme.api.managed_worker import run_managed
    connection = aws_connection(context)
    job = submit(context, connection)
    script = """
import json,os
from pathlib import Path
tenant = os.environ['CRIS_SME_AWS_ORGANIZATION_ID']
report = {'run_metadata':{'run_id':'fixture-process','providers_in_scope':['aws']},'organizations':[{'organization_id':tenant}]}
(Path(os.environ['CRIS_SME_OUTPUT_DIR'])/'cris_sme_report.json').write_text(json.dumps(report))
"""
    def execute(command, **kwargs):
        return run_managed([sys.executable, "-c", script], **kwargs)
    assert execute_once(context["store"], context["root"], execute=execute)
    assert context["store"].job(context["tenant"], context["principal"], job["id"])["status"] == "completed"


def test_wrong_tenant_report_is_never_published(context):
    connection = aws_connection(context)
    job = submit(context, connection)
    def execute(command, **kwargs):
        result = report_worker(command, **kwargs)
        path = Path(kwargs["env"]["CRIS_SME_OUTPUT_DIR"]) / "cris_sme_report.json"
        report = json.loads(path.read_text())
        report["organizations"] = [{"organization_id": "different-tenant"}]
        path.write_text(json.dumps(report))
        return result
    execute_once(context["store"], context["root"], execute=execute)
    assert context["store"].job(context["tenant"], context["principal"], job["id"])["status"] == "failed"
