#!/usr/bin/env python3
"""Fail CI if a generated CRIS-SME evidence snapshot does not replay deterministically."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cris_sme.engine.assessment_replay import replay_evidence_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check deterministic replay for a generated CRIS-SME snapshot."
    )
    parser.add_argument(
        "--snapshot",
        required=True,
        type=Path,
        help="Path to cris_sme_evidence_snapshot.json or a report containing evidence_snapshot.",
    )
    args = parser.parse_args()

    snapshot = _load_snapshot(args.snapshot)
    replay = replay_evidence_snapshot(snapshot)
    if not replay.replayable or not replay.deterministic_match:
        print(json.dumps(replay.model_dump(mode="json"), indent=2))
        raise SystemExit(1)

    print(
        json.dumps(
            {
                "snapshot_id": replay.snapshot_id,
                "deterministic_match": replay.deterministic_match,
                "overall_risk_delta": replay.overall_risk_delta,
                "profile_hash_verified": replay.profile_hash_verified,
                "finding_hash_verified": replay.finding_hash_verified,
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
