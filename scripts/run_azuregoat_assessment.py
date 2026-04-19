# Helper entrypoint for running CRIS-SME against an AzureGoat lab deployment.
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Run CRIS-SME with vulnerable-lab dataset metadata suitable for AzureGoat."""
    repo_root = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["CRIS_SME_COLLECTOR"] = "azure"
    env.setdefault("CRIS_SME_AZURE_ORGANIZATION_NAME", "AzureGoat Lab")
    env.setdefault("CRIS_SME_AZURE_SECTOR", "Training Lab")
    env["CRIS_SME_DATASET_SOURCE_TYPE"] = "vulnerable_lab"
    env["CRIS_SME_AUTHORIZATION_BASIS"] = "intentionally_vulnerable_lab"
    env["CRIS_SME_DATASET_USE"] = "control_stress_test"

    subprocess.run(
        [sys.executable, "-m", "cris_sme.main"],
        cwd=repo_root,
        env=env,
        check=True,
    )


if __name__ == "__main__":
    main()
