#!/usr/bin/env python3
"""Replay a CRIS-SME evidence snapshot without recollecting cloud evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cris_sme.engine.assessment_replay import (
    build_evidence_diff_result,
    replay_evidence_snapshot,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replay and compare CRIS-SME normalized evidence snapshots."
    )
    parser.add_argument(
        "--snapshot",
        required=True,
        type=Path,
        help="Path to cris_sme_evidence_snapshot.json or a report containing evidence_snapshot.",
    )
    parser.add_argument(
        "--previous-snapshot",
        type=Path,
        default=None,
        help="Optional previous snapshot or report for evidence diff classification.",
    )
    args = parser.parse_args()

    current_snapshot = _load_snapshot(args.snapshot)
    previous_snapshot = (
        _load_snapshot(args.previous_snapshot)
        if args.previous_snapshot is not None
        else None
    )
    replay = replay_evidence_snapshot(current_snapshot)
    diff = build_evidence_diff_result(current_snapshot, previous_snapshot)
    print(
        json.dumps(
            {
                "replay": replay.model_dump(mode="json"),
                "evidence_diff": diff.model_dump(mode="json"),
            },
            indent=2,
        )
    )


def _load_snapshot(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("evidence_snapshot"), dict):
        return payload["evidence_snapshot"]
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return payload


if __name__ == "__main__":
    main()
