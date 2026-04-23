#!/usr/bin/env python3
"""Build the full CRIS-SME static site bundle for CI and Vercel deployments."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a deterministic CRIS-SME assessment and assemble a deployable static "
            "site bundle at dist/site."
        ),
    )
    parser.add_argument(
        "--collector",
        default="mock",
        choices=("mock", "azure"),
        help="Collector mode for the assessment step (default: mock).",
    )
    parser.add_argument(
        "--reports-dir",
        default="outputs/reports",
        help="Directory where report artifacts are generated.",
    )
    parser.add_argument(
        "--figures-dir",
        default="outputs/figures",
        help="Directory where figure artifacts are generated.",
    )
    parser.add_argument(
        "--dist-dir",
        default="dist",
        help="Directory where the deployable static site bundle is assembled.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Keep subprocess stdout logs visible.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src")

    run_stdout = None if args.verbose else subprocess.DEVNULL

    subprocess.run(
        [
            sys.executable,
            "scripts/run_assessment_snapshot.py",
            "--collector",
            args.collector,
            "--output-dir",
            args.reports_dir,
            "--figure-dir",
            args.figures_dir,
        ],
        cwd=repo_root,
        env=env,
        stdout=run_stdout,
        check=True,
    )

    subprocess.run(
        [
            sys.executable,
            "scripts/build_pages_site.py",
            "--reports-dir",
            args.reports_dir,
            "--figures-dir",
            args.figures_dir,
            "--dist-dir",
            args.dist_dir,
        ],
        cwd=repo_root,
        env=env,
        stdout=run_stdout,
        check=True,
    )


if __name__ == "__main__":
    main()
