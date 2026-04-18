# UK-focused readiness profiles for CRIS-SME reporting and executive communication.
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from cris_sme.models.finding import Finding


DEFAULT_CYBER_ESSENTIALS_CONTROLS_PATH = Path("data/cyber_essentials_controls.json")


class ReadinessPillar(BaseModel):
    """Readiness status for a single Cyber Essentials pillar."""

    pillar_id: str = Field(..., min_length=3)
    pillar_name: str = Field(..., min_length=3)
    total_controls: int = Field(..., ge=0)
    controls_met: int = Field(..., ge=0)
    controls_not_met: int = Field(..., ge=0)
    readiness_score: float = Field(..., ge=0.0, le=100.0)
    status: str = Field(..., min_length=3)
    active_control_ids: list[str] = Field(default_factory=list)


def build_cyber_essentials_readiness(findings: list[Finding]) -> dict[str, Any]:
    """Build a Cyber Essentials readiness summary from the current CRIS-SME findings."""
    raw_pillars = json.loads(
        DEFAULT_CYBER_ESSENTIALS_CONTROLS_PATH.read_text(encoding="utf-8")
    )
    active_control_ids = {
        finding.control_id
        for finding in findings
        if not finding.is_compliant
    }

    pillars: list[ReadinessPillar] = []
    for item in raw_pillars:
        pillar_control_ids = [str(control_id) for control_id in item.get("control_ids", [])]
        not_met = [control_id for control_id in pillar_control_ids if control_id in active_control_ids]
        total_controls = len(pillar_control_ids)
        controls_not_met = len(not_met)
        controls_met = max(total_controls - controls_not_met, 0)
        readiness_score = round((controls_met / total_controls) * 100.0, 2) if total_controls else 0.0
        status = "ready" if controls_not_met == 0 else ("partial" if controls_met > 0 else "gap")

        pillars.append(
            ReadinessPillar(
                pillar_id=str(item.get("pillar_id", "pillar")),
                pillar_name=str(item.get("pillar_name", "Pillar")),
                total_controls=total_controls,
                controls_met=controls_met,
                controls_not_met=controls_not_met,
                readiness_score=readiness_score,
                status=status,
                active_control_ids=not_met,
            )
        )

    overall_score = round(
        sum(pillar.readiness_score for pillar in pillars) / max(len(pillars), 1),
        2,
    )
    return {
        "profile_name": "Cyber Essentials readiness profile",
        "overall_readiness_score": overall_score,
        "pillar_count": len(pillars),
        "pillars": [pillar.model_dump() for pillar in pillars],
    }
