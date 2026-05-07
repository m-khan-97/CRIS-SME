# HTML rendering for Cyber Essentials evaluation metrics.
from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any


def build_ce_evaluation_metrics_html(metrics: dict[str, Any]) -> str:
    """Build a static HTML report for CE evaluation metrics."""
    observability = _dict(metrics.get("observability_metrics"))
    review = _dict(metrics.get("review_metrics"))
    status_counts = _dict(metrics.get("status_counts"))
    paper_tables = _dict(metrics.get("paper_tables"))

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>CRIS-SME Cyber Essentials Evaluation Metrics</title>
    <style>
      :root {{
        --bg: #f6f8fb;
        --ink: #172033;
        --muted: #617083;
        --panel: #ffffff;
        --line: #d8e2ec;
        --accent: #0f766e;
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
      h1 {{ margin: 0; font-size: clamp(1.7rem, 4vw, 2.45rem); letter-spacing: 0; }}
      h2 {{ margin: 0 0 12px; font-size: 1.25rem; letter-spacing: 0; }}
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
      table {{ width: 100%; border-collapse: collapse; background: #fff; }}
      th, td {{ border-bottom: 1px solid var(--line); padding: 9px; text-align: left; vertical-align: top; overflow-wrap: anywhere; }}
      th {{ color: var(--muted); font-size: 0.78rem; text-transform: uppercase; }}
      .tables {{ display: grid; gap: 14px; }}
      footer {{ color: var(--muted); margin-top: 20px; font-size: 0.9rem; }}
    </style>
  </head>
  <body>
    <main>
      <header>
        <h1>Cyber Essentials Evaluation Metrics</h1>
        <p class="muted">Paper-ready measurements for CRIS-SME CE pre-population, review, observability, and evidence gaps.</p>
      </header>

      <section class="panel">
        <h2>Evaluation Overview</h2>
        <div class="grid">
          {_metric("Questions", metrics.get("question_count", 0), "mapped CE entries")}
          {_metric("Technical", metrics.get("technical_question_count", 0), "technical-control entries")}
          {_metric("Cloud Observable", f"{observability.get('cloud_supported_rate', 0)}%", f"{observability.get('cloud_supported_count', 0)} entries")}
          {_metric("Technical Cloud Observable", f"{observability.get('technical_cloud_supported_rate', 0)}%", f"{observability.get('technical_cloud_supported_count', 0)} entries")}
          {_metric("Reviewed", f"{review.get('reviewed_rate', 0)}%", f"{review.get('reviewed_count', 0)} entries")}
          {_metric("Agreement", f"{review.get('agreement_rate', 0)}%", f"{review.get('agreement_count', 0)} of {review.get('agreement_evaluable_count', 0)}")}
        </div>
      </section>

      <section class="panel">
        <h2>Review Outcomes</h2>
        <div class="grid">
          {_metric("Accepted", review.get("accepted_count", 0), "reviewer accepted")}
          {_metric("Overrides", review.get("override_count", 0), "reviewer changed")}
          {_metric("Needs Evidence", review.get("needs_evidence_count", 0), "blocked entries")}
          {_metric("Pending", review.get("pending_count", 0), "awaiting review")}
        </div>
      </section>

      <section class="panel tables">
        <h2>Paper Tables</h2>
        {_table("Observability By Evidence Class", paper_tables.get("observability_by_evidence_class", []))}
        {_table("Technical Observability", paper_tables.get("technical_observability_by_evidence_class", []))}
        {_table("Proposed Answers", paper_tables.get("proposed_answers", []))}
        {_table("Final Reviewer Answers", paper_tables.get("final_answers", []))}
        {_table("Section Coverage", paper_tables.get("section_coverage", []))}
        {_table("Review Outcomes", paper_tables.get("review_outcomes", []))}
        {_table("Control Failure Contribution", paper_tables.get("control_failure_contribution", []))}
      </section>

      <section class="panel">
        <h2>Evidence Gaps</h2>
        {_gap_taxonomy(metrics.get("evidence_gap_taxonomy", {}))}
      </section>

      <section class="panel">
        <h2>Status Counts</h2>
        {_table("Proposed Status", _counts_to_rows(status_counts.get("proposed_status_counts", {})))}
      </section>

      <footer>{escape(str(metrics.get("deterministic_score_impact", "")))}</footer>
    </main>
  </body>
</html>
"""


def write_ce_evaluation_metrics_html(
    html_content: str,
    output_path: str | Path,
) -> Path:
    """Write a CE evaluation metrics HTML artifact."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_content, encoding="utf-8")
    return path


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _metric(label: str, value: object, helper: object) -> str:
    return (
        '<div class="panel">'
        f'<div class="metric">{escape(str(value))}</div>'
        f'<div><strong>{escape(label)}</strong></div>'
        f'<div class="muted">{escape(str(helper))}</div>'
        "</div>"
    )


def _table(title: str, rows: object) -> str:
    if not isinstance(rows, list) or not rows:
        return f"<h2>{escape(title)}</h2><p class=\"muted\">No rows available.</p>"
    headers = sorted(
        {
            key
            for row in rows
            if isinstance(row, dict)
            for key in row
        }
    )
    header_html = "".join(f"<th>{escape(header.replace('_', ' ').title())}</th>" for header in headers)
    row_html = "".join(
        "<tr>"
        + "".join(f"<td>{escape(_cell(row.get(header)))}</td>" for header in headers)
        + "</tr>"
        for row in rows
        if isinstance(row, dict)
    )
    return (
        f"<div><h2>{escape(title)}</h2>"
        f"<table><thead><tr>{header_html}</tr></thead><tbody>{row_html}</tbody></table></div>"
    )


def _gap_taxonomy(taxonomy: object) -> str:
    if not isinstance(taxonomy, dict) or not taxonomy:
        return '<p class="muted">No gap taxonomy available.</p>'
    rows = []
    for evidence_class, detail in sorted(taxonomy.items()):
        if not isinstance(detail, dict):
            continue
        rows.append(
            {
                "evidence_class": evidence_class,
                "count": detail.get("count", 0),
                "rate": detail.get("rate", 0),
                "sample_question_ids": ", ".join(
                    str(item) for item in detail.get("sample_question_ids", [])
                ),
                "description": detail.get("description", ""),
            }
        )
    return _table("Evidence Gap Taxonomy", rows)


def _counts_to_rows(counts: object) -> list[dict[str, Any]]:
    if not isinstance(counts, dict):
        return []
    total = sum(value for value in counts.values() if isinstance(value, int))
    return [
        {
            "label": str(label),
            "count": count,
            "rate": round((count / total) * 100, 2) if total else 0.0,
        }
        for label, count in sorted(counts.items())
        if isinstance(count, int)
    ]


def _cell(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)
