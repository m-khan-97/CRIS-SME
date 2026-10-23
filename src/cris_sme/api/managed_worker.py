"""Bound the lifetime of a local cloud worker and its process group."""
import locale
import math
import os
import selectors
import signal
import subprocess
import sys
import threading
import time
from typing import Mapping


DEFAULT_OUTPUT_LIMIT = 8 * 1024 * 1024


class WorkerCancelled(Exception):
    """Cancellation was requested before the command completed."""


class WorkerOutputLimitExceeded(Exception):
    """Combined worker stdout/stderr exceeded the configured byte budget."""


def _signal_group(process: subprocess.Popen[bytes], sig: int) -> None:
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        pass


def run_managed(
    command: list[str], *, env: Mapping[str, str], timeout: float,
    cancel: threading.Event, capture_output: bool = True, text: bool = True,
    output_limit: int = DEFAULT_OUTPUT_LIMIT,
) -> subprocess.CompletedProcess[str]:
    """Execute in a dedicated POSIX process group, cleaning it before return."""
    if os.name != "posix":
        raise RuntimeError("Managed cloud workers require POSIX process groups")
    if not capture_output or not text or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("Managed workers require captured text and a positive timeout")
    if isinstance(output_limit, bool) or not isinstance(output_limit, int) or output_limit < 1:
        raise ValueError("Managed worker output limit must be a positive integer")
    if cancel.is_set():
        raise WorkerCancelled()
    streams = selectors.DefaultSelector()
    try:
        process = subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True)
    except BaseException:
        streams.close()
        raise
    deadline = time.monotonic() + timeout
    stdout, stderr = bytearray(), bytearray()
    captured = 0
    try:
        assert process.stdout is not None and process.stderr is not None
        for pipe, buffer in ((process.stdout, stdout), (process.stderr, stderr)):
            os.set_blocking(pipe.fileno(), False)
            streams.register(pipe, selectors.EVENT_READ, buffer)
        while True:
            if cancel.is_set():
                raise WorkerCancelled()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(command, timeout)
            for key, _ in streams.select(timeout=min(0.1, remaining)):
                chunk = os.read(key.fd, min(65536, output_limit - captured + 1))
                if not chunk:
                    streams.unregister(key.fileobj)
                    continue
                captured += len(chunk)
                if captured > output_limit:
                    raise WorkerOutputLimitExceeded("Assessment worker exceeded its captured-output budget.")
                key.data.extend(chunk)
            if not streams.get_map() and process.poll() is not None:
                encoding = "utf-8" if sys.flags.utf8_mode else locale.getencoding()
                def decode(buffer: bytearray) -> str:
                    return buffer.decode(encoding).replace("\r\n", "\n").replace("\r", "\n")
                return subprocess.CompletedProcess(command, process.returncode, decode(stdout), decode(stderr))
    finally:
        streams.close()
        _signal_group(process, signal.SIGTERM)
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
        finally:
            _signal_group(process, signal.SIGKILL)
            process.wait(timeout=2)
