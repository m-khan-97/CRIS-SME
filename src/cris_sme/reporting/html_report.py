# HTML reporting for presentation-ready CRIS-SME outputs.
from __future__ import annotations

from html import escape
from pathlib import Path


def build_html_report(report: dict[str, object]) -> str:
    """Build a self-contained HTML report from the CRIS-SME JSON report structure."""
    summary = escape(str(report.get("summary", "CRIS-SME report")))
    executive_summary = escape(str(report.get("executive_summary", "")))
    overall_risk_score = float(report.get("overall_risk_score", 0.0))
    evaluation_context = report.get("evaluation_context", {})
    category_scores = report.get("category_scores", {})
    organizations = report.get("organizations", [])
    prioritized_risks = report.get("prioritized_risks", [])
    history_comparison = report.get("history_comparison", {})
    compliance = report.get("compliance", {})
    budget_aware_remediation = report.get("budget_aware_remediation", {})
    plain_language_narrative = report.get("plain_language_narrative", {})

    category_cards = "".join(
        f"""
        <article class="metric-card">
          <h3>{escape(str(category))}</h3>
          <p class="metric-value">{float(score):.2f}</p>
        </article>
        """
        for category, score in category_scores.items()
    )

    organization_cards = "".join(
        _build_organization_card(organization)
        for organization in organizations
        if isinstance(organization, dict)
    )

    prioritized_rows = "".join(
        _build_risk_row(risk)
        for risk in prioritized_risks
        if isinstance(risk, dict)
    )
    comparison_card = _build_history_comparison_card(history_comparison)
    uk_regulatory_card = _build_uk_regulatory_card(compliance)
    remediation_card = _build_budget_remediation_card(budget_aware_remediation)
    narrator_card = _build_narrator_card(plain_language_narrative)

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>CRIS-SME Risk Report</title>
    <style>
      :root {{
        --bg: #f4f0e8;
        --panel: #fffaf2;
        --panel-strong: #f1e5d2;
        --ink: #182126;
        --muted: #5f6b73;
        --line: #d5c7b3;
        --accent: #0b6e4f;
        --accent-soft: #d9efe6;
        --risk: #8b2e1f;
        --risk-soft: #f8e0da;
        --warn: #9f6b00;
        --warn-soft: #f8edd2;
        --shadow: 0 18px 42px rgba(41, 31, 21, 0.08);
        --radius: 18px;
      }}

      * {{
        box-sizing: border-box;
      }}

      body {{
        margin: 0;
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top left, rgba(11, 110, 79, 0.12), transparent 30%),
          radial-gradient(circle at top right, rgba(139, 46, 31, 0.1), transparent 28%),
          linear-gradient(180deg, #fbf7f0 0%, var(--bg) 100%);
      }}

      main {{
        max-width: 1240px;
        margin: 0 auto;
        padding: 32px 20px 64px;
      }}

      .hero {{
        background: linear-gradient(135deg, rgba(11, 110, 79, 0.95), rgba(24, 33, 38, 0.95));
        color: #f8fbfa;
        border-radius: 28px;
        padding: 32px;
        box-shadow: var(--shadow);
      }}

      .hero h1 {{
        margin: 0 0 8px;
        font-family: "IBM Plex Serif", Georgia, serif;
        font-size: clamp(2rem, 4vw, 3.4rem);
        line-height: 1.02;
      }}

      .hero p {{
        margin: 0;
        max-width: 920px;
        font-size: 1rem;
        line-height: 1.6;
      }}

      .hero-grid,
      .metric-grid,
      .org-grid {{
        display: grid;
        gap: 16px;
      }}

      .hero-grid {{
        margin-top: 24px;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      }}

      .metric-grid,
      .org-grid {{
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      }}

      .hero-card,
      .metric-card,
      .org-card,
      .table-panel,
      .section-panel {{
        background: var(--panel);
        border: 1px solid rgba(213, 199, 179, 0.7);
        border-radius: var(--radius);
        box-shadow: var(--shadow);
      }}

      .hero-card {{
        background: rgba(255, 250, 242, 0.13);
        border-color: rgba(255, 250, 242, 0.18);
        padding: 16px 18px;
      }}

      .hero-card .label {{
        display: block;
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: rgba(248, 251, 250, 0.76);
      }}

      .hero-card .value {{
        display: block;
        margin-top: 8px;
        font-size: 1.8rem;
        font-weight: 700;
      }}

      section {{
        margin-top: 28px;
      }}

      h2 {{
        margin: 0 0 14px;
        font-family: "IBM Plex Serif", Georgia, serif;
        font-size: 1.45rem;
      }}

      .metric-card,
      .org-card,
      .section-panel {{
        padding: 20px;
      }}

      .metric-card h3,
      .org-card h3 {{
        margin: 0;
        font-size: 0.98rem;
        color: var(--muted);
      }}

      .metric-value {{
        margin: 10px 0 0;
        font-size: 2rem;
        font-weight: 700;
      }}

      .org-card p,
      .section-panel p {{
        margin: 8px 0 0;
        color: var(--muted);
        line-height: 1.55;
      }}

      .detail-list {{
        margin: 16px 0 0;
        padding: 0;
        list-style: none;
        display: grid;
        gap: 10px;
      }}

      .detail-list li {{
        padding: 10px 12px;
        background: var(--panel-strong);
        border-radius: 12px;
        font-size: 0.95rem;
      }}

      .detail-label {{
        font-weight: 600;
        color: var(--ink);
      }}

      .table-panel {{
        overflow: hidden;
      }}

      table {{
        width: 100%;
        border-collapse: collapse;
      }}

      thead {{
        background: #e9dfcf;
      }}

      th,
      td {{
        padding: 14px 16px;
        text-align: left;
        vertical-align: top;
        border-bottom: 1px solid var(--line);
        font-size: 0.95rem;
      }}

      th {{
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--muted);
      }}

      tbody tr:nth-child(even) {{
        background: rgba(241, 229, 210, 0.35);
      }}

      .pill {{
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
      }}

      .pill-high,
      .pill-immediate {{
        background: var(--risk-soft);
        color: var(--risk);
      }}

      .pill-planned {{
        background: var(--warn-soft);
        color: var(--warn);
      }}

      .pill-monitor {{
        background: var(--accent-soft);
        color: var(--accent);
      }}

      .evidence,
      .mapping {{
        margin: 0;
        padding-left: 18px;
      }}

      .footnote {{
        margin-top: 22px;
        color: var(--muted);
        font-size: 0.92rem;
      }}

      @media (max-width: 860px) {{
        th:nth-child(4),
        td:nth-child(4),
        th:nth-child(9),
        td:nth-child(9) {{
          display: none;
        }}
      }}

      @media (max-width: 640px) {{
        main {{
          padding: 18px 14px 42px;
        }}

        .hero {{
          padding: 22px;
        }}

        th:nth-child(3),
        td:nth-child(3),
        th:nth-child(6),
        td:nth-child(6),
        th:nth-child(9),
        td:nth-child(9) {{
          display: none;
        }}
      }}
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <h1>CRIS-SME Risk Intelligence Report</h1>
        <p>{summary}</p>
        <div class="hero-grid">
          <div class="hero-card">
            <span class="label">Overall Risk</span>
            <span class="value">{overall_risk_score:.2f}/100</span>
          </div>
          <div class="hero-card">
            <span class="label">Profiles Evaluated</span>
            <span class="value">{int(evaluation_context.get("evaluated_profiles", 0))}</span>
          </div>
          <div class="hero-card">
            <span class="label">Generated Findings</span>
            <span class="value">{int(evaluation_context.get("generated_findings", 0))}</span>
          </div>
          <div class="hero-card">
            <span class="label">Non-Compliant</span>
            <span class="value">{int(evaluation_context.get("non_compliant_findings", 0))}</span>
          </div>
        </div>
      </section>

      <section class="section-panel">
        <h2>Executive Summary</h2>
        <p>{executive_summary}</p>
      </section>

      <section>
        <h2>Category Scores</h2>
        <div class="metric-grid">{category_cards}</div>
      </section>

      <section>
        <h2>Collection Provenance</h2>
        <div class="org-grid">{organization_cards}</div>
      </section>

      <section class="section-panel">
        <h2>Run Comparison</h2>
        {comparison_card}
      </section>

      <section class="section-panel">
        <h2>UK Regulatory Mapping</h2>
        {uk_regulatory_card}
      </section>

      <section class="section-panel">
        <h2>Budget-Aware Remediation</h2>
        {remediation_card}
      </section>

      <section class="section-panel">
        <h2>Plain-Language Narrator</h2>
        {narrator_card}
      </section>

      <section>
        <h2>Prioritized Risks</h2>
        <div class="table-panel">
          <table>
            <thead>
              <tr>
                <th>Control</th>
                <th>Category</th>
                <th>Severity</th>
                <th>Priority</th>
                <th>Score</th>
                <th>Organization</th>
                <th>Evidence</th>
                <th>Remediation</th>
                <th>Mappings</th>
              </tr>
            </thead>
            <tbody>
              {prioritized_rows}
            </tbody>
          </table>
        </div>
        <p class="footnote">
          This report uses the deterministic CRIS-SME scoring model and preserves collection provenance
          so reviewers can distinguish live cloud evidence from mock or synthetic posture inputs.
        </p>
      </section>
    </main>
  </body>
</html>
"""


def write_html_report(html: str, output_path: str | Path) -> Path:
    """Write an HTML report to disk and return the resolved output path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path


def _build_organization_card(organization: dict[str, object]) -> str:
    """Build an organization-level provenance card for the HTML report."""
    collection_details = organization.get("collection_details", {})
    if not isinstance(collection_details, dict):
        collection_details = {}

    evidence_counts = collection_details.get("evidence_counts", {})
    if not isinstance(evidence_counts, dict):
        evidence_counts = {}

    mode_items = [
        ("Source", collection_details.get("profile_source")),
        ("Network", collection_details.get("network_collection_mode")),
        ("Data", collection_details.get("data_collection_mode")),
        ("Monitoring", collection_details.get("monitoring_collection_mode")),
        ("Compute", collection_details.get("compute_collection_mode")),
        ("Governance", collection_details.get("governance_collection_mode")),
    ]
    evidence_items = [
        (key.replace("_", " "), value) for key, value in evidence_counts.items()
    ]

    detail_markup = "".join(
        f"<li><span class=\"detail-label\">{escape(str(label))}:</span> {escape(str(value))}</li>"
        for label, value in [*mode_items, *evidence_items]
        if value not in (None, "", {})
    )

    note = collection_details.get("note")
    note_markup = (
        f"<p>{escape(str(note))}</p>"
        if note not in (None, "")
        else ""
    )

    return f"""
    <article class="org-card">
      <h3>{escape(str(organization.get("organization_name", "Unknown organization")))}</h3>
      <p>{escape(str(organization.get("provider", "unknown")))} | {escape(str(organization.get("sector", "unknown sector")))}</p>
      <ul class="detail-list">{detail_markup}</ul>
      {note_markup}
    </article>
    """


def _build_risk_row(risk: dict[str, object]) -> str:
    """Build a prioritized-risk row for the HTML report table."""
    evidence_items = risk.get("evidence", [])
    if not isinstance(evidence_items, list):
        evidence_items = []

    mapping_items = risk.get("mapping", [])
    if not isinstance(mapping_items, list):
        mapping_items = []
    remediation_summary = str(risk.get("remediation_summary", "")).strip()
    remediation_cost_tier = risk.get("remediation_cost_tier")
    remediation_value_score = risk.get("remediation_value_score")
    budget_fit_profiles = risk.get("budget_fit_profiles", [])
    if not isinstance(budget_fit_profiles, list):
        budget_fit_profiles = []

    priority = str(risk.get("priority", "Monitor"))
    priority_class = f"pill-{priority.lower()}"

    evidence_markup = "".join(
        f"<li>{escape(str(item))}</li>" for item in evidence_items
    ) or "<li>No evidence recorded</li>"
    mapping_markup = "".join(
        f"<li>{escape(str(item))}</li>" for item in mapping_items
    ) or "<li>No mapping recorded</li>"
    remediation_markup = escape(remediation_summary or "No remediation guidance recorded")
    if remediation_cost_tier:
        remediation_markup += (
            f"<br /><span class=\"pill pill-monitor\">"
            f"{escape(str(remediation_cost_tier))}</span>"
        )
    if remediation_value_score is not None:
        remediation_markup += f"<br />Value score: {float(remediation_value_score):.2f}"
    if budget_fit_profiles:
        remediation_markup += (
            "<br />Budget fits: "
            f"{escape(', '.join(str(item) for item in budget_fit_profiles))}"
        )

    return f"""
    <tr>
      <td><strong>{escape(str(risk.get("control_id", "N/A")))}</strong><br />{escape(str(risk.get("title", "")))}</td>
      <td>{escape(str(risk.get("category", "Unknown")))}</td>
      <td>{escape(str(risk.get("severity", "Unknown")))}</td>
      <td><span class="pill {priority_class}">{escape(priority)}</span></td>
      <td>{float(risk.get("score", 0.0)):.2f}</td>
      <td>{escape(str(risk.get("organization", "Unknown organization")))}</td>
      <td><ul class="evidence">{evidence_markup}</ul></td>
      <td>{remediation_markup}</td>
      <td><ul class="mapping">{mapping_markup}</ul></td>
    </tr>
    """


def _build_history_comparison_card(history_comparison: object) -> str:
    """Build compact HTML for archived-run comparison metadata."""
    if not isinstance(history_comparison, dict):
        return "<p>No archived comparison data is available yet.</p>"

    rows: list[tuple[str, object]] = [
        ("History count", history_comparison.get("history_count")),
        ("Current collector", history_comparison.get("current_collector_mode")),
        ("Previous collector", history_comparison.get("previous_collector_mode")),
        ("Previous distinct collector", history_comparison.get("previous_distinct_mode")),
        ("Overall risk delta", history_comparison.get("overall_risk_delta")),
        (
            "Overall risk delta vs distinct mode",
            history_comparison.get("overall_risk_delta_vs_distinct_mode"),
        ),
        (
            "Non-compliant findings delta",
            history_comparison.get("non_compliant_findings_delta"),
        ),
        ("Latest run", history_comparison.get("latest_generated_at")),
        ("Previous run", history_comparison.get("previous_generated_at")),
        (
            "Previous distinct run",
            history_comparison.get("previous_distinct_generated_at"),
        ),
    ]

    category_deltas = history_comparison.get("category_score_deltas", {})
    if isinstance(category_deltas, dict):
        for category, delta in category_deltas.items():
            rows.append((f"{category} delta", delta))

    detail_markup = "".join(
        f"<li><span class=\"detail-label\">{escape(str(label))}:</span> {escape(str(value))}</li>"
        for label, value in rows
        if value not in (None, "", {})
    )
    return f"<ul class=\"detail-list\">{detail_markup}</ul>"


def _build_uk_regulatory_card(compliance: object) -> str:
    """Build a compact UK-focused compliance summary card for HTML reports."""
    if not isinstance(compliance, dict):
        return "<p>No compliance summary is available yet.</p>"

    uk_profile = compliance.get("uk_sme_profile", {})
    if not isinstance(uk_profile, dict):
        return "<p>No UK SME regulatory summary is available yet.</p>"

    rows: list[tuple[str, object]] = [
        ("Profile", uk_profile.get("profile_name")),
        ("Mapped controls", uk_profile.get("mapped_control_count")),
        ("Mapped non-compliant findings", uk_profile.get("mapped_finding_count")),
        ("Frameworks covered", ", ".join(uk_profile.get("frameworks_covered", []))),
    ]

    findings_by_framework = uk_profile.get("findings_by_framework", {})
    if isinstance(findings_by_framework, dict):
        for framework, count in findings_by_framework.items():
            rows.append((f"{framework} mapped findings", count))

    detail_markup = "".join(
        f"<li><span class=\"detail-label\">{escape(str(label))}:</span> {escape(str(value))}</li>"
        for label, value in rows
        if value not in (None, "", {})
    )
    if not detail_markup:
        return "<p>No UK SME regulatory mappings were identified for this report.</p>"
    return f"<ul class=\"detail-list\">{detail_markup}</ul>"


def _build_budget_remediation_card(remediation: object) -> str:
    """Build compact HTML for SME budget-aware remediation planning."""
    if not isinstance(remediation, dict):
        return "<p>No budget-aware remediation plan is available yet.</p>"

    budget_profiles = remediation.get("budget_profiles", [])
    if not isinstance(budget_profiles, list) or not budget_profiles:
        return "<p>No budget-aware remediation plan is available yet.</p>"

    sections: list[str] = []
    for profile in budget_profiles:
        if not isinstance(profile, dict):
            continue
        actions = profile.get("recommended_actions", [])
        if not isinstance(actions, list):
            actions = []

        action_markup = "".join(
            (
                "<li>"
                f"<span class=\"detail-label\">{escape(str(action.get('control_id', '')))}:</span> "
                f"{escape(str(action.get('title', '')))} "
                f"({float(action.get('score', 0.0)):.2f} risk, "
                f"value {float(action.get('remediation_value_score', 0.0)):.2f})"
                "</li>"
            )
            for action in actions[:5]
            if isinstance(action, dict)
        ) or "<li>No actions fit this budget profile.</li>"

        sections.append(
            f"""
            <article class="org-card">
              <h3>{escape(str(profile.get("label", "Budget profile")))}</h3>
              <p>{escape(str(profile.get("description", "")))}</p>
              <ul class="detail-list">
                <li><span class="detail-label">Budget cap:</span> GBP {escape(str(profile.get("max_monthly_cost_gbp", 0)))}</li>
                <li><span class="detail-label">Allowed tiers:</span> {escape(", ".join(profile.get("allowed_cost_tiers", [])))}</li>
                <li><span class="detail-label">Recommended actions:</span> {escape(str(profile.get("total_recommended", 0)))}</li>
                <li><span class="detail-label">Cumulative risk score:</span> {escape(str(profile.get("cumulative_risk_score", 0.0)))}</li>
                <li><span class="detail-label">Average value score:</span> {escape(str(profile.get("average_value_score", 0.0)))}</li>
                {action_markup}
              </ul>
            </article>
            """
        )

    return "".join(sections) if sections else "<p>No budget-aware remediation plan is available yet.</p>"


def _build_narrator_card(narrative: object) -> str:
    """Build compact HTML for optional LLM-generated plain-language outputs."""
    if not isinstance(narrative, dict) or not narrative:
        return "<p>The plain-language narrator is not enabled for this report.</p>"

    rows: list[tuple[str, object]] = [
        ("Provider", narrative.get("provider")),
        ("Model", narrative.get("model")),
        ("Generated at", narrative.get("generated_at")),
    ]

    detail_markup = "".join(
        f"<li><span class=\"detail-label\">{escape(str(label))}:</span> {escape(str(value))}</li>"
        for label, value in rows
        if value not in (None, "", {})
    )

    executive = escape(str(narrative.get("executive_narrative", "")))
    owner_plan = escape(str(narrative.get("owner_action_plan", "")))
    board_brief = escape(str(narrative.get("board_brief", "")))
    disclaimer = escape(str(narrative.get("disclaimer", "")))

    return f"""
    <ul class="detail-list">{detail_markup}</ul>
    <p><span class="detail-label">Executive narrative:</span> {executive}</p>
    <p><span class="detail-label">Owner action plan:</span> {owner_plan}</p>
    <p><span class="detail-label">Board brief:</span> {board_brief}</p>
    <p><span class="detail-label">Disclaimer:</span> {disclaimer}</p>
    """
