#!/usr/bin/env python3
"""Run a custom deterministic remediation simulation from a CRIS-SME JSON report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cris_sme.engine.remediation_simulator import (
    RemediationSimulationRequest,
    build_custom_report_remediation_simulation,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate custom CRIS-SME remediation selections from an existing report.",
    )
    parser.add_argument(
        "--report",
        default="outputs/reports/cris_sme_report.json",
        help="Path to CRIS-SME JSON report.",
    )
    parser.add_argument(
        "--scenario-id",
        default="custom",
        help="Scenario identifier for the custom simulation.",
    )
    parser.add_argument(
        "--label",
        default="Custom remediation scenario",
        help="Human-readable scenario label.",
    )
    parser.add_argument(
        "--finding-id",
        action="append",
        default=[],
        help="Finding ID to simulate as fixed. Can be repeated.",
    )
    parser.add_argument(
        "--control-id",
        action="append",
        default=[],
        help="Control ID to simulate as fixed. Can be repeated.",
    )
    parser.add_argument(
        "--category",
        action="append",
        default=[],
        help="Finding category to simulate as fixed. Can be repeated.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    request = RemediationSimulationRequest(
        scenario_id=args.scenario_id,
        label=args.label,
        finding_ids=args.finding_id,
        control_ids=args.control_id,
        categories=args.category,
    )
    scenario = build_custom_report_remediation_simulation(report, request)
    print(json.dumps(scenario, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
