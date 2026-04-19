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
    parser.add_argument(
        "--dataset-source-type",
        default=None,
        help="Optional dataset source type override, e.g. live_real, sandbox, or vulnerable_lab.",
    )
    parser.add_argument(
        "--authorization-basis",
        default=None,
        help="Optional authorization basis override for research dataset tracking.",
    )
    parser.add_argument(
        "--dataset-use",
        default=None,
        help="Optional dataset-use override, e.g. live_case_study or control_stress_test.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")
    env["CRIS_SME_COLLECTOR"] = args.collector
    env["CRIS_SME_OUTPUT_DIR"] = args.output_dir
    env["CRIS_SME_FIGURE_DIR"] = args.figure_dir
    if args.dataset_source_type:
        env["CRIS_SME_DATASET_SOURCE_TYPE"] = args.dataset_source_type
    if args.authorization_basis:
        env["CRIS_SME_AUTHORIZATION_BASIS"] = args.authorization_basis
    if args.dataset_use:
        env["CRIS_SME_DATASET_USE"] = args.dataset_use

    subprocess.run(
        [sys.executable, "-m", "cris_sme.main"],
        cwd=repo_root,
        env=env,
        check=True,
    )


if __name__ == "__main__":
    main()
