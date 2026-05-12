#!/usr/bin/env python3
"""Verify a signed or hash-bound CE human-review ledger."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from cris_sme.engine.ce_review_signature import verify_ce_review_ledger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify CE human-review ledger integrity metadata and signature.",
    )
    parser.add_argument(
        "--ledger",
        required=True,
        help="Path to a signed/hash-bound CE human-review ledger JSON.",
    )
    parser.add_argument(
        "--answer-pack",
        default=None,
        help="Optional source answer-pack JSON to verify source binding.",
    )
    parser.add_argument(
        "--signing-key",
        default=None,
        help="Signing key value. Prefer --signing-key-env for real use.",
    )
    parser.add_argument(
        "--signing-key-env",
        default="CRIS_SME_CE_REVIEW_SIGNING_KEY",
        help="Environment variable containing the signing key.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    answer_pack = None
    if args.answer_pack:
        answer_pack = json.loads(Path(args.answer_pack).read_text(encoding="utf-8"))
    signing_key = args.signing_key or os.getenv(args.signing_key_env)
    result = verify_ce_review_ledger(
        Path(args.ledger),
        answer_pack=answer_pack,
        signing_key=signing_key,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
