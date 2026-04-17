# 30-day action-plan export helpers for SME-oriented CRIS-SME outputs.
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_action_plan_outputs(
    action_plan: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write the 30-day action plan to Markdown and JSON artifacts."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = target_dir / "cris_sme_30_day_action_plan.md"
    json_path = target_dir / "cris_sme_30_day_action_plan.json"

    markdown_path.write_text(build_action_plan_markdown(action_plan), encoding="utf-8")
    json_path.write_text(json.dumps(action_plan, indent=2), encoding="utf-8")

    return {
        "action_plan_markdown": markdown_path,
        "action_plan_json": json_path,
    }


def build_action_plan_markdown(action_plan: dict[str, Any]) -> str:
    """Render the 30-day action plan as concise Markdown."""
    lines = [
        "# CRIS-SME 30-Day SME Action Plan",
        "",
        f"- Planning basis: {action_plan.get('planning_basis', '')}",
        "",
    ]

    phases = action_plan.get("phases", [])
    if not isinstance(phases, list):
        phases = []

    for phase in phases:
        if not isinstance(phase, dict):
            continue
        lines.extend(
            [
                f"## {phase.get('label', 'Plan phase')}",
                "",
                f"- Time window: `{phase.get('time_window', '')}`",
                f"- Goal: {phase.get('goal', '')}",
                f"- Total actions: `{phase.get('total_actions', 0)}`",
                f"- Cumulative risk score: `{float(phase.get('cumulative_risk_score', 0.0)):.2f}`",
                "",
            ]
        )
        actions = phase.get("actions", [])
        if not isinstance(actions, list) or not actions:
            lines.extend(["No actions are scheduled in this phase.", ""])
            continue
        lines.extend(
            [
                "| Control | Priority | Score | Cost Tier | Action |",
                "| --- | --- | ---: | --- | --- |",
            ]
        )
        for action in actions:
            if not isinstance(action, dict):
                continue
            lines.append(
                "| "
                f"{action.get('control_id', '')} | "
                f"{action.get('priority', '')} | "
                f"{float(action.get('score', 0.0)):.2f} | "
                f"{action.get('remediation_cost_tier', '')} | "
                f"{action.get('remediation_summary', '')} |"
            )
        lines.append("")

    return "\n".join(lines)
