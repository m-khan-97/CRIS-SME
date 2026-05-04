#!/usr/bin/env python3
"""Verify a CRIS-SME Risk Bill of Materials against report and artifact hashes."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from cris_sme.engine.rbom import verify_risk_bill_of_materials


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify CRIS-SME RBOM report and artifact integrity.",
    )
    parser.add_argument(
        "--report",
        default="outputs/reports/cris_sme_report.json",
        help="Path to the CRIS-SME JSON report.",
    )
    parser.add_argument(
        "--rbom",
        default=None,
        help="Optional path to RBOM JSON. If omitted, the embedded report RBOM is used.",
    )
    parser.add_argument(
        "--base-dir",
        default=".",
        help="Base directory for resolving relative artifact paths.",
    )
    parser.add_argument(
        "--signature",
        default=None,
        help="Optional detached RBOM signature JSON to verify.",
    )
    parser.add_argument(
        "--signing-key",
        default=None,
        help="Signing key value. Prefer --signing-key-env for real use.",
    )
    parser.add_argument(
        "--signing-key-env",
        default="CRIS_SME_RBOM_SIGNING_KEY",
        help="Environment variable containing the signing key.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = verify_risk_bill_of_materials(
        report_path=Path(args.report),
        rbom_path=Path(args.rbom) if args.rbom else None,
        signature_path=Path(args.signature) if args.signature else None,
        signing_key=args.signing_key or os.getenv(args.signing_key_env),
        base_dir=Path(args.base_dir),
    )
    print(json.dumps(result.model_dump(mode="json"), indent=2))
    return 0 if result.verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
