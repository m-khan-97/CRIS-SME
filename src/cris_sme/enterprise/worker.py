"""Lease-fenced workers; each attempt writes to its own private namespace."""
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time

from sqlalchemy import delete

from cris_sme.api.artifact_access import read_regular_file
from cris_sme.api.managed_worker import WorkerCancelled, run_managed
from cris_sme.enterprise.cloud import worker_environment
from cris_sme.enterprise.store import Rejected, new_id
from cris_sme.enterprise.storage import LocalStorage
from cris_sme.enterprise import operations
from cris_sme.enterprise import schema as s


EXPORTS = {"cris_sme_report.json", "cris_sme_report.html", "cris_sme_report.csv",
           "cris_sme_report.sarif", "cris_sme_summary.txt"}


def execute_once(store, root: Path, *, lease_seconds=30, execute=run_managed, shutdown=None, storage=None, worker_id=None):
    storage = storage or LocalStorage(root)
    lease = store.claim(lease_seconds=lease_seconds)
    if lease is None:
        return False
    if worker_id:
        operations.touch_worker(store, worker_id, True)
    with store.engine.connect() as c:
        limits = operations.policy(c, lease["tenant_id"])
    attempt = root / lease["tenant_id"] / lease["id"] / lease["lease_token"]
    guard = operations.WorkspaceGuard(root, lease["tenant_id"], attempt, limits["quota_bytes"], limits["max_artifacts"])
    cancel, done = threading.Event(), threading.Event()
    resource_error = []
    def pulse():
        next_heartbeat = 0.0
        while not done.wait(min(1, lease_seconds / 3)):
            try:
                guard.check()
                if shutdown is not None and shutdown.is_set():
                    cancel.set()
                    return
                if time.monotonic() >= next_heartbeat:
                    if not store.heartbeat(lease, lease_seconds=lease_seconds):
                        cancel.set()
                        return
                    if worker_id:
                        operations.touch_worker(store, worker_id, True)
                    next_heartbeat = time.monotonic() + lease_seconds / 3
            except operations.ResourceLimit as exc:
                resource_error.append(exc.code)
                cancel.set()
                return
            except Exception:
                cancel.set()
                return
    heart = threading.Thread(target=pulse, daemon=True)
    heart.start()
    state, artifacts, error_code = "failed", [], ""
    try:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        operations.check_disk(root, required_bytes=operations.STAGING_BYTES)
        store.publication_budget(lease, operations.JOB_BYTES, operations.JOB_FILES)
        attempt.mkdir(parents=True, exist_ok=False, mode=0o700)
        output, figures = attempt / "reports", attempt / "figures"
        output.mkdir(mode=0o700)
        figures.mkdir(mode=0o700)
        guard.check()
        env = worker_environment(os.environ, lease, output, figures)
        result = execute([sys.executable, "-m", "cris_sme.main"], env=env, timeout=900, cancel=cancel)
        if result.returncode == 0 and not cancel.is_set():
            guard.check()
            data = read_regular_file(output, Path("cris_sme_report.json"), max_bytes=16 * 1024 * 1024)
            report = json.loads(data)
            if not isinstance(report, dict) or not isinstance(report.get("run_metadata"), dict):
                raise ValueError("Missing report provenance")
            if report["run_metadata"].get("providers_in_scope") != [lease["connection"]["provider"]] or (
                [org.get("organization_id") for org in report.get("organizations", [])] != [lease["tenant_id"]]):
                raise ValueError("Report scope mismatch")
            files = {}
            for name in sorted(EXPORTS):
                if (output / name).exists():
                    files[name] = read_regular_file(output, Path(name), max_bytes=32 * 1024 * 1024)
            if sum(map(len, files.values())) > operations.JOB_BYTES:
                raise operations.ResourceLimit("staging_limit")
            store.publication_budget(lease, sum(map(len, files.values())), len(files))
            for name, content in files.items():
                storage.publish(str((output / name).relative_to(root)), content)
                artifacts.append(dict(id=new_id(), name=name, key=str((output / name).relative_to(root)),
                                      sha256=hashlib.sha256(content).hexdigest(), size=len(content)))
            state = "completed"
    except WorkerCancelled:
        state = "cancelled"
    except operations.ResourceLimit as exc:
        state, error_code = "failed", exc.code
    except Rejected as exc:
        state, error_code = "failed", "storage_quota" if exc.status == 429 else "worker_failed"
    except Exception:
        state = "failed"
    finally:
        # Stop renewing only after process-group cleanup and publication preparation.
        done.set()
        heart.join(timeout=lease_seconds / 3 + 1)
    if cancel.is_set():
        state = "failed" if resource_error else "cancelled"
        error_code = resource_error[0] if resource_error else ""
    store.finish(lease, state, artifacts, error_code=error_code)
    return True


def run_worker(store, root, storage=None):
    store.check_database_profile("worker")
    stop = threading.Event()
    worker_id = new_id()
    previous = {sig: signal.signal(sig, lambda *args: stop.set()) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        while not stop.is_set():
            try:
                operations.touch_worker(store, worker_id, False)
                if not execute_once(store, root, shutdown=stop, storage=storage, worker_id=worker_id):
                    stop.wait(1)
            except Exception:
                # No credentials, SQL parameters or provider errors enter public logs.
                print("Enterprise worker operation unavailable; retrying.", file=sys.stderr)
                stop.wait(2)
    finally:
        try:
            with store.engine.begin() as c:
                c.execute(delete(s.workers).where(s.workers.c.id == worker_id))
        except Exception:
            pass
        for sig, handler in previous.items():
            signal.signal(sig, handler)
