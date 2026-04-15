# Automation entrypoint for running CRIS-SME assessments in scheduled or repeatable workflows.
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Run the CRIS-SME assessment with explicit collector and output settings."""
    parser = argparse.ArgumentParser(
        description="Run CRIS-SME and archive a timestamped assessment snapshot.",
    )
    parser.add_argument(
        "--collector",
        default="mock",
        choices=("mock", "azure"),
        help="Collector mode to execute.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/reports",
        help="Directory for report outputs and archived history.",
    )
    parser.add_argument(
        "--figure-dir",
        default="outputs/figures",
        help="Directory for figure outputs.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["CRIS_SME_COLLECTOR"] = args.collector
    env["CRIS_SME_OUTPUT_DIR"] = args.output_dir
    env["CRIS_SME_FIGURE_DIR"] = args.figure_dir

    subprocess.run(
        [sys.executable, "-m", "cris_sme.main"],
        cwd=repo_root,
        env=env,
        check=True,
    )


if __name__ == "__main__":
    main()
