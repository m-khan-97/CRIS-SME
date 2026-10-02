import os
from pathlib import Path
import subprocess
import sys
import select

import pytest

from cris_sme.api import local_runner
from cris_sme.api.state_ownership import own_state


def paths(root):
    return root / "reports", root / "figures", root / "state.sqlite3"


@pytest.mark.parametrize("shared", [0, 1, 2])
def test_each_shared_namespace_blocks_second_owner(tmp_path, shared):
    first = paths(tmp_path / "first")
    second = list(paths(tmp_path / "second"))
    second[shared] = first[shared]
    with own_state(*first):
        with pytest.raises(RuntimeError, match="Another local API"):
            with own_state(*second):
                pytest.fail("second owner admitted")
    with own_state(*second):
        pass


def test_alias_and_duplicate_paths(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(target, target_is_directory=True)
    with own_state(target, target, target / "db"):
        with pytest.raises(RuntimeError, match="Another local API"):
            with own_state(alias, alias, alias / "db"):
                pass


def test_independent_namespaces_can_coexist(tmp_path):
    with own_state(*paths(tmp_path / "a")), own_state(*paths(tmp_path / "b")):
        pass


def test_exception_releases_without_unlinking(tmp_path):
    with pytest.raises(ValueError):
        with own_state(*paths(tmp_path)):
            raise ValueError("stop")
    lock = tmp_path / "reports" / ".cris-api.lock"
    inode = lock.stat().st_ino
    with own_state(*paths(tmp_path)):
        assert lock.stat().st_ino == inode
        assert lock.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("kind", ["symlink", "fifo"])
def test_unsafe_lock_files_rejected(tmp_path, kind):
    output, figure, db = paths(tmp_path)
    output.mkdir()
    lock = output / ".cris-api.lock"
    if kind == "symlink":
        target = tmp_path / "target"
        target.write_text("untouched")
        lock.symlink_to(target)
    else:
        os.mkfifo(lock)
    with pytest.raises((OSError, RuntimeError)):
        with own_state(output, figure, db):
            pass
    if kind == "symlink":
        assert target.read_text() == "untouched"


def test_process_contention_and_exit_recovery(tmp_path):
    script = """
import sys
from pathlib import Path
from cris_sme.api.state_ownership import own_state
root = Path(sys.argv[1])
with own_state(root/'reports', root/'figures', root/'state.sqlite3'):
    print('ready', flush=True)
    sys.stdin.readline()
"""
    process = subprocess.Popen([sys.executable, "-c", script, str(tmp_path)],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
                               env={**os.environ, "PYTHONPATH": str(Path(local_runner.__file__).parents[2])})
    try:
        assert select.select([process.stdout], [], [], 5)[0], "child did not acquire state"
        assert process.stdout.readline().strip() == "ready"
        with pytest.raises(RuntimeError, match="Another local API"):
            with own_state(*paths(tmp_path)):
                pass
        process.kill()
        process.wait(timeout=5)
        with own_state(*paths(tmp_path)):
            pass
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        process.stdin.close()
        process.stdout.close()


@pytest.mark.parametrize("options", [
    {"port": -1}, {"port": 65536}, {"port": True},
    {"request_read_timeout": 0}, {"request_read_timeout": float("nan")},
    {"request_read_timeout": float("inf")}, {"request_read_timeout": True},
    {"max_connections": 0}, {"max_connections": True}, {"max_connections": 1.5},
    {"allowed_origins": ("invalid",)},
])
def test_invalid_startup_does_not_touch_state(tmp_path, options):
    with pytest.raises(ValueError):
        local_runner.run_server(output_dir=tmp_path / "reports", figure_dir=tmp_path / "figures", **options)
    assert list(tmp_path.iterdir()) == []


def test_conflict_precedes_runner_recovery(tmp_path, monkeypatch):
    def forbidden(**kwargs):
        pytest.fail("runner recovery must not start")
    monkeypatch.setattr(local_runner, "LocalAssessmentRunner", forbidden)
    output, figure, db = paths(tmp_path)
    with own_state(output, figure, db):
        with pytest.raises(RuntimeError, match="Another local API"):
            local_runner.run_server(output_dir=output, figure_dir=figure, database_path=db)


@pytest.mark.parametrize("stage", ["runner", "bind", "serve"])
def test_startup_and_shutdown_failures_release_locks(tmp_path, monkeypatch, stage):
    class Server:
        closed = False

        def __init__(self, *args, **kwargs):
            if stage == "bind":
                raise OSError("bind")

        def serve_forever(self):
            raise OSError("serve")

        def server_close(self):
            Server.closed = True

    def runner(**kwargs):
        if stage == "runner":
            raise OSError("runner")
        return object()

    monkeypatch.setattr(local_runner, "LocalAssessmentRunner", runner)
    monkeypatch.setattr(local_runner, "BoundedHTTPServer", Server)
    output, figure, db = paths(tmp_path)
    with pytest.raises(OSError, match=stage):
        local_runner.run_server(output_dir=output, figure_dir=figure, database_path=db)
    assert Server.closed == (stage == "serve")
    with own_state(output, figure, db):
        pass
