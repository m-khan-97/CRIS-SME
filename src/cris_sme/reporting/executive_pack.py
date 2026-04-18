# Board-ready executive pack generation for CRIS-SME.
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_executive_pack(report: dict[str, Any]) -> dict[str, Any]:
    """Build a board-ready executive pack from the current CRIS-SME report."""
    prioritized_risks = report.get("prioritized_risks", [])
    if not isinstance(prioritized_risks, list):
        prioritized_risks = []

    top_risks = [
        {
            "control_id": risk.get("control_id"),
            "title": risk.get("title"),
            "priority": risk.get("priority"),
            "score": risk.get("score"),
            "organization": risk.get("organization"),
            "remediation_summary": risk.get("remediation_summary"),
        }
        for risk in prioritized_risks[:5]
        if isinstance(risk, dict)
    ]

    remediation = report.get("budget_aware_remediation", {})
    free_profile = {}
    if isinstance(remediation, dict):
        for profile in remediation.get("budget_profiles", []):
            if isinstance(profile, dict) and profile.get("profile_id") == "free_this_week":
                free_profile = profile
                break

    action_plan = report.get("action_plan_30_day", {})
    cyber_essentials = report.get("cyber_essentials_readiness", {})
    insurance = report.get("cyber_insurance_evidence", {})
    benchmark = report.get("benchmark_comparison", {})

    return {
        "pack_name": "CRIS-SME Executive Pack",
        "generated_at": report.get("generated_at"),
        "overall_risk_score": report.get("overall_risk_score"),
        "summary": report.get("summary"),
        "board_message": (
            "CRIS-SME highlights the highest-risk cloud governance issues, the most practical fixes "
            "for the next 30 days, and the organisation's current UK-readiness signals."
        ),
        "top_risks": top_risks,
        "quick_wins": {
            "free_fix_count": free_profile.get("total_recommended", 0),
            "free_fix_risk_total": free_profile.get("cumulative_risk_score", 0.0),
        },
        "cyber_essentials_readiness": cyber_essentials,
        "insurance_readiness": (
            insurance.get("readiness_summary", {}) if isinstance(insurance, dict) else {}
        ),
        "benchmark_status": (
            benchmark.get("status", "unknown") if isinstance(benchmark, dict) else "unknown"
        ),
        "benchmark_note": (
            benchmark.get("note", "") if isinstance(benchmark, dict) else ""
        ),
        "action_plan_summary": (
            action_plan.get("phases", []) if isinstance(action_plan, dict) else []
        ),
    }


def write_executive_pack(
    executive_pack: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write board-ready executive pack artifacts to disk."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = target_dir / "cris_sme_executive_pack.md"
    json_path = target_dir / "cris_sme_executive_pack.json"

    markdown_path.write_text(build_executive_pack_markdown(executive_pack), encoding="utf-8")
    json_path.write_text(json.dumps(executive_pack, indent=2), encoding="utf-8")

    return {
        "executive_pack_markdown": markdown_path,
        "executive_pack_json": json_path,
    }


def build_executive_pack_markdown(executive_pack: dict[str, Any]) -> str:
    """Render the board-ready executive pack as concise Markdown."""
    lines = [
        "# CRIS-SME Executive Pack",
        "",
        f"- Generated at: `{executive_pack.get('generated_at', 'unknown')}`",
        f"- Overall risk score: `{float(executive_pack.get('overall_risk_score', 0.0)):.2f}`",
        f"- Summary: {executive_pack.get('summary', '')}",
        "",
        "## Board Message",
        "",
        str(executive_pack.get("board_message", "")),
        "",
    ]

    quick_wins = executive_pack.get("quick_wins", {})
    if isinstance(quick_wins, dict):
        lines.extend(
            [
                "## Quick Wins",
                "",
                f"- Free fixes available this week: `{int(quick_wins.get('free_fix_count', 0))}`",
                f"- Cumulative risk covered by free fixes: `{float(quick_wins.get('free_fix_risk_total', 0.0)):.2f}`",
                "",
            ]
        )

    readiness = executive_pack.get("cyber_essentials_readiness", {})
    if isinstance(readiness, dict):
        lines.extend(
            [
                "## Cyber Essentials Readiness",
                "",
                f"- Overall readiness score: `{float(readiness.get('overall_readiness_score', 0.0)):.2f}`",
                "",
            ]
        )
        for pillar in readiness.get("pillars", []):
            if not isinstance(pillar, dict):
                continue
            lines.append(
                f"- {pillar.get('pillar_name', '')}: {pillar.get('status', '')} "
                f"({float(pillar.get('readiness_score', 0.0)):.2f})"
            )
        lines.append("")

    top_risks = executive_pack.get("top_risks", [])
    if isinstance(top_risks, list) and top_risks:
        lines.extend(
            [
                "## Top Risks",
                "",
                "| Control | Priority | Score | Action |",
                "| --- | --- | ---: | --- |",
            ]
        )
        for risk in top_risks:
            if not isinstance(risk, dict):
                continue
            lines.append(
                "| "
                f"{risk.get('control_id', '')} | "
                f"{risk.get('priority', '')} | "
                f"{float(risk.get('score', 0.0)):.2f} | "
                f"{risk.get('remediation_summary', '')} |"
            )
        lines.append("")

    return "\n".join(lines)
