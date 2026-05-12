#!/usr/bin/env python3
"""Create a hash-bound and optionally signed CE human-review ledger."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from cris_sme.engine.ce_review_import import load_ce_review_decisions
from cris_sme.engine.ce_review_signature import (
    build_signed_ce_review_ledger,
    write_signed_ce_review_ledger,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Bind a completed Cyber Essentials human-review ledger to its source "
            "answer pack with deterministic hashes and an optional HMAC signature."
        )
    )
    parser.add_argument(
        "--answer-pack",
        default="outputs/reports/cris_sme_ce_self_assessment.json",
        help="Path to cris_sme_ce_self_assessment.json.",
    )
    parser.add_argument(
        "--ledger",
        required=True,
        help="Path to a completed CSV or JSON human-review ledger.",
    )
    parser.add_argument(
        "--output",
        default="outputs/reports/cris_sme_ce_human_review_ledger.signed.json",
        help="Path for the signed/hash-bound ledger JSON.",
    )
    parser.add_argument("--reviewer-name", default="", help="Reviewer display name.")
    parser.add_argument("--reviewer-role", default="", help="Reviewer role.")
    parser.add_argument(
        "--reviewer-organisation",
        default="",
        help="Reviewer organisation.",
    )
    parser.add_argument("--reviewer-id", default="", help="Stable reviewer identifier.")
    parser.add_argument(
        "--generated-at",
        default=None,
        help="Optional ISO timestamp for reproducible test fixtures.",
    )
    parser.add_argument(
        "--key-id",
        default="local",
        help="Human-readable signing key identifier.",
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
    answer_pack = json.loads(Path(args.answer_pack).read_text(encoding="utf-8"))
    decisions = load_ce_review_decisions(args.ledger, answer_pack=answer_pack)
    signing_key = args.signing_key or os.getenv(args.signing_key_env)
    ledger = build_signed_ce_review_ledger(
        answer_pack=answer_pack,
        review_decisions=decisions,
        reviewer={
            "name": args.reviewer_name,
            "role": args.reviewer_role,
            "organisation": args.reviewer_organisation,
            "reviewer_id": args.reviewer_id,
        },
        generated_at=args.generated_at,
        signing_key=signing_key,
        key_id=args.key_id,
    )
    output_path = write_signed_ce_review_ledger(ledger, args.output)
    print(
        json.dumps(
            {
                "ledger": str(output_path),
                "canonical_ledger_sha256": ledger["integrity"]["canonical_ledger_sha256"],
                "canonical_decisions_sha256": ledger["integrity"]["canonical_decisions_sha256"],
                "source_answer_pack_sha256": ledger["integrity"]["source_answer_pack_sha256"],
                "signature": bool(ledger.get("signature")),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
