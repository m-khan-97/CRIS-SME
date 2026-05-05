# Static Evidence Room rendering for selective disclosure packages.
from __future__ import annotations

import html
from pathlib import Path
from typing import Any


def build_evidence_room_html(package: dict[str, Any]) -> str:
    """Build a static stakeholder Evidence Room from a selective disclosure package."""
    rooms = [room for room in package.get("rooms", []) if isinstance(room, dict)]
    manifest = package.get("share_manifest", {})
    if not isinstance(manifest, dict):
        manifest = {}
    tabs = "".join(
        f'<a href="#{_escape(room.get("profile_id", "room"))}">{_escape(room.get("profile_name", "Room"))}</a>'
        for room in rooms
    )
    room_html = "".join(_room_section(room) for room in rooms)
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>CRIS-SME Evidence Room</title>
    <style>
      :root {{
        --bg: #f7f8fa;
        --ink: #172033;
        --muted: #64748b;
        --panel: #ffffff;
        --line: #d8e0ea;
        --accent: #0f766e;
        --accent-2: #334155;
        --warn: #a16207;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background: var(--bg);
        color: var(--ink);
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      }}
      .wrap {{ max-width: 1220px; margin: 0 auto; padding: 24px 18px 48px; }}
      header {{ border-bottom: 1px solid var(--line); margin-bottom: 18px; padding-bottom: 16px; }}
      h1 {{ margin: 0; font-size: 2rem; }}
      h2 {{ margin: 0 0 10px; font-size: 1.15rem; }}
      h3 {{ margin: 0 0 8px; font-size: 0.98rem; }}
      h1, h2, h3, p, div {{ min-width: 0; }}
      p {{ line-height: 1.55; overflow-wrap: anywhere; }}
      .muted {{ color: var(--muted); }}
      .tabs {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 14px 0; }}
      .tabs a {{
        color: #042f2e;
        background: #ccfbf1;
        border: 1px solid #99f6e4;
        border-radius: 999px;
        padding: 7px 11px;
        text-decoration: none;
        font-weight: 700;
      }}
      .grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(min(100%, 230px), 1fr));
        gap: 12px;
      }}
      .panel {{
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 13px;
        margin-bottom: 14px;
        min-width: 0;
        overflow: hidden;
      }}
      .metric {{
        font-size: clamp(0.92rem, 2.5vw, 1.45rem);
        font-weight: 800;
        line-height: 1.16;
        margin: 2px 0;
        max-width: 100%;
        overflow-wrap: anywhere;
        word-break: break-word;
      }}
      .list {{ display: grid; gap: 10px; }}
      .item {{
        border: 1px solid var(--line);
        border-radius: 8px;
        background: #fbfdff;
        padding: 10px;
        min-width: 0;
        overflow: hidden;
      }}
      .mono {{
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: 0.82rem;
        line-height: 1.45;
        overflow-wrap: anywhere;
        word-break: break-word;
      }}
      .status-verified {{ color: var(--accent); font-weight: 800; }}
      .status-caveated, .status-unverified {{ color: var(--warn); font-weight: 800; }}
      .room {{ scroll-margin-top: 18px; }}
      footer {{ color: var(--muted); margin-top: 18px; font-size: 0.9rem; }}
    </style>
  </head>
  <body>
    <main class="wrap">
      <header>
        <h1>CRIS-SME Evidence Room</h1>
        <p class="muted">Selective disclosure package with redacted evidence, withheld-evidence reasons, claim citations, assurance case, provenance paths, and RBOM references.</p>
        <div class="tabs">{tabs}</div>
      </header>

      <section class="panel">
        <h2>Share Manifest</h2>
        <div class="grid">
          {_metric("Profiles", package.get("profile_count", 0), "disclosure views")}
          {_metric("RBOM", manifest.get("rbom_report_sha256", "unavailable"), "report hash reference")}
          {_metric("Generated", package.get("generated_at", "unknown"), "package time")}
        </div>
      </section>

      {room_html}

      <footer>{_escape(package.get("deterministic_score_impact", "No deterministic score impact."))}</footer>
    </main>
  </body>
</html>
"""


def write_evidence_room_html(html_content: str, output_path: str | Path) -> Path:
    """Write Evidence Room HTML artifact."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html_content, encoding="utf-8")
    return path


def _room_section(room: dict[str, Any]) -> str:
    claims = _list(room.get("claims"))
    evidence = _list(room.get("shared_evidence"))
    withheld = _list(room.get("withheld_items"))
    redactions = _list(room.get("redactions"))
    paths = _list(room.get("provenance_paths"))
    case = room.get("assurance_case", {})
    if not isinstance(case, dict):
        case = {}
    return f"""
      <section class="room" id="{_escape(room.get("profile_id", "room"))}">
        <div class="panel">
          <h2>{_escape(room.get("profile_name", "Disclosure Room"))}</h2>
          <p class="muted">{_escape(room.get("audience", "stakeholder"))} | {_escape(room.get("disclosure_level", "redacted"))}</p>
          <div class="grid">
            {_metric("Claims", room.get("included_claim_count", 0), "included")}
            {_metric("Evidence", room.get("shared_evidence_count", 0), "shared")}
            {_metric("Redactions", room.get("redaction_count", 0), "applied")}
            {_metric("Withheld", room.get("withheld_count", 0), "recorded")}
          </div>
        </div>

        <div class="grid">
          <div class="panel">
            <h2>Claims</h2>
            <div class="list">{''.join(_claim_item(claim) for claim in claims[:12])}</div>
          </div>
          <div class="panel">
            <h2>Assurance Case</h2>
            <p><strong>Conclusion:</strong> {_escape(case.get("overall_conclusion", "unknown"))}</p>
            <p><strong>Score:</strong> {_escape(case.get("assurance_score", "unknown"))}</p>
            <div class="list">{''.join(_argument_item(arg) for arg in _list(case.get("arguments"))[:5])}</div>
          </div>
        </div>

        <div class="grid">
          <div class="panel">
            <h2>Shared Evidence</h2>
            <div class="list">{''.join(_evidence_item(item) for item in evidence[:12])}</div>
          </div>
          <div class="panel">
            <h2>Withheld Evidence</h2>
            <div class="list">{''.join(_withheld_item(item) for item in withheld[:12])}</div>
          </div>
        </div>

        <div class="grid">
          <div class="panel">
            <h2>Provenance Paths</h2>
            <div class="list">{''.join(_path_item(path) for path in paths[:8])}</div>
          </div>
          <div class="panel">
            <h2>Redaction Register</h2>
            <div class="list">{''.join(_redaction_item(item) for item in redactions[:12])}</div>
          </div>
        </div>
      </section>
"""


def _metric(title: str, value: object, note: str) -> str:
    return (
        '<article class="item">'
        f"<h3>{_escape(title)}</h3>"
        f'<div class="metric">{_escape(value)}</div>'
        f'<p class="muted">{_escape(note)}</p>'
        "</article>"
    )


def _claim_item(claim: Any) -> str:
    if not isinstance(claim, dict):
        return ""
    status = str(claim.get("verification_status", "unknown"))
    return (
        '<article class="item">'
        f'<div class="mono">{_escape(claim.get("claim_id", ""))}</div>'
        f'<p class="status-{_escape(status)}">{_escape(status)}</p>'
        f"<p>{_escape(claim.get('statement', ''))}</p>"
        f'<p class="mono">Controls: {_escape(", ".join(str(item) for item in _list(claim.get("control_ids"))))}</p>'
        "</article>"
    )


def _argument_item(argument: Any) -> str:
    if not isinstance(argument, dict):
        return ""
    return (
        '<article class="item">'
        f"<h3>{_escape(argument.get('top_claim', 'Argument'))}</h3>"
        f"<p>{_escape(argument.get('reasoning', ''))}</p>"
        f'<p class="mono">Claims: {_escape(", ".join(str(item) for item in _list(argument.get("supporting_claim_ids"))))}</p>'
        "</article>"
    )


def _evidence_item(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    evidence = "; ".join(str(entry) for entry in _list(item.get("evidence"))[:4])
    return (
        '<article class="item">'
        f"<h3>{_escape(item.get('control_id', 'Control'))}</h3>"
        f"<p>{_escape(item.get('title', 'Evidence'))}</p>"
        f'<p class="mono">{_escape(evidence)}</p>'
        f'<p class="muted">Proof strength: {_escape(item.get("proof_strength", "unknown"))}</p>'
        "</article>"
    )


def _withheld_item(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    return (
        '<article class="item">'
        f'<div class="mono">{_escape(item.get("item_id", ""))}</div>'
        f"<p>{_escape(item.get('replacement_summary', 'Evidence withheld.'))}</p>"
        f'<p class="muted">{_escape(item.get("reason", ""))}</p>'
        "</article>"
    )


def _path_item(path: Any) -> str:
    if not isinstance(path, dict):
        return ""
    return (
        '<article class="item">'
        f"<h3>{_escape(path.get('control_id', 'Control'))}</h3>"
        f"<p>{_escape(path.get('summary', ''))}</p>"
        f'<div class="mono">{_escape(" -> ".join(str(item) for item in _list(path.get("node_ids"))))}</div>'
        "</article>"
    )


def _redaction_item(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    return (
        '<article class="item">'
        f'<div class="mono">{_escape(item.get("field_path", ""))}</div>'
        f"<p>{_escape(item.get('redaction_type', 'redaction'))}</p>"
        f'<p class="muted">{_escape(item.get("reason", ""))}</p>'
        "</article>"
    )


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)
