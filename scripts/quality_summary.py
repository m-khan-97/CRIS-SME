"""Render actual GitHub Actions step outcomes, never inferred success."""

from __future__ import annotations

import json
import os
from pathlib import Path


CHECKS = (
    ("checkout", "Checkout"),
    ("python", "Python setup"),
    ("install", "Dependencies"),
    ("lint", "Lint"),
    ("types", "Type check"),
    ("controls", "Control metadata"),
    ("capabilities", "Capability evidence register"),
    ("licenses", "Dependency license inventory"),
    ("tests", "Tests"),
    ("package", "Installed package"),
    ("pipeline", "Mock pipeline"),
    ("outputs", "Core outputs"),
    ("replay", "Deterministic replay"),
    ("docs", "Documentation"),
    ("paper", "Paper package"),
    ("upload", "Artifact upload"),
)


def render_summary(steps: dict, *, run_pipeline: bool, upload_artifacts: bool) -> str:
    optional = set()
    if not run_pipeline:
        optional.update({"pipeline", "outputs", "replay"})
    if not (run_pipeline and upload_artifacts):
        optional.add("upload")
    statuses = []
    rows = []
    for key, label in CHECKS:
        outcome = steps.get(key, {}).get("outcome", "missing")
        if outcome not in {"success", "failure", "cancelled", "skipped"}:
            outcome = "missing"
        if key in optional and outcome == "skipped":
            rows.append(f"| {label} | skipped (disabled by caller) |")
        else:
            statuses.append(outcome)
            rows.append(f"| {label} | {outcome} |")
    if "failure" in statuses:
        overall = "failure"
    elif "cancelled" in statuses:
        overall = "cancelled"
    elif any(status != "success" for status in statuses):
        overall = "incomplete"
    else:
        overall = "success"
    return "\n".join([
        "## CRIS-SME Quality Summary", "",
        f"Checks before summary: **{overall}**", "",
        "| Check | Outcome |", "| --- | --- |", *rows, "",
    ])


def main() -> None:
    summary = render_summary(
        json.loads(os.environ["QUALITY_STEPS"]),
        run_pipeline=os.environ.get("RUN_MOCK_PIPELINE") == "true",
        upload_artifacts=os.environ.get("UPLOAD_GENERATED_ARTIFACTS") == "true",
    )
    with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as stream:
        stream.write(summary)


if __name__ == "__main__":
    main()
