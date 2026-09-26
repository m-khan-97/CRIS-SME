"""Supervise the private API and nginx, terminating their process groups together."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time


def _signal_group(process: subprocess.Popen, signum: int) -> None:
    try:
        os.killpg(process.pid, signum)
    except ProcessLookupError:
        pass


def supervise(commands: list[list[str]], shutdown_timeout: float = 10.0) -> int:
    processes: list[subprocess.Popen] = []
    stopping = False

    def stop(signum: int, frame: object) -> None:
        nonlocal stopping
        stopping = True

    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        for command in commands:
            if stopping:
                return 0
            processes.append(subprocess.Popen(command, start_new_session=True))
        while not stopping:
            for index, process in enumerate(processes):
                result = process.poll()
                if result is not None:
                    print(f"Service {commands[index][0]} exited: {result}", file=sys.stderr)
                    return result if result > 0 else 1
            time.sleep(0.1)
        return 0
    finally:
        for process in processes:
            _signal_group(process, signal.SIGTERM)
        deadline = time.monotonic() + shutdown_timeout
        while time.monotonic() < deadline:
            for process in processes:
                process.poll()
            alive = False
            for process in processes:
                try:
                    os.killpg(process.pid, 0)
                    alive = True
                except ProcessLookupError:
                    pass
            if not alive:
                break
            time.sleep(0.1)
        # A service may exit while leaving a scan subprocess alive in its group.
        for process in processes:
            _signal_group(process, signal.SIGKILL)
            process.wait()
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def main() -> int:
    return supervise([
        [sys.executable, "-m", "cris_sme.api.local_runner", "--host", "127.0.0.1",
         "--port", "8787", "--output-dir", "/data/outputs/reports",
         "--figure-dir", "/data/outputs/figures"],
        ["nginx", "-g", "daemon off;"],
    ])


if __name__ == "__main__":
    raise SystemExit(main())
