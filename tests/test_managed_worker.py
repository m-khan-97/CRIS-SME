"""Exercise real local subprocess cleanup, including descendants."""
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest

from cris_sme.api.managed_worker import WorkerCancelled, WorkerOutputLimitExceeded, run_managed


def wait_for_file(path):
    deadline = time.monotonic() + 5
    while not path.exists() or not path.read_text():
        assert time.monotonic() < deadline
        time.sleep(0.01)


def alive(pid):
    status = Path(f"/proc/{pid}/stat")
    try:
        return status.read_text().rsplit(")", 1)[1].split()[0] != "Z"
    except (FileNotFoundError, ProcessLookupError):
        return False


@pytest.mark.parametrize("error", [FileNotFoundError, ProcessLookupError])
def test_process_disappearance_during_stat_read_means_not_alive(monkeypatch, error):
    def disappeared(*args, **kwargs):
        raise error()
    monkeypatch.setattr(Path, "read_text", disappeared)
    assert not alive(12345)


def test_captures_command_result():
    result = run_managed([sys.executable, "-c", "import sys; print('out'); print('err',file=sys.stderr); sys.exit(3)"],
                         env=os.environ, timeout=5, cancel=threading.Event())
    assert (result.returncode, result.stdout, result.stderr) == (3, "out\n", "err\n")


def test_precancel_does_not_spawn(monkeypatch):
    cancel = threading.Event()
    cancel.set()
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: pytest.fail("spawned cancelled command"))
    with pytest.raises(WorkerCancelled):
        run_managed(["unused"], env={}, timeout=5, cancel=cancel)


@pytest.mark.parametrize("mode", ["cancel", "timeout", "normal"])
def test_cleans_process_group_and_background_child(tmp_path, mode):
    ready = tmp_path / "pids"
    script = """
import os, subprocess, sys, signal, time
from pathlib import Path
signal.signal(signal.SIGTERM, signal.SIG_IGN)
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
Path(sys.argv[1]).write_text(f'{os.getpid()} {child.pid}')
if sys.argv[2] != 'normal': time.sleep(60)
"""
    cancel = threading.Event()
    outcomes = []
    def run():
        try:
            outcomes.append(run_managed([sys.executable, "-c", script, str(ready), mode],
                                        env=os.environ, timeout=0.5 if mode == "timeout" else 10, cancel=cancel))
        except (WorkerCancelled, subprocess.TimeoutExpired) as exc:
            outcomes.append(exc)

    worker = threading.Thread(target=run)
    worker.start()
    try:
        wait_for_file(ready)
        if mode == "cancel":
            cancel.set()
        worker.join(timeout=7)
        assert not worker.is_alive()
        assert len(outcomes) == 1
        if mode == "normal":
            assert outcomes[0].returncode == 0
        else:
            assert isinstance(outcomes[0], WorkerCancelled if mode == "cancel" else subprocess.TimeoutExpired)
        pids = [int(pid) for pid in ready.read_text().split()]
        deadline = time.monotonic() + 2
        while any(alive(pid) for pid in pids) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert all(not alive(pid) for pid in pids)
    finally:
        cancel.set()
        worker.join(timeout=7)


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf")])
def test_rejects_invalid_timeout(timeout):
    with pytest.raises(ValueError):
        run_managed(["unused"], env={}, timeout=timeout, cancel=threading.Event())


@pytest.mark.parametrize("limit", [0, -1, True, 1.5, "1024"])
def test_rejects_invalid_output_limit_before_spawning(monkeypatch, limit):
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: pytest.fail("invalid budget spawned a worker"))
    with pytest.raises(ValueError, match="positive integer"):
        run_managed(["unused"], env={}, timeout=5, cancel=threading.Event(), output_limit=limit)


def test_combined_output_at_exact_limit_is_preserved():
    result = run_managed([sys.executable, "-c", "import os; os.write(1,b'a'*4096); os.write(2,b'b'*4096)"],
                         env=os.environ, timeout=5, cancel=threading.Event(), output_limit=8192)
    assert result.stdout == "a" * 4096
    assert result.stderr == "b" * 4096


@pytest.mark.parametrize("stream", [1, 2, "both"])
def test_output_overflow_stops_noisy_worker(tmp_path, stream):
    ready = tmp_path / "pid"
    script = """
import os, signal, sys, time
from pathlib import Path
signal.signal(signal.SIGTERM, signal.SIG_IGN)
Path(sys.argv[1]).write_text(str(os.getpid()))
fds = [1,2] if sys.argv[2] == 'both' else [int(sys.argv[2])]
try:
    for fd in fds: os.write(fd, b'x'*4097)
except BrokenPipeError: pass
time.sleep(60)
"""
    with pytest.raises(WorkerOutputLimitExceeded, match="captured-output budget"):
        run_managed([sys.executable, "-c", script, str(ready), str(stream)], env=os.environ,
                    timeout=5, cancel=threading.Event(), output_limit=8192 if stream == "both" else 4096)
    assert not alive(int(ready.read_text()))


def test_drains_large_interleaved_streams_without_deadlock():
    script = "import os\nfor _ in range(32):\n os.write(1,b'o'*8192)\n os.write(2,b'e'*8192)"
    result = run_managed([sys.executable, "-c", script], env=os.environ,
                         timeout=5, cancel=threading.Event(), output_limit=524288)
    assert result.stdout == "o" * 262144
    assert result.stderr == "e" * 262144


def test_text_mode_preserves_split_multibyte_and_normalizes_newlines():
    script = "import os,time; os.write(1,b'\\xe2'); time.sleep(.05); os.write(1,b'\\x82\\xac\\r\\nnext\\r'); os.write(2,b'err\\r\\n')"
    result = run_managed([sys.executable, "-c", script], env={**os.environ, "LC_ALL": "C.UTF-8"},
                         timeout=5, cancel=threading.Event())
    assert result.stdout == "\u20ac\nnext\n"
    assert result.stderr == "err\n"


def test_worker_closed_pipes_remains_cancellable(tmp_path):
    ready = tmp_path / "pid"
    script = "import os,time,sys; from pathlib import Path; os.close(1); os.close(2); Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(60)"
    cancel = threading.Event()
    outcomes = []
    def execute():
        try:
            run_managed([sys.executable, "-c", script, str(ready)], env=os.environ, timeout=5, cancel=cancel)
        except WorkerCancelled:
            outcomes.append("cancelled")
    worker = threading.Thread(target=execute)
    worker.start()
    try:
        wait_for_file(ready)
        cancel.set()
        worker.join(timeout=5)
        assert not worker.is_alive()
        assert outcomes == ["cancelled"]
        assert not alive(int(ready.read_text()))
    finally:
        cancel.set()
        worker.join(timeout=5)


def test_spawn_failure_closes_selector(monkeypatch):
    from cris_sme.api import managed_worker
    selector = managed_worker.selectors.DefaultSelector()
    monkeypatch.setattr(managed_worker.selectors, "DefaultSelector", lambda: selector)
    with pytest.raises(FileNotFoundError):
        run_managed(["/nonexistent/cris-test-worker"], env={}, timeout=5, cancel=threading.Event())
    with pytest.raises(ValueError):
        selector.fileno()
