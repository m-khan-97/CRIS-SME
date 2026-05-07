# HTML rendering for the Cyber Essentials evidence review console.
from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any


def build_ce_review_console_html(console: dict[str, Any]) -> str:
    """Build an interactive static review console for CE evidence decisions."""
    summary = console.get("review_summary", {})
    if not isinstance(summary, dict):
        summary = {}
    question_set = console.get("question_set", {})
    if not isinstance(question_set, dict):
        question_set = {}
    entries = [
        entry for entry in console.get("entries", []) if isinstance(entry, dict)
    ]
    sections = _group_by_section(entries)
    section_tabs = "".join(
        f'<a href="#{escape(section)}">{escape(section.replace("_", " ").title())}</a>'
        for section in sections
    )
    section_html = "".join(
        _section_html(section, section_entries)
        for section, section_entries in sections.items()
    )
    console_json = json.dumps(console, separators=(",", ":"))

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>CRIS-SME Cyber Essentials Evidence Review Console</title>
    <style>
      :root {{
        --bg: #f6f8fb;
        --ink: #172033;
        --muted: #617083;
        --panel: #ffffff;
        --line: #d8e2ec;
        --accent: #0f766e;
        --accent-soft: #ccfbf1;
        --warning: #a16207;
        --warning-soft: #fef3c7;
        --risk: #b42318;
        --risk-soft: #fee2e2;
        --ok: #166534;
        --ok-soft: #dcfce7;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background: var(--bg);
        color: var(--ink);
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      }}
      main {{ max-width: 1260px; margin: 0 auto; padding: 26px 18px 60px; }}
      header {{
        border-bottom: 1px solid var(--line);
        display: grid;
        gap: 14px;
        padding-bottom: 18px;
        margin-bottom: 18px;
      }}
      h1 {{ margin: 0; font-size: clamp(1.7rem, 4vw, 2.45rem); letter-spacing: 0; }}
      h2 {{ margin: 0 0 12px; font-size: 1.25rem; letter-spacing: 0; }}
      h3 {{ margin: 0 0 8px; font-size: 1rem; letter-spacing: 0; }}
      p {{ line-height: 1.55; overflow-wrap: anywhere; }}
      label {{ display: block; font-size: 0.78rem; font-weight: 800; color: var(--muted); margin-bottom: 5px; }}
      select, input, textarea {{
        width: 100%;
        border: 1px solid var(--line);
        border-radius: 6px;
        background: #fff;
        color: var(--ink);
        font: inherit;
        padding: 8px;
      }}
      textarea {{ min-height: 72px; resize: vertical; }}
      button {{
        border: 1px solid var(--accent);
        background: var(--accent);
        color: #fff;
        border-radius: 6px;
        padding: 9px 12px;
        font-weight: 800;
        cursor: pointer;
      }}
      button.secondary {{
        background: #fff;
        color: var(--accent);
      }}
      .muted {{ color: var(--muted); }}
      .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 190px), 1fr)); gap: 12px; }}
      .review-grid {{ display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.8fr); gap: 14px; align-items: start; }}
      .panel {{
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 14px;
        overflow: hidden;
      }}
      .metric {{ font-size: 1.55rem; font-weight: 800; margin: 2px 0; overflow-wrap: anywhere; }}
      .tabs {{ display: flex; flex-wrap: wrap; gap: 8px; }}
      .tabs a {{
        background: var(--accent-soft);
        color: #042f2e;
        border: 1px solid #99f6e4;
        border-radius: 999px;
        padding: 7px 11px;
        text-decoration: none;
        font-weight: 800;
      }}
      .toolbar {{ display: flex; flex-wrap: wrap; gap: 9px; align-items: center; }}
      .entry {{
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
        max-width: 100%;
        overflow-wrap: anywhere;
      }}
      .status-supported_risk_found {{ background: var(--risk-soft); color: var(--risk); }}
      .status-supported_no_issue {{ background: var(--ok-soft); color: var(--ok); }}
      .status-endpoint_required,
      .status-policy_required,
      .status-manual_required,
      .status-insufficient_evidence {{ background: var(--warning-soft); color: var(--warning); }}
      .state-pending {{ background: #e2e8f0; color: #263548; }}
      .state-accepted {{ background: var(--ok-soft); color: var(--ok); }}
      .state-overridden,
      .state-needs_evidence {{ background: var(--warning-soft); color: var(--warning); }}
      .review-fields {{ display: grid; gap: 10px; }}
      ul {{ margin: 8px 0 0; padding-left: 18px; }}
      li {{ margin-bottom: 5px; overflow-wrap: anywhere; }}
      footer {{ color: var(--muted); margin-top: 20px; font-size: 0.9rem; }}
      @media (max-width: 820px) {{
        .review-grid {{ grid-template-columns: 1fr; }}
      }}
    </style>
  </head>
  <body>
    <main>
      <header>
        <div>
          <h1>Cyber Essentials Evidence Review Console</h1>
          <p class="muted">{escape(str(console.get("review_policy", {}).get("certification_boundary", "")))}</p>
        </div>
        <div class="toolbar">
          <button type="button" id="export-review">Export Review Ledger</button>
          <button type="button" class="secondary" id="reset-review">Clear Local Decisions</button>
        </div>
        <div class="tabs">{section_tabs}</div>
      </header>

      <section class="panel">
        <h2>Review Set</h2>
        <div class="grid">
          {_metric("Question Set", question_set.get("name", "unknown"), f"version {question_set.get('version', 'unknown')}")}
          {_metric("Questions", console.get("question_count", 0), "review entries")}
          {_metric("Human Review", summary.get("human_review_required_count", 0), "entries")}
          {_metric("Cloud Supported", summary.get("cloud_supported_review_items", 0), "entries")}
        </div>
      </section>

      <section class="panel">
        <h2>Reviewer State</h2>
        <div class="grid" id="review-state-metrics">
          {_count_metrics(summary.get("review_state_counts", {}))}
        </div>
      </section>

      {section_html}

      <footer>{escape(str(console.get("deterministic_score_impact", "")))}</footer>
    </main>
    <script>
      const CRIS_CE_CONSOLE = {console_json};
      const STORAGE_KEY = "cris_sme_ce_review_console_v1";

      function loadDecisions() {{
        try {{
          return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{{}}");
        }} catch (_error) {{
          return {{}};
        }}
      }}

      function saveDecision(questionId, decision) {{
        const decisions = loadDecisions();
        decisions[questionId] = decision;
        localStorage.setItem(STORAGE_KEY, JSON.stringify(decisions));
        renderStateMetrics();
      }}

      function hydrateDecisions() {{
        const decisions = loadDecisions();
        document.querySelectorAll("[data-question-id]").forEach((article) => {{
          const questionId = article.dataset.questionId;
          const decision = decisions[questionId] || {{}};
          article.querySelectorAll("[data-review-field]").forEach((field) => {{
            const key = field.dataset.reviewField;
            if (decision[key] !== undefined) {{
              field.value = decision[key];
            }}
          }});
          updateStatePill(article);
        }});
        renderStateMetrics();
      }}

      function captureDecision(article) {{
        const decision = {{}};
        article.querySelectorAll("[data-review-field]").forEach((field) => {{
          decision[field.dataset.reviewField] = field.value;
        }});
        saveDecision(article.dataset.questionId, decision);
        updateStatePill(article);
      }}

      function updateStatePill(article) {{
        const select = article.querySelector("[data-review-field='state']");
        const pill = article.querySelector("[data-review-state-pill]");
        const state = select ? select.value : "pending";
        if (!pill) return;
        pill.textContent = state;
        pill.className = "pill state-" + state;
      }}

      function mergedLedger() {{
        const decisions = loadDecisions();
        return {{
          ...CRIS_CE_CONSOLE,
          exported_at: new Date().toISOString(),
          entries: CRIS_CE_CONSOLE.entries.map((entry) => {{
            const decision = decisions[entry.question_id];
            if (!decision) return entry;
            return {{
              ...entry,
              review_decision: {{
                ...entry.review_decision,
                ...decision,
              }},
            }};
          }}),
        }};
      }}

      function renderStateMetrics() {{
        const counts = {{}};
        CRIS_CE_CONSOLE.entries.forEach((entry) => {{
          counts[entry.review_decision.state] = (counts[entry.review_decision.state] || 0) + 1;
        }});
        Object.values(loadDecisions()).forEach((decision) => {{
          const state = decision.state || "pending";
          counts.pending = Math.max(0, (counts.pending || 0) - 1);
          counts[state] = (counts[state] || 0) + 1;
        }});
        const container = document.getElementById("review-state-metrics");
        if (!container) return;
        container.innerHTML = Object.entries(counts).sort().map(([key, value]) => `
          <div class="panel">
            <div class="metric">${{value}}</div>
            <div><strong>${{key.replaceAll("_", " ")}}</strong></div>
            <div class="muted">entries</div>
          </div>
        `).join("");
      }}

      document.querySelectorAll("[data-question-id]").forEach((article) => {{
        article.querySelectorAll("[data-review-field]").forEach((field) => {{
          field.addEventListener("change", () => captureDecision(article));
          field.addEventListener("keyup", () => captureDecision(article));
        }});
      }});

      document.getElementById("export-review").addEventListener("click", () => {{
        const blob = new Blob([JSON.stringify(mergedLedger(), null, 2)], {{ type: "application/json" }});
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = "cris_sme_ce_review_ledger.json";
        link.click();
        URL.revokeObjectURL(url);
      }});

      document.getElementById("reset-review").addEventListener("click", () => {{
        localStorage.removeItem(STORAGE_KEY);
        hydrateDecisions();
      }});

      hydrateDecisions();
    </script>
  </body>
</html>
"""


def write_ce_review_console_html(html_content: str, output_path: str | Path) -> Path:
    """Write a CE evidence review console HTML report."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_content, encoding="utf-8")
    return path


def _section_html(section: str, entries: list[dict[str, Any]]) -> str:
    items = "".join(_entry_html(entry) for entry in entries)
    return f"""
      <section class="panel" id="{escape(section)}">
        <h2>{escape(section.replace("_", " ").title())}</h2>
        {items}
      </section>
    """


def _entry_html(entry: dict[str, Any]) -> str:
    status = str(entry.get("proposed_status", "manual_required"))
    decision = entry.get("review_decision", {})
    if not isinstance(decision, dict):
        decision = {}
    state = str(decision.get("state", "pending"))
    linked = entry.get("linked_findings", [])
    evidence = entry.get("evidence", [])
    planned = entry.get("planned_evidence_paths", [])
    controls = ", ".join(str(item) for item in entry.get("supporting_control_ids", []))
    return f"""
        <article class="entry" data-question-id="{escape(str(entry.get("question_id", "unknown")))}">
          <div class="review-grid">
            <div>
              <h3>{escape(str(entry.get("question_id", "unknown")))}: {escape(str(entry.get("short_paraphrase", "")))}</h3>
              <div class="meta">
                <span class="pill">{escape(str(entry.get("evidence_class", "unknown")))}</span>
                <span class="pill status-{escape(status)}">{escape(status)}</span>
                <span class="pill" data-review-state-pill>{escape(state)}</span>
                <span class="pill">controls: {escape(controls or "none")}</span>
              </div>
              <p class="muted">{escape(str(entry.get("caveat", "")))}</p>
              <details>
                <summary>Linked findings</summary>
                <ul>{_linked_items(linked)}</ul>
              </details>
              <details>
                <summary>Evidence snippets</summary>
                <ul>{_list_items(evidence, "No evidence snippet attached.")}</ul>
              </details>
              <details>
                <summary>Evidence still needed</summary>
                <ul>{_list_items(planned, "No planned evidence path recorded.")}</ul>
              </details>
            </div>
            <div class="review-fields">
              {_select("Review decision", "state", state, ["pending", "accepted", "overridden", "needs_evidence"])}
              {_input("Final status", "final_status", decision.get("final_status", ""))}
              {_input("Reviewer", "reviewer", decision.get("reviewer", ""))}
              {_input("Evidence reference", "additional_evidence_reference", decision.get("additional_evidence_reference", ""))}
              {_textarea("Reviewer note", "reviewer_note", decision.get("reviewer_note", ""))}
              {_textarea("Override reason", "override_reason", decision.get("override_reason", ""))}
            </div>
          </div>
        </article>
    """


def _group_by_section(entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        section = str(entry.get("section", "unknown"))
        grouped.setdefault(section, []).append(entry)
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
        return _metric("Pending", 0, "entries")
    return "".join(
        _metric(str(key).replace("_", " ").title(), value, "entries")
        for key, value in sorted(counts.items())
    )


def _linked_items(items: object) -> str:
    if not isinstance(items, list):
        items = []
    values = []
    for item in items:
        if isinstance(item, dict):
            values.append(
                f"{item.get('control_id')} {item.get('priority')} {item.get('score')}: {item.get('title')}"
            )
    return _list_items(values, "No linked CRIS-SME risk finding.")


def _list_items(items: object, empty: str) -> str:
    if not isinstance(items, list):
        items = []
    values = [str(item).strip() for item in items if str(item).strip()]
    if not values:
        values = [empty]
    return "".join(f"<li>{escape(value)}</li>" for value in values)


def _select(label: str, field: str, value: object, options: list[str]) -> str:
    options_html = "".join(
        f'<option value="{escape(option)}"{" selected" if option == value else ""}>{escape(option)}</option>'
        for option in options
    )
    return (
        f'<div><label>{escape(label)}</label>'
        f'<select data-review-field="{escape(field)}">{options_html}</select></div>'
    )


def _input(label: str, field: str, value: object) -> str:
    return (
        f'<div><label>{escape(label)}</label>'
        f'<input data-review-field="{escape(field)}" value="{escape(str(value))}" /></div>'
    )


def _textarea(label: str, field: str, value: object) -> str:
    return (
        f'<div><label>{escape(label)}</label>'
        f'<textarea data-review-field="{escape(field)}">{escape(str(value))}</textarea></div>'
    )
