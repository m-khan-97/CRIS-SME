"""Lease-fenced workers; each attempt writes to its own private namespace."""
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import threading

from cris_sme.api.artifact_access import read_regular_file
from cris_sme.api.managed_worker import WorkerCancelled, run_managed
from cris_sme.enterprise.cloud import worker_environment
from cris_sme.enterprise.store import new_id


EXPORTS = {"cris_sme_report.json", "cris_sme_report.html", "cris_sme_report.csv",
           "cris_sme_report.sarif", "cris_sme_summary.txt"}


def execute_once(store, root: Path, *, lease_seconds=30, execute=run_managed, shutdown=None):
    lease = store.claim(lease_seconds=lease_seconds)
    if lease is None:
        return False
    cancel, done = threading.Event(), threading.Event()
    def pulse():
        while not done.wait(lease_seconds / 3):
            try:
                if (shutdown is not None and shutdown.is_set()) or not store.heartbeat(lease, lease_seconds=lease_seconds):
                    cancel.set()
                    return
            except Exception:
                cancel.set()
                return
    heart = threading.Thread(target=pulse, daemon=True)
    heart.start()
    state, artifacts = "failed", []
    try:
        attempt = root / lease["tenant_id"] / lease["id"] / lease["lease_token"]
        attempt.mkdir(parents=True, exist_ok=False, mode=0o700)
        output, figures = attempt / "reports", attempt / "figures"
        output.mkdir(mode=0o700)
        figures.mkdir(mode=0o700)
        env = worker_environment(os.environ, lease, output, figures)
        result = execute([sys.executable, "-m", "cris_sme.main"], env=env, timeout=900, cancel=cancel)
        if result.returncode == 0 and not cancel.is_set():
            data = read_regular_file(output, Path("cris_sme_report.json"), max_bytes=16 * 1024 * 1024)
            report = json.loads(data)
            if not isinstance(report, dict) or not isinstance(report.get("run_metadata"), dict):
                raise ValueError("Missing report provenance")
            if report["run_metadata"].get("providers_in_scope") != [lease["connection"]["provider"]] or (
                [org.get("organization_id") for org in report.get("organizations", [])] != [lease["tenant_id"]]):
                raise ValueError("Report scope mismatch")
            for name in sorted(EXPORTS):
                if (output / name).exists():
                    content = read_regular_file(output, Path(name), max_bytes=32 * 1024 * 1024)
                    artifacts.append(dict(id=new_id(), name=name, key=str((output / name).relative_to(root)),
                                          sha256=hashlib.sha256(content).hexdigest(), size=len(content)))
            state = "completed"
    except WorkerCancelled:
        state = "cancelled"
    except Exception:
        state = "failed"
    finally:
        # Stop renewing only after process-group cleanup and publication preparation.
        done.set()
        heart.join(timeout=lease_seconds / 3 + 1)
    if cancel.is_set():
        state = "cancelled"
    store.finish(lease, state, artifacts)
    return True


def run_worker(store, root):
    stop = threading.Event()
    previous = {sig: signal.signal(sig, lambda *args: stop.set()) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        while not stop.is_set():
            try:
                if not execute_once(store, root, shutdown=stop):
                    stop.wait(1)
            except Exception:
                # No credentials, SQL parameters or provider errors enter public logs.
                print("Enterprise worker operation unavailable; retrying.", file=sys.stderr)
                stop.wait(2)
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
