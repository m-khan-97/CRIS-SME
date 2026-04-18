# Native recommendation comparison for grounding CRIS-SME against Azure-native signals.
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from cris_sme.engine.scoring import ScoredFinding
from cris_sme.models.cloud_profile import CloudProfile


DEFAULT_NATIVE_RECOMMENDATION_MAPPING_PATH = Path("data/native_recommendation_mapping.json")


class NativeRecommendationMappingEntry(BaseModel):
    """Mapping between a CRIS-SME control and a native recommendation pattern."""

    control_id: str = Field(..., min_length=3)
    framework: str = Field(..., min_length=3)
    keyword_rules: list[str] = Field(default_factory=list)
    notes: str = Field(..., min_length=8)


@lru_cache(maxsize=1)
def load_native_recommendation_mappings(
    path: str | Path = DEFAULT_NATIVE_RECOMMENDATION_MAPPING_PATH,
) -> dict[str, NativeRecommendationMappingEntry]:
    """Load the native recommendation mapping catalog."""
    raw_entries = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = [
        NativeRecommendationMappingEntry.model_validate(item)
        for item in raw_entries
    ]
    return {entry.control_id: entry for entry in entries}


def build_native_validation_summary(
    profiles: list[CloudProfile],
    prioritized_findings: list[ScoredFinding],
) -> dict[str, Any]:
    """Compare active CRIS-SME findings with visible unhealthy native recommendations."""
    mappings = load_native_recommendation_mappings()
    active_controls = {item.finding.control_id: item for item in prioritized_findings}
    native_recommendations = _collect_unhealthy_native_recommendations(profiles)

    agreement_count = 0
    cris_only_count = 0
    native_only_count = 0
    control_comparisons: list[dict[str, Any]] = []

    for control_id, mapping in mappings.items():
        matched_native = [
            recommendation
            for recommendation in native_recommendations
            if _recommendation_matches_mapping(recommendation, mapping)
        ]
        cris_item = active_controls.get(control_id)
        cris_active = cris_item is not None
        native_active = bool(matched_native)

        if cris_active and native_active:
            comparison_status = "agreement"
            agreement_count += 1
        elif cris_active:
            comparison_status = "cris_only"
            cris_only_count += 1
        elif native_active:
            comparison_status = "native_only"
            native_only_count += 1
        else:
            comparison_status = "clear"

        control_comparisons.append(
            {
                "control_id": control_id,
                "framework": mapping.framework,
                "comparison_status": comparison_status,
                "cris_active": cris_active,
                "native_active": native_active,
                "cris_score": cris_item.score if cris_item is not None else None,
                "native_recommendation_count": len(matched_native),
                "native_recommendations": matched_native[:5],
                "notes": mapping.notes,
            }
        )

    return {
        "framework": "Microsoft Defender for Cloud",
        "controls_mapped": len(mappings),
        "native_unhealthy_recommendation_count": len(native_recommendations),
        "agreement_count": agreement_count,
        "cris_only_count": cris_only_count,
        "native_only_count": native_only_count,
        "coverage_note": (
            "Comparison is based on currently visible unhealthy Defender for Cloud assessments "
            "and mapped CRIS-SME controls. It supports calibration and divergence analysis, "
            "but it is not a claim that either system fully subsumes the other."
        ),
        "control_comparisons": control_comparisons,
    }


def _collect_unhealthy_native_recommendations(
    profiles: list[CloudProfile],
) -> list[dict[str, Any]]:
    """Collect compact unhealthy recommendation records from profile metadata."""
    recommendations: list[dict[str, Any]] = []
    for profile in profiles:
        raw_items = profile.metadata.get("native_security_recommendations", [])
        if not isinstance(raw_items, list):
            continue
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            if str(item.get("status_code", "")).lower() == "unhealthy":
                recommendations.append(item)
    return recommendations


def _recommendation_matches_mapping(
    recommendation: dict[str, Any],
    mapping: NativeRecommendationMappingEntry,
) -> bool:
    """Return whether a compact native recommendation matches a mapped control."""
    display_name = str(recommendation.get("display_name", "")).strip().lower()
    if not display_name:
        return False
    return any(rule.lower() in display_name for rule in mapping.keyword_rules)
