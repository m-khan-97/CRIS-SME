#!/usr/bin/env python3
"""Create a detached HMAC-SHA256 signature for a CRIS-SME RBOM."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from cris_sme.engine.rbom import (
    sign_risk_bill_of_materials,
    write_risk_bill_of_materials_signature,
)
from cris_sme.models.platform import RiskBillOfMaterials


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sign a CRIS-SME RBOM with a detached HMAC-SHA256 signature.",
    )
    parser.add_argument(
        "--rbom",
        default="outputs/reports/cris_sme_risk_bill_of_materials.json",
        help="Path to the RBOM JSON file.",
    )
    parser.add_argument(
        "--output",
        default="outputs/reports/cris_sme_risk_bill_of_materials.signature.json",
        help="Path where the detached signature JSON should be written.",
    )
    parser.add_argument(
        "--key-id",
        default="local",
        help="Human-readable signing key identifier recorded in the signature.",
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
    signing_key = args.signing_key or os.getenv(args.signing_key_env)
    if not signing_key:
        raise SystemExit(
            f"Missing signing key. Set {args.signing_key_env} or pass --signing-key."
        )

    rbom_path = Path(args.rbom)
    rbom = RiskBillOfMaterials.model_validate_json(
        rbom_path.read_text(encoding="utf-8")
    )
    signature = sign_risk_bill_of_materials(
        rbom,
        signing_key=signing_key,
        key_id=args.key_id,
    )
    output_path = write_risk_bill_of_materials_signature(
        signature,
        Path(args.output),
    )
    print(json.dumps({"signature": str(output_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
