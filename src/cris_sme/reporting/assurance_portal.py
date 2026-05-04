# Customer-facing assurance portal HTML generation for CRIS-SME.
from __future__ import annotations

import html
from pathlib import Path
from typing import Any


def build_assurance_portal_html(report: dict[str, Any]) -> str:
    """Build a customer-facing static assurance portal from trust artifacts."""
    trust_badge = _dict(report.get("report_trust_badge"))
    assurance_case = _dict(report.get("assurance_case"))
    claim_pack = _dict(report.get("claim_verification_pack"))
    provenance = _dict(report.get("decision_provenance_graph"))
    narrative = _dict(report.get("claim_bound_narrative"))
    replay = _dict(_dict(report.get("assessment_replay")).get("replay"))
    rbom = _dict(report.get("risk_bill_of_materials"))
    backlog = _dict(report.get("evidence_gap_backlog"))

    sections = _narrative_sections(narrative)
    arguments = _arguments(assurance_case)
    claims = _claims(claim_pack)
    paths = _paths(provenance)

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>CRIS-SME Assurance Portal</title>
    <style>
      :root {{
        --bg: #f6f8fb;
        --ink: #162231;
        --muted: #66788f;
        --panel: #ffffff;
        --line: #d9e2ec;
        --accent: #0d9488;
        --accent-2: #2563eb;
        --warn: #b45309;
        --ok: #15803d;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background: var(--bg);
        color: var(--ink);
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      }}
      .wrap {{ max-width: 1180px; margin: 0 auto; padding: 24px 18px 48px; }}
      header {{
        border-bottom: 1px solid var(--line);
        padding-bottom: 18px;
        margin-bottom: 20px;
      }}
      h1 {{ margin: 0; font-size: 2rem; }}
      h2 {{ margin: 0 0 10px; font-size: 1.1rem; }}
      p {{ line-height: 1.55; }}
      .muted {{ color: var(--muted); }}
      .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        gap: 14px;
        margin-bottom: 16px;
      }}
      .panel {{
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 14px;
      }}
      .badge {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        color: #042f2e;
        background: #ccfbf1;
        border: 1px solid #99f6e4;
        border-radius: 999px;
        padding: 6px 10px;
        font-weight: 700;
      }}
      .metric {{ font-size: 1.65rem; font-weight: 800; margin: 4px 0; }}
      .list {{ display: grid; gap: 10px; }}
      .item {{
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 10px;
        background: #fbfdff;
      }}
      .claim-id {{
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: 0.82rem;
        color: var(--accent-2);
      }}
      .status-verified {{ color: var(--ok); font-weight: 700; }}
      .status-caveated, .status-unverified {{ color: var(--warn); font-weight: 700; }}
      .path {{
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: 0.82rem;
        overflow-wrap: anywhere;
        color: #334155;
      }}
      footer {{ margin-top: 22px; color: var(--muted); font-size: 0.9rem; }}
    </style>
  </head>
  <body>
    <main class="wrap">
      <header>
        <h1>CRIS-SME Assurance Portal</h1>
        <p class="muted">Customer-facing view of report trust, replay, claims, assurance case, provenance paths, and caveats.</p>
        <span class="badge">{_escape(trust_badge.get("label", "CRIS-SME Assurance"))}</span>
      </header>

      <section class="grid">
        {_metric_card("Assurance Score", f'{_float(assurance_case.get("assurance_score")):.2f}', assurance_case.get("overall_conclusion", "unknown"))}
        {_metric_card("Claims", str(int(claim_pack.get("claim_count", 0))), f'{int(claim_pack.get("verified_claim_count", 0))} verified')}
        {_metric_card("Replay", "Verified" if replay.get("deterministic_match") else "Not verified", f"Delta {_float(replay.get('overall_risk_delta')):.2f}")}
        {_metric_card("RBOM", "Present" if rbom.get("canonical_report_sha256") else "Missing", f"{len(rbom.get('artifacts', [])) if isinstance(rbom.get('artifacts'), list) else 0} artifacts")}
        {_metric_card("Evidence Gaps", str(int(backlog.get("item_count", 0))), f"{int(backlog.get('high_priority_count', 0))} high priority")}
        {_metric_card("Provenance", str(int(provenance.get("path_count", 0))), f"{int(provenance.get('node_count', 0))} nodes")}
      </section>

      <section class="panel">
        <h2>Claim-Bound Narrative</h2>
        <div class="list">{''.join(_section_card(section) for section in sections)}</div>
      </section>

      <section class="grid">
        <div class="panel">
          <h2>Assurance Case Arguments</h2>
          <div class="list">{''.join(_argument_card(argument) for argument in arguments)}</div>
        </div>
        <div class="panel">
          <h2>Verified And Caveated Claims</h2>
          <div class="list">{''.join(_claim_card(claim) for claim in claims[:12])}</div>
        </div>
      </section>

      <section class="panel">
        <h2>Top Provenance Paths</h2>
        <div class="list">{''.join(_path_card(path) for path in paths[:8])}</div>
      </section>

      <footer>
        {_escape(str(trust_badge.get("risk_score_impact", "The assurance portal does not change deterministic CRIS-SME risk scores.")))}
      </footer>
    </main>
  </body>
</html>
"""


def write_assurance_portal_html(html_content: str, output_path: str | Path) -> Path:
    """Write the assurance portal HTML artifact."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_content, encoding="utf-8")
    return path


def _metric_card(title: str, value: str, note: object) -> str:
    return (
        '<article class="panel">'
        f"<h2>{_escape(title)}</h2>"
        f'<div class="metric">{_escape(value)}</div>'
        f'<p class="muted">{_escape(str(note))}</p>'
        "</article>"
    )


def _section_card(section: dict[str, Any]) -> str:
    claims = ", ".join(str(item) for item in section.get("cited_claim_ids", []))
    caveats = section.get("caveats", [])
    caveat_html = ""
    if isinstance(caveats, list) and caveats:
        caveat_html = "<p><strong>Caveats:</strong> " + _escape("; ".join(str(item) for item in caveats)) + "</p>"
    return (
        '<article class="item">'
        f"<h2>{_escape(str(section.get('heading', 'Narrative')))}</h2>"
        f"<p>{_escape(str(section.get('text', '')))}</p>"
        f'<p class="claim-id">Claims: {_escape(claims)}</p>'
        f"{caveat_html}"
        "</article>"
    )


def _argument_card(argument: dict[str, Any]) -> str:
    return (
        '<article class="item">'
        f"<h2>{_escape(str(argument.get('top_claim', 'Argument')))}</h2>"
        f"<p><strong>Conclusion:</strong> {_escape(str(argument.get('conclusion', 'unknown')))} | "
        f"<strong>Confidence:</strong> {_float(argument.get('confidence')):.2f}</p>"
        f"<p>{_escape(str(argument.get('reasoning', '')))}</p>"
        f'<p class="claim-id">Supporting claims: {_escape(", ".join(str(item) for item in argument.get("supporting_claim_ids", [])))}</p>'
        "</article>"
    )


def _claim_card(claim: dict[str, Any]) -> str:
    status = str(claim.get("verification_status", "unknown"))
    return (
        '<article class="item">'
        f'<div class="claim-id">{_escape(str(claim.get("claim_id", "")))}</div>'
        f'<p class="status-{_escape(status)}">{_escape(status)}</p>'
        f"<p>{_escape(str(claim.get('statement', '')))}</p>"
        "</article>"
    )


def _path_card(path: dict[str, Any]) -> str:
    return (
        '<article class="item">'
        f"<h2>{_escape(str(path.get('control_id', 'Control')))}</h2>"
        f"<p>{_escape(str(path.get('summary', '')))}</p>"
        f'<div class="path">{_escape(" -> ".join(str(item) for item in path.get("node_ids", [])))}</div>'
        "</article>"
    )


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _narrative_sections(narrative: dict[str, Any]) -> list[dict[str, Any]]:
    sections = narrative.get("sections", [])
    return [item for item in sections if isinstance(item, dict)] if isinstance(sections, list) else []


def _arguments(assurance_case: dict[str, Any]) -> list[dict[str, Any]]:
    arguments = assurance_case.get("arguments", [])
    return [item for item in arguments if isinstance(item, dict)] if isinstance(arguments, list) else []


def _claims(claim_pack: dict[str, Any]) -> list[dict[str, Any]]:
    claims = claim_pack.get("claims", [])
    return [item for item in claims if isinstance(item, dict)] if isinstance(claims, list) else []


def _paths(provenance: dict[str, Any]) -> list[dict[str, Any]]:
    paths = provenance.get("top_decision_paths", [])
    return [item for item in paths if isinstance(item, dict)] if isinstance(paths, list) else []


def _float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)
