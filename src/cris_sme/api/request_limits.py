"""Bound connection workers and pre-dispatch header reading for the local API."""
import threading
import time
from http.server import ThreadingHTTPServer


DEFAULT_MAX_CONNECTIONS = 16


class BoundedHTTPServer(ThreadingHTTPServer):
    def __init__(self, server_address, handler, *, max_connections=DEFAULT_MAX_CONNECTIONS):
        if isinstance(max_connections, bool) or not isinstance(max_connections, int) or max_connections < 1:
            raise ValueError("max connections must be a positive integer")
        self._connection_slots = threading.BoundedSemaphore(max_connections)
        super().__init__(server_address, handler)

    def process_request(self, request, client_address):
        if not self._connection_slots.acquire(blocking=False):
            # Never block the accept loop trying to write to an overloaded client.
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._connection_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._connection_slots.release()


class HeaderDeadlineReader:
    """Keep over-read body bytes while limiting all header lines to one deadline."""
    def __init__(self, stream, connection, timeout):
        self.stream = stream
        self.connection = connection
        self.timeout = timeout
        self.deadline = None
        self.pending = bytearray()

    def start_headers(self):
        self.deadline = time.monotonic() + self.timeout

    def finish_headers(self):
        self.deadline = None
        self.connection.settimeout(self.timeout)

    def _check_deadline(self):
        if self.deadline is not None:
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Request header deadline exceeded")
            self.connection.settimeout(remaining)

    def readline(self, size=-1):
        while True:
            self._check_deadline()
            limit = len(self.pending) if size < 0 else min(size, len(self.pending))
            newline = self.pending.find(b"\n", 0, limit)
            if newline >= 0:
                limit = newline + 1
            if newline >= 0 or (size >= 0 and len(self.pending) >= size):
                result = bytes(self.pending[:limit])
                del self.pending[:limit]
                return result
            chunk_size = 8192 if size < 0 else min(8192, size - len(self.pending))
            chunk = self.stream.read1(chunk_size)
            self._check_deadline()
            if not chunk:
                result = bytes(self.pending)
                self.pending.clear()
                return result
            self.pending.extend(chunk)

    def read1(self, size):
        if self.pending:
            result = bytes(self.pending[:size])
            del self.pending[:size]
            return result
        return self.stream.read1(size)

    def close(self):
        self.stream.close()
