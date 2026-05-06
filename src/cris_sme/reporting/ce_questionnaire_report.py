# HTML rendering for Cyber Essentials self-assessment pre-population packs.
from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any


def build_ce_self_assessment_html(pack: dict[str, Any]) -> str:
    """Build a static CE self-assessment pre-population report."""
    summary = pack.get("coverage_summary", {})
    if not isinstance(summary, dict):
        summary = {}
    question_set = pack.get("question_set", {})
    if not isinstance(question_set, dict):
        question_set = {}
    answers = [
        answer for answer in pack.get("answers", []) if isinstance(answer, dict)
    ]
    sections = _group_by_section(answers)
    section_tabs = "".join(
        f'<a href="#{escape(section)}">{escape(section.replace("_", " ").title())}</a>'
        for section in sections
    )
    section_html = "".join(
        _section_html(section, section_answers)
        for section, section_answers in sections.items()
    )

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>CRIS-SME Cyber Essentials Pre-Assessment Pack</title>
    <style>
      :root {{
        --bg: #f7f9fb;
        --ink: #172033;
        --muted: #617083;
        --panel: #ffffff;
        --line: #d8e2ec;
        --accent: #0f766e;
        --warn: #a16207;
        --risk: #b42318;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background: var(--bg);
        color: var(--ink);
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      }}
      main {{ max-width: 1220px; margin: 0 auto; padding: 28px 18px 56px; }}
      header {{ border-bottom: 1px solid var(--line); padding-bottom: 18px; margin-bottom: 18px; }}
      h1 {{ margin: 0; font-size: clamp(1.7rem, 4vw, 2.5rem); }}
      h2 {{ margin: 0 0 12px; font-size: 1.25rem; }}
      h3 {{ margin: 0 0 6px; font-size: 1rem; }}
      p {{ line-height: 1.55; overflow-wrap: anywhere; }}
      .muted {{ color: var(--muted); }}
      .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 190px), 1fr)); gap: 12px; }}
      .panel {{
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 14px;
        overflow: hidden;
      }}
      .metric {{ font-size: 1.55rem; font-weight: 800; margin: 2px 0; overflow-wrap: anywhere; }}
      .tabs {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }}
      .tabs a {{
        background: #ccfbf1;
        color: #042f2e;
        border: 1px solid #99f6e4;
        border-radius: 999px;
        padding: 7px 11px;
        text-decoration: none;
        font-weight: 700;
      }}
      .answer {{
        border: 1px solid var(--line);
        border-radius: 8px;
        background: #fbfdff;
        padding: 12px;
        margin-bottom: 10px;
      }}
      .meta {{ display: flex; flex-wrap: wrap; gap: 7px; margin: 8px 0; }}
      .pill {{
        display: inline-flex;
        border-radius: 999px;
        padding: 4px 8px;
        font-size: 0.78rem;
        font-weight: 800;
        background: #e2e8f0;
        color: #263548;
      }}
      .status-supported_risk_found {{ background: #fee2e2; color: var(--risk); }}
      .status-supported_no_issue {{ background: #dcfce7; color: #166534; }}
      .status-endpoint_required,
      .status-policy_required,
      .status-manual_required,
      .status-insufficient_evidence {{ background: #fef3c7; color: var(--warn); }}
      ul {{ margin: 8px 0 0; padding-left: 18px; }}
      li {{ margin-bottom: 5px; overflow-wrap: anywhere; }}
      footer {{ color: var(--muted); margin-top: 20px; font-size: 0.9rem; }}
    </style>
  </head>
  <body>
    <main>
      <header>
        <h1>Cyber Essentials Pre-Assessment Pack</h1>
        <p class="muted">{escape(str(pack.get("certification_boundary", "")))}</p>
        <div class="tabs">{section_tabs}</div>
      </header>

      <section class="panel">
        <h2>Question Set</h2>
        <div class="grid">
          {_metric("Set", question_set.get("name", "unknown"), f"version {question_set.get('version', 'unknown')}")}
          {_metric("Requirements", question_set.get("requirements_version", "unknown"), "NCSC version")}
          {_metric("Questions", pack.get("question_count", 0), "mapped entries")}
          {_metric("Technical", pack.get("technical_question_count", 0), "technical-control entries")}
        </div>
      </section>

      <section class="panel">
        <h2>Coverage</h2>
        <div class="grid">
          {_count_metrics(summary.get("evidence_class_counts", {}))}
        </div>
      </section>

      <section class="panel">
        <h2>Proposed Status</h2>
        <div class="grid">
          {_count_metrics(summary.get("proposed_status_counts", {}))}
        </div>
      </section>

      {section_html}

      <footer>{escape(str(pack.get("deterministic_score_impact", "")))}</footer>
    </main>
  </body>
</html>
"""


def write_ce_self_assessment_html(html_content: str, output_path: str | Path) -> Path:
    """Write a CE self-assessment HTML report."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_content, encoding="utf-8")
    return path


def _section_html(section: str, answers: list[dict[str, Any]]) -> str:
    items = "".join(_answer_html(answer) for answer in answers)
    return f"""
      <section class="panel" id="{escape(section)}">
        <h2>{escape(section.replace("_", " ").title())}</h2>
        {items}
      </section>
    """


def _answer_html(answer: dict[str, Any]) -> str:
    status = str(answer.get("proposed_status", "manual_required"))
    linked = answer.get("linked_findings", [])
    evidence = answer.get("evidence", [])
    planned = answer.get("planned_evidence_paths", [])
    linked_markup = _list_items(
        [
            f"{item.get('control_id')} {item.get('priority')} {item.get('score')}: {item.get('title')}"
            for item in linked
            if isinstance(item, dict)
        ],
        "No linked CRIS-SME risk finding.",
    )
    evidence_markup = _list_items(evidence, "No evidence snippet attached.")
    planned_markup = _list_items(planned, "No planned evidence path recorded.")
    controls = ", ".join(str(item) for item in answer.get("supporting_control_ids", []))
    return f"""
        <article class="answer">
          <h3>{escape(str(answer.get("question_id", "unknown")))}: {escape(str(answer.get("short_paraphrase", "")))}</h3>
          <div class="meta">
            <span class="pill">{escape(str(answer.get("evidence_class", "unknown")))}</span>
            <span class="pill status-{escape(status)}">{escape(status)}</span>
            <span class="pill">controls: {escape(controls or "none")}</span>
          </div>
          <p class="muted">{escape(str(answer.get("caveat", "")))}</p>
          <details>
            <summary>Linked findings</summary>
            <ul>{linked_markup}</ul>
          </details>
          <details>
            <summary>Evidence snippets</summary>
            <ul>{evidence_markup}</ul>
          </details>
          <details>
            <summary>Evidence still needed</summary>
            <ul>{planned_markup}</ul>
          </details>
        </article>
    """


def _group_by_section(answers: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for answer in answers:
        section = str(answer.get("section", "unknown"))
        grouped.setdefault(section, []).append(answer)
    return grouped


def _metric(label: str, value: object, helper: object) -> str:
    return (
        '<div class="panel">'
        f'<div class="metric">{escape(str(value))}</div>'
        f'<div><strong>{escape(label)}</strong></div>'
        f'<div class="muted">{escape(str(helper))}</div>'
        "</div>"
    )


def _count_metrics(counts: object) -> str:
    if not isinstance(counts, dict) or not counts:
        return _metric("Unavailable", 0, "no counts")
    return "".join(
        _metric(str(key).replace("_", " ").title(), value, "entries")
        for key, value in sorted(counts.items())
    )


def _list_items(items: object, empty: str) -> str:
    if not isinstance(items, list):
        items = []
    values = [str(item).strip() for item in items if str(item).strip()]
    if not values:
        values = [empty]
    return "".join(f"<li>{escape(value)}</li>" for value in values)

