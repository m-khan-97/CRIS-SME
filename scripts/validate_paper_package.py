#!/usr/bin/env python3
"""Validate the Cyber Essentials paper package for stale or unsafe claims."""
from __future__ import annotations

import argparse
import csv
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


DEFAULT_ROOT = Path("paper/cyber-essentials")

FORBIDDEN_PHRASES = {
    "provisional agreement rate",
    "pending external human cross-check",
    "external human cross-check is pending",
    "AI-assisted draft acceptance as human agreement",
}

REQUIRED_FILES = [
    "main.md",
    "README.md",
    "submission-plan.md",
    "references.bib",
    "related-work-competitor-check.md",
    "review-ledger-current-final.csv",
    "tables/results-summary.md",
    "tables/results-summary.csv",
    "figures/ce-evidence-class-distribution.svg",
    "figures/ce-proposed-answer-distribution.svg",
    "figures/azure-category-score-comparison.svg",
    "figures/ce-workflow.svg",
]

EXPECTED_REVIEW_METRICS = {
    "reviewer_ledger_entries_received": "28",
    "final_accepted_rows": "23",
    "needs_evidence": "5",
    "pending": "78",
    "final_human_agreement_evaluable": "23",
    "external_human_cross_check": "Complete",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=str(DEFAULT_ROOT),
        help="Paper package directory to validate.",
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    errors: list[str] = []
    errors.extend(_validate_required_files(root))
    errors.extend(_validate_svg_figures(root))
    errors.extend(_validate_csv_files(root))
    errors.extend(_validate_claim_language(root))
    errors.extend(_validate_review_metrics(root))
    errors.extend(_validate_markdown_links(root))

    if errors:
        print("Paper package validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"Paper package validation passed: {root}")
    return 0


def _validate_required_files(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED_FILES:
        path = root / relative
        if not path.is_file():
            errors.append(f"missing required paper artifact: {path}")
    return errors


def _validate_svg_figures(root: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted((root / "figures").glob("*.svg")):
        try:
            element = ET.parse(path).getroot()
        except ET.ParseError as exc:
            errors.append(f"malformed SVG XML in {path}: {exc}")
            continue
        if not element.tag.endswith("svg"):
            errors.append(f"SVG root is not <svg> in {path}")
    return errors


def _validate_csv_files(root: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(root.rglob("*.csv")):
        try:
            with path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.reader(handle))
        except csv.Error as exc:
            errors.append(f"CSV parse failed for {path}: {exc}")
            continue
        if not rows:
            errors.append(f"CSV file is empty: {path}")
    return errors


def _validate_claim_language(root: Path) -> list[str]:
    errors: list[str] = []
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8").lower()
        for phrase in FORBIDDEN_PHRASES:
            if phrase.lower() in text:
                errors.append(f"forbidden stale/unsafe phrase in {path}: {phrase}")

    main_text = (root / "main.md").read_text(encoding="utf-8")
    required_claims = [
        "23 of 23 agreement over agreement-evaluable rows",
        "not a Cyber Essentials certification claim",
        "direct cloud, inferred cloud, endpoint required, policy required, manual required, or not observable",
    ]
    for claim in required_claims:
        if claim not in main_text:
            errors.append(f"main.md is missing required claim discipline text: {claim}")
    return errors


def _validate_review_metrics(root: Path) -> list[str]:
    path = root / "tables/results-summary.csv"
    errors: list[str] = []
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    metrics: dict[str, str] = {}
    for row in rows:
        if row.get("table") == "review_metric":
            metrics[row.get("metric", "")] = (
                row.get("count") or row.get("rate") or row.get("score") or row.get("notes") or ""
            )

    for metric, expected in EXPECTED_REVIEW_METRICS.items():
        actual = metrics.get(metric)
        if actual != expected:
            errors.append(
                f"review metric {metric!r} expected {expected!r}, found {actual!r}"
            )

    if metrics.get("ai_draft_accepted") == metrics.get("final_human_agreement_evaluable"):
        notes = {
            row.get("metric"): row.get("notes", "")
            for row in rows
            if row.get("table") == "review_metric"
        }
        if "Not independent human agreement" not in notes.get("ai_draft_accepted", ""):
            errors.append("AI draft acceptance is not clearly separated from human agreement")
    return errors


def _validate_markdown_links(root: Path) -> list[str]:
    errors: list[str] = []
    pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            target = match.group(1).strip()
            if _is_external_or_anchor(target):
                continue
            if target.startswith("/"):
                errors.append(f"absolute local markdown link in {path}: {target}")
                continue
            clean_target = target.split("#", 1)[0]
            if not clean_target:
                continue
            resolved = (path.parent / clean_target).resolve()
            try:
                resolved.relative_to(root.resolve())
            except ValueError:
                errors.append(f"markdown link points outside paper package in {path}: {target}")
                continue
            if not resolved.exists():
                errors.append(f"broken local markdown link in {path}: {target}")
    return errors


def _is_external_or_anchor(target: str) -> bool:
    return (
        target.startswith("#")
        or target.startswith("http://")
        or target.startswith("https://")
        or target.startswith("mailto:")
    )


if __name__ == "__main__":
    raise SystemExit(main())
