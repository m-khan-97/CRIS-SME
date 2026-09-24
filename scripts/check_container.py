"""Exercise a private mock-only container without exposing a host port."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
import uuid


def docker(*args: str) -> str:
    return subprocess.check_output(["docker", *args], text=True, timeout=180).strip()


def healthy(name: str) -> None:
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        state = json.loads(docker("inspect", name))[0]["State"]
        if not state["Running"]:
            raise RuntimeError(f"Container stopped before readiness: {state['ExitCode']}")
        if state.get("Health", {}).get("Status") == "healthy":
            return
        time.sleep(1)
    raise RuntimeError("Container readiness timed out")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    name = f"cris-smoke-{uuid.uuid4().hex[:12]}"
    volume = f"{name}-data"
    docker("volume", "create", volume)
    try:
        docker("run", "-d", "--name", name, "--read-only", "--tmpfs", "/tmp:rw,nosuid,size=64m",
               "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
               "--mount", f"type=volume,src={volume},dst=/data", args.image)
        healthy(name)
        docker("exec", name, "python", "-c", "import os; assert os.getuid() == 10001")
        docker("exec", "-e", "CRIS_SME_COLLECTOR=mock", name, "python", "-m", "cris_sme.main")
        check = (
            "import json, urllib.request; "
            "u='http://127.0.0.1:8080/api/report-artifact?path=/data/outputs/reports/cris_sme_report.json'; "
            "r=json.load(urllib.request.urlopen(u, timeout=5)); "
            "assert r['collector_mode']=='mock' and r['prioritized_risks']; "
            "assert b'<html' in urllib.request.urlopen('http://127.0.0.1:8080/', timeout=5).read().lower()"
        )
        docker("exec", name, "python", "-c", check)
        docker("stop", "--time", "15", name)
        state = json.loads(docker("inspect", name))[0]["State"]
        if state["ExitCode"] != 0:
            raise RuntimeError(f"Ungraceful shutdown: {state['ExitCode']}")
        docker("start", name)
        healthy(name)
        docker("exec", name, "python", "-c", check)
        docker("exec", name, "python", "-c",
               "import os, signal; from pathlib import Path; "
               "os.kill(int(Path('/tmp/nginx.pid').read_text()), signal.SIGTERM)")
        if docker("wait", name) == "0":
            raise RuntimeError("Unexpected service exit was reported as success")
        print("Container nonroot, report retrieval, persistence, stop and failure checks passed.")
    except Exception:
        subprocess.run(["docker", "logs", "--tail", "80", name], check=False, timeout=10)
        raise
    finally:
        subprocess.run(["docker", "rm", "-f", name], check=False, timeout=30)
        subprocess.run(["docker", "volume", "rm", volume], check=False, timeout=30)


if __name__ == "__main__":
    main()
