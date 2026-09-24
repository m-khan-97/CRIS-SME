"""Build sdist/wheel and run a mock assessment in a clean installed environment."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import venv
import zipfile


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="cris-package-") as scratch:
        work = Path(scratch)
        source = work / "source"
        source.mkdir()
        for name in ("pyproject.toml", "setup.py", "MANIFEST.in", "README.md", "LICENSE"):
            shutil.copy2(root / name, source / name)
        for name in ("src", "data"):
            shutil.copytree(root / name, source / name, ignore=shutil.ignore_patterns(
                "__pycache__", "*.pyc", "*.egg-info",
            ))
        subprocess.run([sys.executable, "-m", "build", "--no-isolation", "--outdir", str(work / "dist"),
                        str(source)], check=True)
        wheel, = (work / "dist").glob("*.whl")
        with zipfile.ZipFile(wheel) as archive:
            for asset in (root / "data").glob("*.json"):
                if asset.name in {"finding_exceptions.json", "mute_rules.json"}:
                    if f"cris_sme/_data/{asset.name}" in archive.namelist():
                        raise RuntimeError(f"Mutable registry leaked into wheel: {asset.name}")
                    continue
                if archive.read(f"cris_sme/_data/{asset.name}") != asset.read_bytes():
                    raise RuntimeError(f"Packaged policy differs: {asset.name}")
        environment = work / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / "bin" / "python"
        subprocess.run([str(python), "-m", "pip", "install", "--require-hashes",
                        "-r", str(root / "requirements/runtime.txt")], check=True)
        subprocess.run([str(python), "-m", "pip", "install", "--no-deps", str(wheel)], check=True)
        subprocess.run([str(python), "-m", "pip", "check"], check=True)
        # Remove the copied source before executing: a fallback to it must fail.
        shutil.rmtree(source)
        run = work / "run"
        run.mkdir()
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("CRIS_SME_", "AWS_", "AZURE_", "PYTHON"))}
        env.update({"CRIS_SME_COLLECTOR": "mock", "PYTHONNOUSERSITE": "1"})
        subprocess.run([str(python), "-m", "cris_sme.main"], cwd=run, env=env,
                       check=True, stdout=subprocess.DEVNULL, timeout=120)
        reports = run / "outputs" / "reports"
        for name in ("cris_sme_report.json", "cris_sme_report.html", "cris_sme_dashboard.html",
                     "cris_sme_dashboard_payload.json", "cris_sme_summary.txt",
                     "cris_sme_evidence_snapshot.json"):
            if not (reports / name).is_file() or (reports / name).stat().st_size == 0:
                raise RuntimeError(f"Missing/empty installed assessment output: {name}")
        report = json.loads((reports / "cris_sme_report.json").read_text())
        if report.get("collector_mode") != "mock" or not report.get("prioritized_risks"):
            raise RuntimeError("Installed assessment did not produce mock findings")
        print("Installed sdist/wheel smoke test passed, outside the source checkout.")


if __name__ == "__main__":
    main()
