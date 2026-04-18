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
    confidence_calibration = report.get("confidence_calibration", {})
    native_validation = report.get("native_validation", {})
    organizations = report.get("organizations", [])
    prioritized_risks = report.get("prioritized_risks", [])
    history_comparison = report.get("history_comparison", {})
    compliance = report.get("compliance", {})
    budget_aware_remediation = report.get("budget_aware_remediation", {})
    action_plan_30_day = report.get("action_plan_30_day", {})
    cyber_insurance_evidence = report.get("cyber_insurance_evidence", {})
    benchmark_comparison = report.get("benchmark_comparison", {})
    cyber_essentials_readiness = report.get("cyber_essentials_readiness", {})
    executive_pack = report.get("executive_pack", {})
    plain_language_narrative = report.get("plain_language_narrative", {})

    if not isinstance(evaluation_context, dict):
        evaluation_context = {}
    if not isinstance(category_scores, dict):
        category_scores = {}
    if not isinstance(prioritized_risks, list):
        prioritized_risks = []
    if not isinstance(organizations, list):
        organizations = []

    risk_angle = max(0.0, min(100.0, overall_risk_score)) * 3.6
    risk_status = _risk_band_label(overall_risk_score)
    risk_status_class = _risk_band_class(overall_risk_score)

    category_cards = _build_category_cards(category_scores)
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
    confidence_card = _build_confidence_calibration_card(confidence_calibration)
    native_validation_card = _build_native_validation_card(native_validation)
    uk_regulatory_card = _build_uk_regulatory_card(compliance)
    remediation_card = _build_budget_remediation_card(budget_aware_remediation)
    action_plan_card = _build_action_plan_card(action_plan_30_day)
    insurance_card = _build_cyber_insurance_card(cyber_insurance_evidence)
    benchmark_card = _build_benchmark_card(benchmark_comparison)
    uk_readiness_card = _build_uk_readiness_card(cyber_essentials_readiness)
    executive_pack_card = _build_executive_pack_card(executive_pack)
    narrator_card = _build_narrator_card(plain_language_narrative)
    top_actions_card = _build_top_actions_panel(
        prioritized_risks=prioritized_risks,
        remediation=budget_aware_remediation,
        action_plan=action_plan_30_day,
    )

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>CRIS-SME Risk Report</title>
    <style>
      :root {{
        --bg: #eef4f7;
        --bg-soft: #f8fbfd;
        --panel: rgba(255, 255, 255, 0.88);
        --panel-strong: #f4f8fb;
        --ink: #10212b;
        --muted: #5a6c78;
        --line: rgba(73, 100, 115, 0.16);
        --navy: #102230;
        --navy-soft: #183547;
        --accent: #007a78;
        --accent-soft: rgba(0, 122, 120, 0.12);
        --sky: #417dff;
        --sky-soft: rgba(65, 125, 255, 0.12);
        --risk: #c44536;
        --risk-soft: rgba(196, 69, 54, 0.14);
        --warn: #b97807;
        --warn-soft: rgba(185, 120, 7, 0.14);
        --ok: #2b8761;
        --ok-soft: rgba(43, 135, 97, 0.14);
        --shadow: 0 24px 64px rgba(16, 33, 43, 0.12);
        --radius: 24px;
        --radius-tight: 16px;
      }}

      * {{
        box-sizing: border-box;
      }}

      html {{
        scroll-behavior: smooth;
      }}

      body {{
        margin: 0;
        font-family: "IBM Plex Sans", "Aptos", "Segoe UI", sans-serif;
        color: var(--ink);
        background:
          radial-gradient(circle at top left, rgba(0, 122, 120, 0.13), transparent 28%),
          radial-gradient(circle at 85% 10%, rgba(65, 125, 255, 0.14), transparent 26%),
          linear-gradient(180deg, #f8fbfd 0%, var(--bg) 52%, #ecf3f7 100%);
      }}

      body::before {{
        content: "";
        position: fixed;
        inset: 0;
        background-image:
          linear-gradient(rgba(16, 33, 43, 0.025) 1px, transparent 1px),
          linear-gradient(90deg, rgba(16, 33, 43, 0.025) 1px, transparent 1px);
        background-size: 36px 36px;
        pointer-events: none;
        mask-image: radial-gradient(circle at center, black, transparent 78%);
      }}

      .page-shell {{
        position: relative;
        max-width: 1440px;
        margin: 0 auto;
        padding: 28px 18px 64px;
        display: grid;
        grid-template-columns: 252px minmax(0, 1fr);
        gap: 22px;
      }}

      .nav-rail {{
        position: sticky;
        top: 18px;
        align-self: start;
        padding: 22px;
        background: linear-gradient(180deg, rgba(16, 34, 48, 0.98), rgba(24, 53, 71, 0.96));
        color: #f2f8fb;
        border-radius: 30px;
        box-shadow: var(--shadow);
        overflow: hidden;
      }}

      .nav-rail::after {{
        content: "";
        position: absolute;
        inset: auto -34% -38% auto;
        width: 240px;
        height: 240px;
        background: radial-gradient(circle, rgba(65, 125, 255, 0.24), transparent 68%);
        pointer-events: none;
      }}

      .nav-kicker {{
        margin: 0 0 8px;
        font-size: 0.74rem;
        font-weight: 600;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: rgba(242, 248, 251, 0.6);
      }}

      .nav-title {{
        margin: 0;
        font-family: "IBM Plex Serif", Georgia, serif;
        font-size: 1.55rem;
        line-height: 1.1;
      }}

      .nav-summary {{
        margin: 12px 0 0;
        color: rgba(242, 248, 251, 0.8);
        line-height: 1.58;
        font-size: 0.94rem;
      }}

      .nav-score {{
        margin-top: 18px;
        padding: 14px 16px;
        border-radius: 18px;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.08);
      }}

      .nav-score strong {{
        display: block;
        font-size: 2rem;
        line-height: 1;
      }}

      .nav-score span {{
        display: block;
        margin-top: 6px;
        color: rgba(242, 248, 251, 0.72);
        font-size: 0.9rem;
      }}

      .nav-links {{
        margin: 20px 0 0;
        padding: 0;
        list-style: none;
        display: grid;
        gap: 8px;
      }}

      .nav-links a {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        padding: 10px 12px;
        border-radius: 14px;
        color: #f2f8fb;
        text-decoration: none;
        background: rgba(255, 255, 255, 0.04);
        transition: transform 0.2s ease, background 0.2s ease;
      }}

      .nav-links a:hover {{
        transform: translateX(3px);
        background: rgba(255, 255, 255, 0.1);
      }}

      .nav-links a span {{
        color: rgba(242, 248, 251, 0.62);
        font-size: 0.8rem;
      }}

      main {{
        min-width: 0;
      }}

      .report-section {{
        margin-top: 26px;
      }}

      .hero {{
        position: relative;
        overflow: hidden;
        background:
          radial-gradient(circle at 12% 18%, rgba(46, 212, 191, 0.24), transparent 24%),
          radial-gradient(circle at 88% 24%, rgba(115, 163, 255, 0.28), transparent 26%),
          linear-gradient(140deg, rgba(16, 34, 48, 0.98), rgba(22, 50, 68, 0.95) 58%, rgba(26, 63, 79, 0.93));
        color: #f2f8fb;
        border-radius: 32px;
        padding: 30px;
        box-shadow: var(--shadow);
      }}

      .hero-shell {{
        display: grid;
        grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.95fr);
        gap: 22px;
        align-items: start;
      }}

      .eyebrow {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 7px 11px;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.08);
        color: rgba(242, 248, 251, 0.86);
        font-size: 0.76rem;
        font-weight: 600;
        letter-spacing: 0.12em;
        text-transform: uppercase;
      }}

      .hero h1 {{
        margin: 18px 0 10px;
        font-family: "IBM Plex Serif", Georgia, serif;
        font-size: clamp(2.2rem, 4.2vw, 4rem);
        line-height: 0.98;
        max-width: 12ch;
      }}

      .hero p {{
        margin: 0;
        max-width: 72ch;
        font-size: 1.02rem;
        line-height: 1.72;
        color: rgba(242, 248, 251, 0.82);
      }}

      .hero-meta,
      .metric-grid,
      .org-grid,
      .summary-grid,
      .bento-grid {{
        display: grid;
        gap: 16px;
      }}

      .hero-meta {{
        margin-top: 24px;
        grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      }}

      .metric-grid,
      .org-grid {{
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      }}

      .summary-grid {{
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      }}

      .bento-grid {{
        grid-template-columns: minmax(0, 1.08fr) minmax(300px, 0.92fr);
      }}

      .hero-side {{
        display: grid;
        gap: 16px;
      }}

      .score-card,
      .top-actions {{
        padding: 22px;
        border-radius: 26px;
        background: rgba(255, 255, 255, 0.09);
        border: 1px solid rgba(255, 255, 255, 0.1);
      }}

      .hero-card,
      .metric-card,
      .org-card,
      .table-panel,
      .section-panel {{
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: var(--radius);
        box-shadow: var(--shadow);
        backdrop-filter: blur(12px);
      }}

      .hero-card,
      .metric-card,
      .org-card,
      .section-panel {{
        padding: 20px;
      }}

      .hero-card {{
        background: rgba(255, 255, 255, 0.08);
        border-color: rgba(255, 255, 255, 0.1);
      }}

      .hero-card .label {{
        display: block;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: rgba(242, 248, 251, 0.66);
      }}

      .hero-card .value {{
        display: block;
        margin-top: 8px;
        font-size: 1.95rem;
        font-weight: 700;
      }}

      .hero-card .subvalue {{
        display: block;
        margin-top: 8px;
        color: rgba(242, 248, 251, 0.74);
        font-size: 0.92rem;
        line-height: 1.45;
      }}

      .score-card h2,
      .top-actions h2 {{
        margin: 0 0 10px;
        font-family: "IBM Plex Sans", "Aptos", "Segoe UI", sans-serif;
        font-size: 1.05rem;
        color: #f2f8fb;
      }}

      .score-dial-shell {{
        margin-top: 18px;
        display: flex;
        align-items: center;
        gap: 18px;
      }}

      .score-dial-wrap {{
        position: relative;
        width: 132px;
        height: 132px;
      }}

      .score-dial {{
        width: 132px;
        height: 132px;
        border-radius: 50%;
        display: grid;
        place-items: center;
        background:
          conic-gradient(
            var(--risk) 0deg {risk_angle:.2f}deg,
            rgba(255, 255, 255, 0.12) {risk_angle:.2f}deg 360deg
          );
      }}

      .score-dial::before {{
        content: "";
        width: 94px;
        height: 94px;
        border-radius: 50%;
        background: rgba(16, 34, 48, 0.98);
        box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.06);
      }}

      .score-dial-value {{
        position: absolute;
        inset: 0;
        display: grid;
        place-items: center;
        text-align: center;
      }}

      .score-dial-value strong {{
        display: block;
        font-size: 2rem;
        line-height: 1;
      }}

      .score-dial-value span {{
        display: block;
        margin-top: 6px;
        font-size: 0.78rem;
        color: rgba(242, 248, 251, 0.66);
        text-transform: uppercase;
        letter-spacing: 0.1em;
      }}

      .score-copy p {{
        margin: 4px 0 0;
        font-size: 0.95rem;
        line-height: 1.55;
      }}

      .score-status,
      .pill {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 10px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
      }}

      .score-status {{
        margin-top: 10px;
      }}

      .score-status-critical,
      .pill-high,
      .pill-immediate,
      .pill-status_gap {{
        background: var(--risk-soft);
        color: var(--risk);
      }}

      .score-status-elevated,
      .pill-planned,
      .pill-status_partial {{
        background: var(--warn-soft);
        color: var(--warn);
      }}

      .score-status-managed,
      .pill-monitor,
      .pill-status_ready {{
        background: var(--accent-soft);
        color: var(--accent);
      }}

      .score-status-low,
      .pill-low {{
        background: var(--ok-soft);
        color: var(--ok);
      }}

      .action-list {{
        margin: 0;
        padding: 0;
        list-style: none;
        display: grid;
        gap: 10px;
      }}

      .action-list li {{
        padding: 12px 13px;
        border-radius: 16px;
        background: rgba(255, 255, 255, 0.08);
      }}

      .action-list strong {{
        display: block;
        font-size: 0.95rem;
      }}

      .action-list span {{
        display: block;
        margin-top: 4px;
        color: rgba(242, 248, 251, 0.74);
        font-size: 0.9rem;
        line-height: 1.45;
      }}

      .section-heading {{
        display: flex;
        align-items: end;
        justify-content: space-between;
        gap: 18px;
        margin-bottom: 16px;
      }}

      .section-heading h2 {{
        margin: 0;
        font-family: "IBM Plex Serif", Georgia, serif;
        font-size: 1.55rem;
      }}

      .section-heading p {{
        margin: 8px 0 0;
        max-width: 72ch;
        color: var(--muted);
        line-height: 1.62;
      }}

      .section-kicker {{
        display: inline-block;
        margin-bottom: 8px;
        font-size: 0.76rem;
        font-weight: 600;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: var(--accent);
      }}

      .section-anchor {{
        color: var(--muted);
        text-decoration: none;
        font-size: 0.88rem;
        white-space: nowrap;
      }}

      .section-anchor:hover {{
        color: var(--ink);
      }}

      .metric-card {{
        position: relative;
        overflow: hidden;
      }}

      .metric-card::after {{
        content: "";
        position: absolute;
        inset: auto -10% -22% auto;
        width: 120px;
        height: 120px;
        background: radial-gradient(circle, rgba(65, 125, 255, 0.12), transparent 68%);
        pointer-events: none;
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

      .metric-bar {{
        margin-top: 16px;
        width: 100%;
        height: 10px;
        border-radius: 999px;
        background: rgba(16, 33, 43, 0.08);
        overflow: hidden;
      }}

      .metric-bar span {{
        display: block;
        height: 100%;
        border-radius: inherit;
        background: linear-gradient(90deg, var(--accent), var(--sky));
      }}

      .metric-foot {{
        margin-top: 10px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
        color: var(--muted);
        font-size: 0.88rem;
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
        border-radius: 24px;
      }}

      table {{
        width: 100%;
        border-collapse: collapse;
      }}

      thead {{
        background: linear-gradient(90deg, rgba(16, 34, 48, 0.98), rgba(24, 53, 71, 0.96));
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
        color: rgba(242, 248, 251, 0.74);
      }}

      tbody tr:nth-child(even) {{
        background: rgba(244, 248, 251, 0.72);
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

      @media (max-width: 1120px) {{
        .page-shell {{
          grid-template-columns: 1fr;
        }}

        .nav-rail {{
          position: static;
        }}

        .hero-shell,
        .bento-grid {{
          grid-template-columns: 1fr;
        }}
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
        .page-shell {{
          padding: 16px 12px 42px;
        }}

        .hero {{
          padding: 22px;
        }}

        .score-dial-shell {{
          flex-direction: column;
          align-items: flex-start;
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
    <div class="page-shell">
      <aside class="nav-rail">
        <p class="nav-kicker">CRIS-SME</p>
        <h2 class="nav-title">UK SME cloud risk reporting with product-grade clarity</h2>
        <p class="nav-summary">
          This report is designed around the strongest modern posture-report patterns:
          security at a glance, top actions, longitudinal context, and evidence-backed
          explanation for non-enterprise teams.
        </p>
        <div class="nav-score">
          <strong>{overall_risk_score:.2f}</strong>
          <span>{escape(risk_status)} overall risk | {int(evaluation_context.get("non_compliant_findings", 0))} non-compliant findings</span>
        </div>
        <ul class="nav-links">
          <li><a href="#overview">Overview <span>01</span></a></li>
          <li><a href="#posture">Posture & actions <span>02</span></a></li>
          <li><a href="#evidence">Evidence & provenance <span>03</span></a></li>
          <li><a href="#assurance">Assurance & benchmark <span>04</span></a></li>
          <li><a href="#uk">UK obligations <span>05</span></a></li>
          <li><a href="#risks">Prioritized risks <span>06</span></a></li>
        </ul>
      </aside>

      <main>
        <section id="overview" class="hero report-section">
          <div class="hero-shell">
            <div>
              <span class="eyebrow">Cloud Risk Intelligence Report</span>
              <h1>CRIS-SME Risk Intelligence Report</h1>
              <p>{summary}</p>
              <div class="hero-meta">
                <div class="hero-card">
                  <span class="label">Profiles Evaluated</span>
                  <span class="value">{int(evaluation_context.get("evaluated_profiles", 0))}</span>
                  <span class="subvalue">Tenant or synthetic posture profiles assessed in this run.</span>
                </div>
                <div class="hero-card">
                  <span class="label">Generated Findings</span>
                  <span class="value">{int(evaluation_context.get("generated_findings", 0))}</span>
                  <span class="subvalue">Deterministic control outcomes converted into scored findings.</span>
                </div>
                <div class="hero-card">
                  <span class="label">Non-Compliant</span>
                  <span class="value">{int(evaluation_context.get("non_compliant_findings", 0))}</span>
                  <span class="subvalue">Issues currently driving the SME risk posture upward.</span>
                </div>
              </div>
            </div>

            <div class="hero-side">
              <div class="score-card">
                <h2>Security at a glance</h2>
                <div class="score-dial-shell">
                  <div class="score-dial-wrap">
                    <div class="score-dial"></div>
                    <div class="score-dial-value">
                      <div>
                        <strong>{overall_risk_score:.2f}</strong>
                        <span>Risk / 100</span>
                      </div>
                    </div>
                  </div>
                  <div class="score-copy">
                    <p>CRIS-SME keeps the model explainable, evidence-based, and transparent enough for research reviewers, security teams, and SME decision-makers to read from the same artifact.</p>
                    <div class="score-status {risk_status_class}">{escape(risk_status)}</div>
                  </div>
                </div>
              </div>

              <div class="top-actions">
                <h2>Top actions</h2>
                {top_actions_card}
              </div>
            </div>
          </div>
        </section>

        <section class="report-section">
          <div class="bento-grid">
            <article class="section-panel">
              <div class="section-heading">
                <div>
                  <span class="section-kicker">Executive Summary</span>
                  <h2>What matters most right now</h2>
                  <p>{executive_summary}</p>
                </div>
              </div>
            </article>

            <article class="section-panel">
              <div class="section-heading">
                <div>
                  <span class="section-kicker">Board Snapshot</span>
                  <h2>Fast-reading decision context</h2>
                  <p>The report is structured to feel closer to the best posture platforms: quick orientation first, then action paths, then evidence and compliance detail.</p>
                </div>
              </div>
              <div class="summary-grid">
                <div class="metric-card">
                  <h3>Calibration controls</h3>
                  <p class="metric-value">{escape(str(confidence_calibration.get("controls_with_calibration", 0)))}</p>
                </div>
                <div class="metric-card">
                  <h3>Native mappings</h3>
                  <p class="metric-value">{escape(str(native_validation.get("controls_mapped", 0)))}</p>
                </div>
                <div class="metric-card">
                  <h3>Benchmark status</h3>
                  <p class="metric-value" style="font-size:1.3rem;">{escape(str(benchmark_comparison.get("status", "unknown")).replace("_", " "))}</p>
                </div>
              </div>
            </article>
          </div>
        </section>

        <section id="posture" class="report-section">
          <div class="section-heading">
            <div>
              <span class="section-kicker">Posture & Priority</span>
              <h2>Category Scores</h2>
              <p>Borrowing from better market experiences, the emphasis here is on readability: where risk clusters, how much it matters, and which domains need attention first.</p>
            </div>
            <a class="section-anchor" href="#overview">Back to top</a>
          </div>
          <div class="metric-grid">{category_cards}</div>
        </section>

        <section id="evidence" class="report-section">
          <div class="section-heading">
            <div>
              <span class="section-kicker">Collection Provenance</span>
              <h2>Collection Provenance</h2>
              <p>Strong reports separate conclusions from the telemetry that created them. This section keeps collection mode and evidence counts visible, not hidden.</p>
            </div>
            <a class="section-anchor" href="#overview">Back to top</a>
          </div>
          <div class="org-grid">{organization_cards}</div>
        </section>

        <section id="assurance" class="section-panel report-section">
          <div class="section-heading">
            <div>
              <span class="section-kicker">Model Assurance</span>
              <h2>Confidence Calibration</h2>
              <p>Confidence is surfaced as part of the scoring story, so the report reads as measured and defensible rather than opaque.</p>
            </div>
            <a class="section-anchor" href="#overview">Back to top</a>
          </div>
          {confidence_card}
        </section>

        <section class="section-panel report-section">
          <div class="section-heading">
            <div>
              <span class="section-kicker">Native Baseline</span>
              <h2>Native Recommendation Validation</h2>
              <p>Alignment against Microsoft Defender for Cloud adds external grounding and helps position CRIS-SME as an explainable overlay, not a disconnected scoring toy.</p>
            </div>
          </div>
          {native_validation_card}
        </section>

        <section class="section-panel report-section">
          <div class="section-heading">
            <div>
              <span class="section-kicker">Longitudinal Tracking</span>
              <h2>Run Comparison</h2>
              <p>Modern governance tools stand out when they show movement over time. This section highlights posture drift and progress, not just a one-off scan.</p>
            </div>
          </div>
          {comparison_card}
        </section>

        <section class="section-panel report-section">
          <div class="section-heading">
            <div>
              <span class="section-kicker">Budget-Aware Planning</span>
              <h2>Budget-Aware Remediation</h2>
              <p>SMEs need action sequences constrained by cost, not just a louder list of severe issues. The presentation now treats this as a core product capability.</p>
            </div>
          </div>
          {remediation_card}
        </section>

        <section class="section-panel report-section">
          <div class="section-heading">
            <div>
              <span class="section-kicker">Operational Delivery</span>
              <h2>30-Day SME Action Plan</h2>
              <p>The action plan is formatted as a practical execution layer so the report can move directly into operational follow-up.</p>
            </div>
          </div>
          {action_plan_card}
        </section>

        <section class="section-panel report-section">
          <div class="section-heading">
            <div>
              <span class="section-kicker">Insurance Readiness</span>
              <h2>Cyber Insurance Evidence Pack</h2>
              <p>Instead of looking like an engineer-only export, the report now carries a clearer insurer- and stakeholder-facing posture summary.</p>
            </div>
          </div>
          {insurance_card}
        </section>

        <section class="section-panel report-section">
          <div class="section-heading">
            <div>
              <span class="section-kicker">Benchmark Scaffold</span>
              <h2>Benchmark Scaffold</h2>
              <p>Even before the benchmark dataset matures, the report reserves visual space for peer comparison so the product category can evolve cleanly.</p>
            </div>
          </div>
          {benchmark_card}
        </section>

        <section id="uk" class="section-panel report-section">
          <div class="section-heading">
            <div>
              <span class="section-kicker">UK Obligations</span>
              <h2>UK Regulatory Mapping</h2>
              <p>This section keeps Cyber Essentials, UK GDPR, FCA SYSC, and related obligations visible in the same visual language as technical posture.</p>
            </div>
            <a class="section-anchor" href="#overview">Back to top</a>
          </div>
          {uk_regulatory_card}
        </section>

        <section class="section-panel report-section">
          <div class="section-heading">
            <div>
              <span class="section-kicker">Government-Facing Readiness</span>
              <h2>Cyber Essentials Readiness</h2>
              <p>Instead of burying Cyber Essentials in mapping notes, the report treats it as a primary readiness story for UK SMEs.</p>
            </div>
          </div>
          {uk_readiness_card}
        </section>

        <section class="section-panel report-section">
          <div class="section-heading">
            <div>
              <span class="section-kicker">Board Output</span>
              <h2>Executive Pack</h2>
              <p>The executive layer is now visually closer to a board-ready briefing than a raw export, which helps with demos, case studies, and leadership conversations.</p>
            </div>
          </div>
          {executive_pack_card}
        </section>

        <section class="section-panel report-section">
          <div class="section-heading">
            <div>
              <span class="section-kicker">Narration Layer</span>
              <h2>Plain-Language Narrator</h2>
              <p>The optional narrator remains clearly secondary to the deterministic model, preserving trust and explainability.</p>
            </div>
          </div>
          {narrator_card}
        </section>

        <section id="risks" class="report-section">
          <div class="section-heading">
            <div>
              <span class="section-kicker">Risk Register</span>
              <h2>Prioritized Risks</h2>
              <p>This remains the evidence-rich core of the report, but it now sits under clearer context, triage, and action framing so the whole document scans more like a mature security product artifact.</p>
            </div>
            <a class="section-anchor" href="#overview">Back to top</a>
          </div>
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
    </div>
  </body>
</html>
"""


def write_html_report(html: str, output_path: str | Path) -> Path:
    """Write an HTML report to disk and return the resolved output path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path


def _risk_band_label(score: float) -> str:
    """Map a numeric score to a human-readable risk band."""
    if score >= 70:
        return "Critical posture exposure"
    if score >= 45:
        return "Elevated posture exposure"
    if score >= 20:
        return "Managed but material risk"
    return "Relatively contained risk"


def _risk_band_class(score: float) -> str:
    """Map a numeric score to the matching CSS status class."""
    if score >= 70:
        return "score-status-critical"
    if score >= 45:
        return "score-status-elevated"
    if score >= 20:
        return "score-status-managed"
    return "score-status-low"


def _build_category_cards(category_scores: dict[str, object]) -> str:
    """Build category score cards with a more visual posture meter."""
    cards: list[str] = []
    for category, raw_score in category_scores.items():
        score = float(raw_score)
        clamped_score = max(0.0, min(100.0, score))
        cards.append(
            f"""
            <article class="metric-card">
              <h3>{escape(str(category))}</h3>
              <p class="metric-value">{score:.2f}</p>
              <div class="metric-bar"><span style="width: {clamped_score:.2f}%;"></span></div>
              <div class="metric-foot">
                <span>{escape(_risk_band_label(score))}</span>
                <span>{clamped_score:.0f}% of risk scale</span>
              </div>
            </article>
            """
        )
    return "".join(cards)


def _build_top_actions_panel(
    *,
    prioritized_risks: list[object],
    remediation: object,
    action_plan: object,
) -> str:
    """Build a market-style top actions panel for the hero area."""
    actions: list[str] = []
    visible_risks = [
        risk for risk in prioritized_risks[:3] if isinstance(risk, dict)
    ]
    for risk in visible_risks:
        actions.append(
            f"""
            <li>
              <strong>{escape(str(risk.get("control_id", "N/A")))} | {escape(str(risk.get("title", "")))}</strong>
              <span>{escape(str(risk.get("priority", "Monitor")))} priority, {float(risk.get("score", 0.0)):.2f} risk score, {escape(str(risk.get("remediation_cost_tier", "unknown")))} remediation cost.</span>
            </li>
            """
        )

    if isinstance(remediation, dict):
        budget_profiles = remediation.get("budget_profiles", [])
        if isinstance(budget_profiles, list):
            for profile in budget_profiles:
                if not isinstance(profile, dict):
                    continue
                if str(profile.get("profile_id")) == "free_this_week":
                    actions.append(
                        f"""
                        <li>
                          <strong>Free this week</strong>
                          <span>{int(profile.get("total_recommended", 0))} recommended free actions covering {float(profile.get("cumulative_risk_score", 0.0)):.2f} cumulative risk score.</span>
                        </li>
                        """
                    )
                    break

    if isinstance(action_plan, dict):
        phases = action_plan.get("phases", [])
        if isinstance(phases, list) and phases:
            phase = phases[0]
            if isinstance(phase, dict):
                actions.append(
                    f"""
                    <li>
                      <strong>{escape(str(phase.get("label", "Immediate action phase")))}</strong>
                      <span>{escape(str(phase.get("goal", "")))} Total actions: {int(phase.get("total_actions", 0))}.</span>
                    </li>
                    """
                )

    if not actions:
        return "<p>No immediate actions are available yet.</p>"
    return f"<ul class=\"action-list\">{''.join(actions[:4])}</ul>"


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
        ("IAM", collection_details.get("iam_collection_mode")),
        ("Network", collection_details.get("network_collection_mode")),
        ("Data", collection_details.get("data_collection_mode")),
        ("Monitoring", collection_details.get("monitoring_collection_mode")),
        ("Compute", collection_details.get("compute_collection_mode")),
        ("Governance", collection_details.get("governance_collection_mode")),
        ("Identity observability", collection_details.get("identity_observability")),
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
    note_markup = f"<p>{escape(str(note))}</p>" if note not in (None, "") else ""

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
            f"<br /><span class=\"pill pill-monitor\">{escape(str(remediation_cost_tier))}</span>"
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


def _build_confidence_calibration_card(calibration: object) -> str:
    """Build compact HTML for confidence calibration summary data."""
    if not isinstance(calibration, dict):
        return "<p>No confidence calibration summary is available yet.</p>"

    rows: list[tuple[str, object]] = [
        ("Controls with calibration", calibration.get("controls_with_calibration")),
        ("Average observed confidence", calibration.get("average_observed_confidence")),
        ("Average calibrated confidence", calibration.get("average_calibrated_confidence")),
        ("Method summary", calibration.get("method_summary")),
    ]
    status_counts = calibration.get("status_counts", {})
    if isinstance(status_counts, dict):
        for status, count in status_counts.items():
            rows.append((f"{status} controls", count))

    detail_markup = "".join(
        f"<li><span class=\"detail-label\">{escape(str(label))}:</span> {escape(str(value))}</li>"
        for label, value in rows
        if value not in (None, "", {})
    )
    return (
        f"<ul class=\"detail-list\">{detail_markup}</ul>"
        if detail_markup
        else "<p>No confidence calibration summary is available yet.</p>"
    )


def _build_native_validation_card(native_validation: object) -> str:
    """Build compact HTML for Azure-native recommendation comparison."""
    if not isinstance(native_validation, dict):
        return "<p>No native recommendation validation summary is available yet.</p>"

    rows: list[tuple[str, object]] = [
        ("Framework", native_validation.get("framework")),
        ("Controls mapped", native_validation.get("controls_mapped")),
        (
            "Native unhealthy recommendations",
            native_validation.get("native_unhealthy_recommendation_count"),
        ),
        ("Agreement count", native_validation.get("agreement_count")),
        ("CRIS-only count", native_validation.get("cris_only_count")),
        ("Native-only count", native_validation.get("native_only_count")),
        ("Coverage note", native_validation.get("coverage_note")),
    ]
    comparisons = native_validation.get("control_comparisons", [])
    if not isinstance(comparisons, list):
        comparisons = []
    comparison_markup = "".join(
        (
            "<li>"
            f"<span class=\"detail-label\">{escape(str(item.get('control_id', '')))} "
            f"({escape(str(item.get('comparison_status', 'unknown')))}):</span> "
            f"{int(item.get('native_recommendation_count', 0))} native recommendation(s)"
            "</li>"
        )
        for item in comparisons[:8]
        if isinstance(item, dict)
    ) or "<li>No mapped control comparisons are available.</li>"
    detail_markup = "".join(
        f"<li><span class=\"detail-label\">{escape(str(label))}:</span> {escape(str(value))}</li>"
        for label, value in rows
        if value not in (None, "", {})
    )
    return f"<ul class=\"detail-list\">{detail_markup}{comparison_markup}</ul>"


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


def _build_cyber_insurance_card(insurance_pack: object) -> str:
    """Build compact HTML for insurer-facing evidence summaries."""
    if not isinstance(insurance_pack, dict):
        return "<p>No cyber insurance evidence pack is available yet.</p>"

    readiness = insurance_pack.get("readiness_summary", {})
    if not isinstance(readiness, dict):
        readiness = {}

    detail_rows = [
        ("Jurisdiction", insurance_pack.get("jurisdiction")),
        ("Readiness score", readiness.get("readiness_score")),
        ("Questions assessed", readiness.get("question_count")),
        ("Met", readiness.get("met_count")),
        ("Partial", readiness.get("partial_count")),
        ("Not met", readiness.get("not_met_count")),
        ("Unknown", readiness.get("unknown_count")),
    ]
    detail_markup = "".join(
        f"<li><span class=\"detail-label\">{escape(str(label))}:</span> {escape(str(value))}</li>"
        for label, value in detail_rows
        if value not in (None, "", {})
    )

    questions = insurance_pack.get("questions", [])
    if not isinstance(questions, list):
        questions = []
    question_markup = "".join(
        (
            "<li>"
            f"<span class=\"detail-label\">{escape(str(question.get('question_id', 'INS-?')))} - "
            f"{escape(str(question.get('theme', 'Unknown theme')))} "
            f"({escape(str(question.get('status', 'unknown')))}):</span> "
            f"{escape(str(question.get('question', '')))} "
            f"<br />{escape(str(question.get('evidence_statement', '')))}"
            "</li>"
        )
        for question in questions[:6]
        if isinstance(question, dict)
    ) or "<li>No insurance evidence questions were generated.</li>"
    disclaimer = escape(str(insurance_pack.get("disclaimer", "")))
    return (
        f"<ul class=\"detail-list\">{detail_markup}{question_markup}</ul>"
        f"<p>{disclaimer}</p>"
    )


def _build_action_plan_card(action_plan: object) -> str:
    """Build compact HTML for the 30-day SME action plan."""
    if not isinstance(action_plan, dict):
        return "<p>No 30-day action plan is available yet.</p>"

    phases = action_plan.get("phases", [])
    if not isinstance(phases, list) or not phases:
        return "<p>No 30-day action plan is available yet.</p>"

    sections: list[str] = []
    for phase in phases:
        if not isinstance(phase, dict):
            continue
        actions = phase.get("actions", [])
        if not isinstance(actions, list):
            actions = []
        action_markup = "".join(
            (
                "<li>"
                f"<span class=\"detail-label\">{escape(str(action.get('control_id', '')))}:</span> "
                f"{escape(str(action.get('remediation_summary', '')))} "
                f"({float(action.get('score', 0.0)):.2f} risk, {escape(str(action.get('remediation_cost_tier', '')))} cost)"
                "</li>"
            )
            for action in actions[:5]
            if isinstance(action, dict)
        ) or "<li>No actions are scheduled in this phase.</li>"

        sections.append(
            f"""
            <article class="org-card">
              <h3>{escape(str(phase.get("label", "Plan phase")))}</h3>
              <p>{escape(str(phase.get("goal", "")))}</p>
              <ul class="detail-list">
                <li><span class="detail-label">Time window:</span> {escape(str(phase.get("time_window", "")))}</li>
                <li><span class="detail-label">Total actions:</span> {escape(str(phase.get("total_actions", 0)))}</li>
                <li><span class="detail-label">Cumulative risk score:</span> {escape(str(phase.get("cumulative_risk_score", 0.0)))}</li>
                {action_markup}
              </ul>
            </article>
            """
        )
    return "".join(sections) if sections else "<p>No 30-day action plan is available yet.</p>"


def _build_benchmark_card(benchmark_comparison: object) -> str:
    """Build compact HTML for benchmark scaffold status."""
    if not isinstance(benchmark_comparison, dict):
        return "<p>No benchmark comparison summary is available yet.</p>"

    rows = [
        ("Dataset size", benchmark_comparison.get("dataset_size")),
        ("Peer count", benchmark_comparison.get("peer_count")),
        ("Provider", benchmark_comparison.get("provider")),
        ("Collector mode", benchmark_comparison.get("collector_mode")),
        ("Status", benchmark_comparison.get("status")),
        ("Note", benchmark_comparison.get("note")),
        (
            "Peer average overall risk",
            benchmark_comparison.get("peer_average_overall_risk"),
        ),
        (
            "Percentile worse than peers",
            benchmark_comparison.get("percentile_worse_than_peers"),
        ),
    ]
    detail_markup = "".join(
        f"<li><span class=\"detail-label\">{escape(str(label))}:</span> {escape(str(value))}</li>"
        for label, value in rows
        if value not in (None, "", {})
    )
    return (
        f"<ul class=\"detail-list\">{detail_markup}</ul>"
        if detail_markup
        else "<p>No benchmark comparison summary is available yet.</p>"
    )


def _build_uk_readiness_card(readiness: object) -> str:
    """Build compact HTML for Cyber Essentials readiness."""
    if not isinstance(readiness, dict):
        return "<p>No Cyber Essentials readiness summary is available yet.</p>"
    rows = [
        ("Profile", readiness.get("profile_name")),
        ("Overall readiness score", readiness.get("overall_readiness_score")),
        ("Pillar count", readiness.get("pillar_count")),
    ]
    pillars = readiness.get("pillars", [])
    if not isinstance(pillars, list):
        pillars = []
    pillar_markup = "".join(
        (
            "<li>"
            f"<span class=\"detail-label\">{escape(str(pillar.get('pillar_name', '')))}:</span> "
            f"<span class=\"pill pill-status_{escape(str(pillar.get('status', '')))}\">{escape(str(pillar.get('status', '')))}</span> "
            f"({float(pillar.get('readiness_score', 0.0)):.2f})"
            "</li>"
        )
        for pillar in pillars
        if isinstance(pillar, dict)
    )
    detail_markup = "".join(
        f"<li><span class=\"detail-label\">{escape(str(label))}:</span> {escape(str(value))}</li>"
        for label, value in rows
        if value not in (None, "", {})
    )
    return f"<ul class=\"detail-list\">{detail_markup}{pillar_markup}</ul>"


def _build_executive_pack_card(executive_pack: object) -> str:
    """Build compact HTML for the board-ready executive pack."""
    if not isinstance(executive_pack, dict):
        return "<p>No executive pack is available yet.</p>"
    rows = [
        ("Pack", executive_pack.get("pack_name")),
        ("Board message", executive_pack.get("board_message")),
        ("Benchmark status", executive_pack.get("benchmark_status")),
        ("Benchmark note", executive_pack.get("benchmark_note")),
    ]
    top_risks = executive_pack.get("top_risks", [])
    if not isinstance(top_risks, list):
        top_risks = []
    risk_markup = "".join(
        (
            "<li>"
            f"<span class=\"detail-label\">{escape(str(risk.get('control_id', '')))}:</span> "
            f"{escape(str(risk.get('title', '')))} ({escape(str(risk.get('priority', '')))}, "
            f"{float(risk.get('score', 0.0)):.2f})"
            "</li>"
        )
        for risk in top_risks[:5]
        if isinstance(risk, dict)
    )
    detail_markup = "".join(
        f"<li><span class=\"detail-label\">{escape(str(label))}:</span> {escape(str(value))}</li>"
        for label, value in rows
        if value not in (None, "", {})
    )
    return f"<ul class=\"detail-list\">{detail_markup}{risk_markup}</ul>"
