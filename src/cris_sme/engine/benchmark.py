# Benchmark dataset scaffolding for future UK SME cloud-risk comparison workflows.
from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from pydantic import BaseModel, Field


DEFAULT_BENCHMARK_DATASET_PATH = Path("data/benchmark_dataset.json")


class BenchmarkObservation(BaseModel):
    """A single normalized benchmark observation for a CRIS-SME assessment run."""

    observation_id: str = Field(..., min_length=3)
    generated_at: str = Field(..., min_length=8)
    organization_label: str = Field(..., min_length=3)
    provider: str = Field(..., min_length=2)
    sector: str = Field(..., min_length=2)
    collector_mode: str = Field(..., min_length=2)
    sample_source: str = Field(..., min_length=3)
    organization_count: int = Field(..., ge=1)
    overall_risk_score: float = Field(..., ge=0.0, le=100.0)
    category_scores: dict[str, float] = Field(default_factory=dict)


def load_benchmark_dataset(
    path: str | Path = DEFAULT_BENCHMARK_DATASET_PATH,
) -> list[BenchmarkObservation]:
    """Load the current benchmark dataset scaffold."""
    raw_items = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw_items, list):
        raise ValueError("Benchmark dataset must be a list of observations.")
    return [BenchmarkObservation.model_validate(item) for item in raw_items]


def build_benchmark_observation(report: dict[str, Any]) -> BenchmarkObservation:
    """Convert the current CRIS-SME report into a normalized benchmark observation."""
    organizations = report.get("organizations", [])
    if not isinstance(organizations, list):
        organizations = []

    providers = {
        str(item.get("provider", "")).strip().lower()
        for item in organizations
        if isinstance(item, dict)
    }
    sectors = {
        str(item.get("sector", "")).strip()
        for item in organizations
        if isinstance(item, dict)
    }
    sources = {
        str(item.get("collection_details", {}).get("profile_source", "")).strip()
        for item in organizations
        if isinstance(item, dict) and isinstance(item.get("collection_details"), dict)
    }
    provider = next(iter(providers)) if len(providers) == 1 else "mixed"
    sector = next(iter(sectors)) if len(sectors) == 1 else "mixed"
    sample_source = next(iter(sources)) if len(sources) == 1 else "mixed"
    label = (
        organizations[0].get("organization_name")
        if len(organizations) == 1 and isinstance(organizations[0], dict)
        else "Assessment cohort"
    )

    return BenchmarkObservation(
        observation_id=(
            f"{report.get('collector_mode', 'report')}-"
            f"{report.get('generated_at', '1970-01-01T00:00:00Z')}"
        ),
        generated_at=str(report.get("generated_at", "1970-01-01T00:00:00Z")),
        organization_label=str(label),
        provider=str(provider or "unknown"),
        sector=str(sector or "unknown"),
        collector_mode=str(report.get("collector_mode", "unknown")),
        sample_source=str(sample_source or "unknown"),
        organization_count=max(len(organizations), 1),
        overall_risk_score=float(report.get("overall_risk_score", 0.0)),
        category_scores={
            str(category): float(score)
            for category, score in (report.get("category_scores", {}) or {}).items()
        },
    )


def build_benchmark_comparison(
    report: dict[str, Any],
    dataset: list[BenchmarkObservation],
) -> dict[str, Any]:
    """Compare the current report against the benchmark scaffold when peers exist."""
    observation = build_benchmark_observation(report)
    peers = [
        item
        for item in dataset
        if item.provider == observation.provider
        and item.collector_mode == observation.collector_mode
        and item.observation_id != observation.observation_id
    ]

    comparison: dict[str, Any] = {
        "dataset_size": len(dataset),
        "peer_count": len(peers),
        "provider": observation.provider,
        "collector_mode": observation.collector_mode,
        "sector": observation.sector,
        "observation": observation.model_dump(),
    }

    if len(peers) < 3:
        comparison["status"] = "insufficient_dataset"
        comparison["note"] = (
            "Benchmark comparison is scaffolded, but fewer than three comparable peer observations "
            "are currently available for a meaningful percentile ranking."
        )
        return comparison

    peer_scores = [item.overall_risk_score for item in peers]
    percentile_worse_than = round(
        (
            sum(1 for score in peer_scores if observation.overall_risk_score > score)
            / len(peer_scores)
        )
        * 100.0,
        2,
    )
    comparison.update(
        {
            "status": "available",
            "peer_average_overall_risk": round(mean(peer_scores), 2),
            "peer_min_overall_risk": round(min(peer_scores), 2),
            "peer_max_overall_risk": round(max(peer_scores), 2),
            "percentile_worse_than_peers": percentile_worse_than,
        }
    )
    return comparison
