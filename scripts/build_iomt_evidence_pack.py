#!/usr/bin/env python3
"""Build a focused CRIS-IoMT evidence pack from a CRIS report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cris_sme.reporting.iomt_evidence_pack import (
    build_iomt_evidence_pack,
    write_iomt_evidence_pack,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build CRIS-IoMT JSON and Markdown evidence-pack artifacts.",
    )
    parser.add_argument(
        "--report",
        required=True,
        help="Path to a CRIS report JSON file.",
    )
    parser.add_argument(
        "--manifest",
        help="Optional Azure evidence-lab manifest JSON file.",
    )
    parser.add_argument(
        "--output-dir",
        help="Directory for generated pack artifacts. Defaults to the report directory.",
    )
    args = parser.parse_args()

    report_path = Path(args.report)
    report = _load_json(report_path)
    manifest = _load_json(Path(args.manifest)) if args.manifest else None
    output_dir = Path(args.output_dir) if args.output_dir else report_path.parent

    pack = build_iomt_evidence_pack(report, lab_manifest=manifest)
    written = write_iomt_evidence_pack(pack, output_dir)
    for label, path in written.items():
        print(f"{label}: {path}")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


if __name__ == "__main__":
    main()
