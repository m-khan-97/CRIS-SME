"""Generate hash-locked pip profiles, or check their input/output fingerprints."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PROFILES = {
    "runtime": ["pyproject.toml"],
    "cloud": ["pyproject.toml", "--extra", "azure", "--extra", "aws"],
    "mcp": ["pyproject.toml", "--extra", "mcp"],
    "build": ["requirements/build.in"],
    "dev": ["pyproject.toml", "requirements/build.in", "--extra", "dev",
            "--extra", "azure", "--extra", "aws"],
}
INPUTS = ("pyproject.toml", "requirements/build.in", "scripts/lock_dependencies.py")


def fingerprints(root: Path) -> dict[str, str]:
    paths = [*INPUTS, *(f"requirements/{name}.txt" for name in PROFILES)]
    return {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in paths}


def check(root: Path) -> bool:
    manifest = root / "requirements/lock-manifest.json"
    try:
        return json.loads(manifest.read_text())["sha256"] == fingerprints(root)
    except (OSError, KeyError, ValueError):
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--upgrade", action="store_true")
    args = parser.parse_args()
    if args.check:
        if not check(ROOT):
            raise SystemExit("Dependency locks are missing/stale. Run python scripts/lock_dependencies.py.")
        print("Dependency lock input/output fingerprints match.")
        return
    version = subprocess.check_output(["uv", "--version"], text=True).strip()
    for name, inputs in PROFILES.items():
        command = ["uv", "pip", "compile", *inputs, "--universal", "--python-version", "3.11",
                   "--generate-hashes", "--output-file", f"requirements/{name}.txt",
                   "--custom-compile-command", "python scripts/lock_dependencies.py", "--quiet"]
        if args.upgrade:
            command.append("--upgrade")
        subprocess.run(command, cwd=ROOT, check=True)
    (ROOT / "requirements/lock-manifest.json").write_text(
        json.dumps({"generator": version, "sha256": fingerprints(ROOT)}, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
