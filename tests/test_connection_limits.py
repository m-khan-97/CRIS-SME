"""Pre-dispatch deadlines and bounded worker admission on the local API."""
import socket
import time
from http.server import ThreadingHTTPServer
from io import BytesIO
from threading import Event, Thread
from types import SimpleNamespace

import pytest

from cris_sme.api.local_runner import create_handler
from cris_sme.api.request_limits import BoundedHTTPServer, HeaderDeadlineReader
from tests.test_request_deadlines import Connection


@pytest.mark.parametrize("value", [0, -1, True, 1.5, "16", None])
def test_connection_limit_requires_positive_integer(value):
    with pytest.raises(ValueError, match="positive integer"):
        BoundedHTTPServer(("127.0.0.1", 0), create_handler(SimpleNamespace()), max_connections=value)


def test_header_reader_preserves_prefetched_body_and_line_limit():
    stream = BytesIO(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n{\"ok\":true}")
    reader = HeaderDeadlineReader(stream, Connection(), 1)
    reader.start_headers()
    assert reader.readline(3) == b"GET"
    assert reader.readline(65537) == b" / HTTP/1.1\r\n"
    assert reader.readline(65537) == b"Host: localhost\r\n"
    assert reader.readline(65537) == b"\r\n"
    reader.finish_headers()
    assert reader.read1(4) == b'{"ok'
    assert reader.read1(100) == b'":true}'
    assert reader.read1(1) == b""
    reader.close()
    assert stream.closed


def test_header_lines_share_one_deadline(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr("cris_sme.api.request_limits.time.monotonic", lambda: clock[0])

    class Stream:
        def read1(self, size):
            clock[0] += 0.4
            return b"X: value\r\n"

    connection = Connection()
    reader = HeaderDeadlineReader(Stream(), connection, 1)
    reader.start_headers()
    assert reader.readline(65537) == b"X: value\r\n"
    assert reader.readline(65537) == b"X: value\r\n"
    with pytest.raises(TimeoutError, match="header deadline"):
        reader.readline(65537)


def test_incomplete_header_eof_returns_remaining_bytes():
    reader = HeaderDeadlineReader(BytesIO(b"Host: local"), Connection(), 1)
    reader.start_headers()
    assert reader.readline() == b"Host: local"
    assert reader.readline() == b""


def test_deadline_rejects_already_buffered_lines_after_time_expires(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr("cris_sme.api.request_limits.time.monotonic", lambda: clock[0])
    reader = HeaderDeadlineReader(BytesIO(b"line1\nline2\n"), Connection(), 1)
    reader.start_headers()
    assert reader.readline() == b"line1\n"
    clock[0] = 2
    with pytest.raises(TimeoutError):
        reader.readline()


@pytest.mark.parametrize("initial", [b"G", b"GET /health HTTP/1.1\r\nHost: localhost\r\nX: "])
def test_request_line_and_header_trickles_hit_total_deadline(initial):
    server = BoundedHTTPServer(("127.0.0.1", 0), create_handler(SimpleNamespace(), request_read_timeout=0.25))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    stop = Event()
    sender = None
    try:
        with socket.create_connection(server.server_address, timeout=3) as client:
            client.sendall(initial)

            def trickle():
                while not stop.wait(0.03):
                    try:
                        client.sendall(b"x")
                    except OSError:
                        return

            sender = Thread(target=trickle, daemon=True)
            sender.start()
            assert client.recv(4096) == b""
    finally:
        stop.set()
        if sender:
            sender.join(timeout=3)
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)


def test_overflow_is_closed_without_worker_and_capacity_recovers():
    entered = Event()
    release = Event()
    seen = []

    def handler(request, address, server):
        seen.append(address)
        entered.set()
        release.wait(3)
        request.sendall(b"ok")

    server = BoundedHTTPServer(("127.0.0.1", 0), handler, max_connections=1)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with socket.create_connection(server.server_address, timeout=3) as first:
            assert entered.wait(2)
            with socket.create_connection(server.server_address, timeout=3) as overflow:
                assert overflow.recv(16) == b""
            assert len(seen) == 1
            release.set()
            assert first.recv(16) == b"ok"
        deadline = time.monotonic() + 3
        while True:
            with socket.create_connection(server.server_address, timeout=3) as next_client:
                if next_client.recv(16) == b"ok":
                    break
            assert time.monotonic() < deadline
            time.sleep(0.01)
        assert len(seen) == 2
    finally:
        release.set()
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)


def test_thread_start_failure_releases_connection_slot(monkeypatch):
    server = BoundedHTTPServer(("127.0.0.1", 0), create_handler(SimpleNamespace()), max_connections=1)
    def fail(*args):
        raise RuntimeError("thread creation failed")

    monkeypatch.setattr(ThreadingHTTPServer, "process_request", fail)
    try:
        for _ in range(2):
            with pytest.raises(RuntimeError, match="thread creation"):
                server.process_request(None, None)
    finally:
        server.server_close()


def test_worker_failure_releases_connection_slot(monkeypatch):
    server = BoundedHTTPServer(("127.0.0.1", 0), create_handler(SimpleNamespace()), max_connections=1)
    def fail(*args):
        raise RuntimeError("worker failed")

    monkeypatch.setattr(ThreadingHTTPServer, "process_request_thread", fail)
    try:
        assert server._connection_slots.acquire(blocking=False)
        with pytest.raises(RuntimeError):
            server.process_request_thread(None, None)
        assert server._connection_slots.acquire(blocking=False)
        server._connection_slots.release()
    finally:
        server.server_close()


def test_cli_passes_limits_to_server(monkeypatch):
    from cris_sme.api import local_runner

    captured = {}
    monkeypatch.setattr("sys.argv", ["cris-api", "--max-connections", "4", "--request-read-timeout", "2.5"])
    monkeypatch.setattr(local_runner, "run_server", lambda **kwargs: captured.update(kwargs))
    assert local_runner.main() == 0
    assert captured["max_connections"] == 4
    assert captured["request_read_timeout"] == 2.5


def test_run_server_uses_bounded_server_and_closes_on_exit(tmp_path, monkeypatch):
    from cris_sme.api import local_runner

    calls = []
    class Server:
        def __init__(self, address, handler, *, max_connections):
            calls.append(max_connections)

        def serve_forever(self):
            raise KeyboardInterrupt

        def server_close(self):
            calls.append("closed")

    monkeypatch.setattr(local_runner, "BoundedHTTPServer", Server)
    with pytest.raises(KeyboardInterrupt):
        local_runner.run_server(output_dir=tmp_path, figure_dir=tmp_path / "figures", max_connections=3)
    assert calls == [3, "closed"]
