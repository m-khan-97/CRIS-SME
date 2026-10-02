from io import BytesIO
from types import SimpleNamespace

import pytest

from cris_sme.api.local_runner import RequestBodyError, create_handler


class Connection:
    def __init__(self):
        self.timeout = 7.0
        self.changes = []

    def gettimeout(self):
        return self.timeout

    def settimeout(self, value):
        self.timeout = value
        self.changes.append(value)


def reader(stream):
    handler_type = create_handler(SimpleNamespace(), request_read_timeout=1)
    handler = handler_type.__new__(handler_type)
    handler.connection = Connection()
    handler.rfile = stream
    handler.close_connection = False
    return handler


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), float("-inf")])
def test_invalid_deadlines_are_rejected(value):
    with pytest.raises(ValueError, match="finite"):
        create_handler(SimpleNamespace(), request_read_timeout=value)


def test_fragmented_body_uses_remaining_total_budget(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr("cris_sme.api.local_runner.time.monotonic", lambda: clock[0])

    class Stream:
        def read1(self, length):
            clock[0] += 0.25
            return b"x"

    handler = reader(Stream())
    assert handler._read_body(3) == b"xxx"
    assert handler.connection.changes == [1.0, 0.75, 0.5, 7.0]
    assert handler.connection.timeout == 7.0


def test_trickled_bytes_do_not_refresh_deadline(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr("cris_sme.api.local_runner.time.monotonic", lambda: clock[0])

    class Stream:
        def read1(self, length):
            clock[0] += 0.4
            return b"x"

    handler = reader(Stream())
    with pytest.raises(RequestBodyError) as error:
        handler._read_body(5)
    assert error.value.status == 408
    assert handler.close_connection
    assert handler.connection.timeout == 7.0


def test_final_chunk_arriving_after_deadline_is_rejected(monkeypatch):
    times = iter([0.0, 0.1, 1.1])
    monkeypatch.setattr("cris_sme.api.local_runner.time.monotonic", lambda: next(times))
    with pytest.raises(RequestBodyError) as error:
        reader(BytesIO(b"{}"))._read_body(2)
    assert error.value.status == 408


def test_socket_timeout_restores_timeout_and_closes_request():
    class Stream:
        def read1(self, length):
            raise TimeoutError

    handler = reader(Stream())
    with pytest.raises(RequestBodyError) as error:
        handler._read_body(2)
    assert error.value.status == 408
    assert handler.connection.timeout == 7.0
    assert handler.close_connection


def test_truncated_body_restores_timeout():
    handler = reader(BytesIO(b"{"))
    with pytest.raises(RequestBodyError, match="incomplete") as error:
        handler._read_body(2)
    assert error.value.status == 400
    assert handler.connection.timeout == 7.0


@pytest.mark.parametrize("partial_headers", [False, True])
def test_stalled_real_connection_is_closed_without_cloud_work(partial_headers):
    import socket
    from http.server import ThreadingHTTPServer
    from threading import Thread

    calls = []
    runner = SimpleNamespace(validate_aws_role=lambda payload: calls.append(payload))
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(runner, request_read_timeout=0.2))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with socket.create_connection(server.server_address, timeout=3) as client:
            data = b"POST /api/environment/aws/validate-role HTTP/1.1\r\nHost: localhost\r\n"
            if not partial_headers:
                data += b"Content-Length: 10\r\nContent-Type: application/json\r\n\r\n{"
            client.sendall(data)
            response = bytearray()
            while chunk := client.recv(4096):
                response.extend(chunk)
        if partial_headers:
            assert not response
        else:
            assert b" 408 " in response.splitlines()[0]
        assert calls == []
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)


def test_real_trickle_cannot_extend_body_deadline():
    import socket
    from http.server import ThreadingHTTPServer
    from threading import Event, Thread

    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(SimpleNamespace(), request_read_timeout=0.25))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    stop = Event()
    sender = None
    try:
        with socket.create_connection(server.server_address, timeout=3) as client:
            client.sendall(b"POST /api/environment/aws/validate-role HTTP/1.1\r\n"
                           b"Host: localhost\r\nContent-Length: 128\r\n"
                           b"Content-Type: application/json\r\n\r\n")

            def trickle():
                while not stop.wait(0.03):
                    try:
                        client.sendall(b" ")
                    except OSError:
                        return

            sender = Thread(target=trickle, daemon=True)
            sender.start()
            response = bytearray()
            while chunk := client.recv(4096):
                response.extend(chunk)
            assert b" 408 " in response.splitlines()[0]
    finally:
        stop.set()
        if sender:
            sender.join(timeout=3)
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
