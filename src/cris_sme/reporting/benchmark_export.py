# Benchmark observation export helpers for CRIS-SME longitudinal benchmarking.
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_benchmark_outputs(
    benchmark_observation: dict[str, Any],
    benchmark_comparison: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write benchmark observation and comparison artifacts to disk."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    observation_path = target_dir / "cris_sme_benchmark_observation.json"
    comparison_path = target_dir / "cris_sme_benchmark_comparison.md"

    observation_path.write_text(
        json.dumps(benchmark_observation, indent=2),
        encoding="utf-8",
    )
    comparison_path.write_text(
        build_benchmark_comparison_markdown(benchmark_comparison),
        encoding="utf-8",
    )

    return {
        "benchmark_observation_json": observation_path,
        "benchmark_comparison_markdown": comparison_path,
    }


def build_benchmark_comparison_markdown(benchmark_comparison: dict[str, Any]) -> str:
    """Render the benchmark comparison as concise Markdown."""
    lines = [
        "# CRIS-SME Benchmark Comparison",
        "",
        f"- Dataset size: `{benchmark_comparison.get('dataset_size', 0)}`",
        f"- Peer count: `{benchmark_comparison.get('peer_count', 0)}`",
        f"- Provider: `{benchmark_comparison.get('provider', 'unknown')}`",
        f"- Collector mode: `{benchmark_comparison.get('collector_mode', 'unknown')}`",
        f"- Status: `{benchmark_comparison.get('status', 'unknown')}`",
        "",
    ]
    note = benchmark_comparison.get("note")
    if note:
        lines.extend([str(note), ""])
    if benchmark_comparison.get("status") == "available":
        lines.extend(
            [
                f"- Peer average overall risk: `{float(benchmark_comparison.get('peer_average_overall_risk', 0.0)):.2f}`",
                f"- Percentile worse than peers: `{float(benchmark_comparison.get('percentile_worse_than_peers', 0.0)):.2f}`",
                "",
            ]
        )
    return "\n".join(lines)
