from __future__ import annotations

import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from cris_sme.collectors.mock_collector import MockCollector
from cris_sme.controls.catalog import load_control_catalog
from cris_sme.data_paths import policy_data_path


def test_policies_do_not_depend_on_working_directory(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "control_catalog.json").write_text("[]")
    monkeypatch.chdir(tmp_path)
    load_control_catalog.cache_clear()
    assert len(load_control_catalog()) == 36
    assert MockCollector().collect_profiles()
    assert policy_data_path("cyber_insurance_questions.json").is_file()


def test_explicit_catalog_path_still_overrides(tmp_path: Path) -> None:
    custom = tmp_path / "custom.json"
    custom.write_text("[]")
    assert load_control_catalog(custom) == {}


def test_missing_policy_is_not_silently_empty() -> None:
    with pytest.raises(FileNotFoundError):
        policy_data_path("nonexistent.json")
    with pytest.raises(ValueError):
        policy_data_path("../control_catalog.json")


def start_supervisor(tmp_path: Path, *, ignore_term: bool = False, fail: bool = False):
    ready = tmp_path / "ready"
    child = (
        "import os, signal, time; from pathlib import Path; "
        + ("signal.signal(signal.SIGTERM, signal.SIG_IGN); " if ignore_term else "")
        + f"Path({str(ready)!r}).write_text(str(os.getpid())); time.sleep(60)"
    )
    commands = [[sys.executable, "-c", child]]
    if fail:
        commands.append([sys.executable, "-c", "import time; time.sleep(0.5); raise SystemExit(7)"])
    code = (
        "from cris_sme.api.supervisor import supervise; "
        f"raise SystemExit(supervise({commands!r}, shutdown_timeout=0.3))"
    )
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    process = subprocess.Popen([sys.executable, "-c", code], env=env)
    return process, ready


def wait_ready(process: subprocess.Popen, ready: Path) -> int:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if ready.exists():
            return int(ready.read_text())
        if process.poll() is not None:
            pytest.fail("Supervisor exited before child startup")
        time.sleep(0.02)
    pytest.fail("Supervisor did not start child")


@pytest.mark.skipif(os.name != "posix", reason="Container uses POSIX process groups")
@pytest.mark.parametrize("sig,ignore_term", [(signal.SIGTERM, False), (signal.SIGINT, False),
                                           (signal.SIGTERM, True)])
def test_supervisor_stops_and_reaps_children(tmp_path: Path, sig: int, ignore_term: bool) -> None:
    process, ready = start_supervisor(tmp_path, ignore_term=ignore_term)
    try:
        pid = wait_ready(process, ready)
        process.send_signal(sig)
        assert process.wait(timeout=5) == 0
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)


@pytest.mark.skipif(os.name != "posix", reason="Container uses POSIX process groups")
def test_supervisor_service_failure_stops_sibling(tmp_path: Path) -> None:
    process, ready = start_supervisor(tmp_path, fail=True)
    try:
        pid = wait_ready(process, ready)
        assert process.wait(timeout=5) == 7
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
