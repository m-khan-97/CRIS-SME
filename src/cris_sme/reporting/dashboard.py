# Dashboard payload + interactive HTML console generation for CRIS-SME.
from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any


def build_dashboard_payload(
    report: dict[str, Any],
    history_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a compact dashboard-oriented payload from the full report."""
    prioritized = report.get("prioritized_risks", [])
    if not isinstance(prioritized, list):
        prioritized = []
    category_scores = report.get("category_scores", {})
    if not isinstance(category_scores, dict):
        category_scores = {}
    history = report.get("history_comparison", {})
    if not isinstance(history, dict):
        history = {}
    compliance = report.get("compliance", {})
    if not isinstance(compliance, dict):
        compliance = {}
    graph_context = report.get("graph_context", {})
    if not isinstance(graph_context, dict):
        graph_context = {}

    priority_counts = _priority_counts(prioritized)
    status_counts = _status_counts(prioritized)
    domain_counts = _domain_counts(prioritized)
    confidence_stats = _confidence_stats(prioritized)
    framework_coverage = compliance.get("frameworks_covered", [])
    if not isinstance(framework_coverage, list):
        framework_coverage = []

    payload = {
        "dashboard_schema_version": "1.0.0",
        "generated_at": report.get("generated_at"),
        "collector_mode": report.get("collector_mode"),
        "executive_overview": {
            "overall_risk_score": report.get("overall_risk_score", 0.0),
            "risk_band": _risk_band(float(report.get("overall_risk_score", 0.0))),
            "evaluated_profiles": int(
                (report.get("evaluation_context", {}) or {}).get("evaluated_profiles", 0)
            ),
            "finding_count": len(prioritized),
            "priority_counts": priority_counts,
            "lifecycle_status_counts": status_counts,
            "framework_coverage_count": len(framework_coverage),
            "provider_coverage_count": len(
                {
                    str(org.get("provider", "unknown"))
                    for org in (report.get("organizations", []) or [])
                    if isinstance(org, dict)
                }
            ),
            "confidence_summary": confidence_stats,
            "top_business_risks": _top_business_risks(prioritized),
        },
        "domain_breakdown": {
            "scores": category_scores,
            "finding_counts": domain_counts,
        },
        "trend": {
            "overall": history.get("overall_trend", _fallback_overall_trend(report, history_reports)),
            "domain": history.get("domain_trend", {}),
            "new_findings_count": history.get("new_findings_count", 0),
            "resolved_findings_count": history.get("resolved_findings_count", 0),
            "recurring_regression_count": history.get("recurring_regression_count", 0),
            "priority_distribution_trend": history.get("priority_distribution_trend", []),
            "framework_readiness_trend": history.get("framework_readiness_trend", []),
        },
        "finding_explorer": {
            "findings": prioritized,
            "available_priorities": sorted(
                {
                    str(item.get("priority", "Monitor"))
                    for item in prioritized
                    if isinstance(item, dict)
                }
            ),
            "available_domains": sorted(
                {
                    str(item.get("category", "Unknown"))
                    for item in prioritized
                    if isinstance(item, dict)
                }
            ),
            "available_statuses": sorted(status_counts),
        },
        "compliance_readiness": {
            "frameworks_covered": framework_coverage,
            "uk_profile": compliance.get("uk_sme_profile", {}),
            "cyber_essentials": report.get("cyber_essentials_readiness", {}),
        },
        "confidence_and_evidence": {
            "confidence_calibration": report.get("confidence_calibration", {}),
            "direct_vs_inferred": _direct_inferred_unavailable_counts(prioritized),
            "evidence_sufficiency_counts": _evidence_sufficiency_counts(prioritized),
            "collector_coverage": report.get("collector_coverage", []),
            "provider_evidence_contract_summary": _provider_contract_summary(
                report.get("provider_evidence_contracts", {})
            ),
            "provider_contract_conformance": _provider_contract_conformance_summary(
                report.get("provider_contract_conformance", {})
            ),
            "assessment_replay": _assessment_replay_summary(
                report.get("assessment_replay", {})
            ),
            "evidence_gap_backlog": _evidence_gap_backlog_summary(
                report.get("evidence_gap_backlog", {})
            ),
            "policy_pack_changelog": _policy_pack_changelog_summary(
                report.get("policy_pack_changelog", {})
            ),
        },
        "graph_context": {
            "blast_radius": graph_context.get("blast_radius", {}),
            "toxic_combinations": graph_context.get("toxic_combinations", []),
            "top_exposure_chains": graph_context.get("top_exposure_chains", []),
            "assets": graph_context.get("assets", []),
            "relationships": graph_context.get("relationships", []),
        },
        "remediation": {
            "budget_profiles": (report.get("budget_aware_remediation", {}) or {}).get("budget_profiles", []),
            "action_plan": report.get("action_plan_30_day", {}),
            "simulation": report.get("remediation_simulation", {}),
            "quick_wins": _quick_wins(report),
        },
        "exceptions_and_governance": {
            "status_counts": status_counts,
            "exception_rows": _exception_rows(prioritized),
        },
        "decision_ledger": _decision_ledger_summary(report.get("decision_ledger", {})),
        "control_drift_attribution": _control_drift_attribution_summary(
            report.get("control_drift_attribution", {})
        ),
        "assessment_assurance": _assessment_assurance_summary(
            report.get("assessment_assurance", {})
        ),
        "native_validation": report.get("native_validation", {}),
        "artifacts": report.get("report_artifacts", {}),
    }
    return payload


def write_dashboard_payload(payload: dict[str, Any], output_dir: str | Path) -> Path:
    """Write the dashboard JSON payload to disk."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / "cris_sme_dashboard_payload.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def build_dashboard_html(payload: dict[str, Any]) -> str:
    """Build a premium interactive dashboard HTML using only local assets."""
    payload_json = json.dumps(payload)
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>CRIS-SME Decision Console</title>
    <style>
      :root {{
        --bg: #07101b;
        --panel: #0f1d2d;
        --panel-2: #14273d;
        --ink: #e7eff8;
        --muted: #95abc1;
        --line: rgba(149, 171, 193, 0.18);
        --accent: #1dc9b7;
        --accent-2: #5da3ff;
        --danger: #ff6f61;
        --warn: #ffb347;
        --ok: #69d79c;
      }}

      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
        background:
          radial-gradient(circle at 10% 10%, rgba(29, 201, 183, 0.18), transparent 28%),
          radial-gradient(circle at 90% 15%, rgba(93, 163, 255, 0.16), transparent 30%),
          var(--bg);
        color: var(--ink);
      }}
      .container {{ max-width: 1440px; margin: 0 auto; padding: 20px; }}
      .hero {{
        background: linear-gradient(140deg, rgba(15,29,45,0.95), rgba(20,39,61,0.95));
        border: 1px solid var(--line);
        border-radius: 22px;
        padding: 24px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.28);
      }}
      .hero h1 {{
        margin: 0;
        font-size: clamp(1.8rem, 2.8vw, 2.9rem);
        letter-spacing: -0.02em;
      }}
      .hero p {{ margin: 8px 0 0; color: var(--muted); max-width: 85ch; line-height: 1.55; }}
      .grid {{
        display: grid;
        gap: 14px;
        margin-top: 14px;
        grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      }}
      .card {{
        background: linear-gradient(180deg, rgba(20,39,61,0.88), rgba(11,23,36,0.92));
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 14px;
      }}
      .label {{ color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; }}
      .metric {{ font-size: 1.8rem; font-weight: 700; margin-top: 6px; }}
      .section {{
        margin-top: 18px;
        background: rgba(15, 29, 45, 0.92);
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 16px;
      }}
      .section h2 {{ margin: 0 0 12px; font-size: 1.05rem; letter-spacing: 0.01em; }}
      .bars {{
        display: grid;
        gap: 10px;
      }}
      .bar-row {{
        display: grid;
        grid-template-columns: 180px 1fr 70px;
        align-items: center;
        gap: 10px;
      }}
      .bar-bg {{
        height: 10px;
        border-radius: 999px;
        background: rgba(149,171,193,0.15);
        overflow: hidden;
      }}
      .bar-fill {{
        height: 100%;
        border-radius: 999px;
        background: linear-gradient(90deg, var(--accent), var(--accent-2));
      }}
      .trend-box {{
        background: rgba(7, 16, 27, 0.65);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 10px 12px;
      }}
      .split {{
        display: grid;
        grid-template-columns: 1.1fr 1fr;
        gap: 14px;
      }}
      .kpi-strip {{
        display: grid;
        gap: 10px;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      }}
      .kpi {{
        background: rgba(7,16,27,0.52);
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 10px;
      }}
      table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
      }}
      th, td {{
        border-bottom: 1px solid var(--line);
        padding: 10px 8px;
        text-align: left;
        vertical-align: top;
      }}
      th {{
        color: var(--muted);
        font-weight: 600;
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
      }}
      .pill {{
        display: inline-block;
        border-radius: 999px;
        padding: 2px 10px;
        font-size: 0.72rem;
        border: 1px solid var(--line);
      }}
      .pill-immediate {{ background: rgba(255,111,97,0.18); color: #ffcabf; }}
      .pill-high {{ background: rgba(255,179,71,0.18); color: #ffe0b3; }}
      .pill-planned {{ background: rgba(105,215,156,0.18); color: #c8f5dc; }}
      .pill-monitor {{ background: rgba(93,163,255,0.18); color: #d4e7ff; }}
      .toolbar {{
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-bottom: 10px;
      }}
      input, select {{
        background: rgba(7, 16, 27, 0.65);
        color: var(--ink);
        border: 1px solid var(--line);
        border-radius: 9px;
        padding: 8px 10px;
      }}
      .mono {{ font-family: "IBM Plex Mono", "Consolas", monospace; }}
      .list {{ margin: 0; padding-left: 18px; color: var(--muted); }}
      @media (max-width: 1080px) {{
        .split {{ grid-template-columns: 1fr; }}
        .bar-row {{ grid-template-columns: 1fr; }}
      }}
    </style>
  </head>
  <body>
    <div class="container">
      <section class="hero">
        <h1>CRIS-SME Risk Decision Console</h1>
        <p>Evidence-driven cloud risk intelligence for SMEs. Deterministic control decisions, lifecycle-aware findings, graph-context prioritization, and budget-aware remediation in one operator-friendly console.</p>
        <div class="grid" id="hero-cards"></div>
      </section>

      <section class="section">
        <h2>Domain Breakdown</h2>
        <div class="bars" id="domain-bars"></div>
      </section>

      <section class="section split">
        <div>
          <h2>Trend</h2>
          <div class="trend-box" id="overall-trend"></div>
          <div class="kpi-strip" id="trend-kpis" style="margin-top:10px;"></div>
        </div>
        <div>
          <h2>Graph Context</h2>
          <div class="kpi-strip" id="graph-kpis"></div>
          <h3 style="margin:12px 0 6px; font-size:0.9rem;">Toxic Combinations</h3>
          <ul class="list" id="toxic-list"></ul>
        </div>
      </section>

      <section class="section">
        <h2>Finding Explorer</h2>
        <div class="toolbar">
          <input id="search-box" placeholder="Search control, title, evidence..." />
          <select id="priority-filter"></select>
          <select id="domain-filter"></select>
          <select id="status-filter"></select>
        </div>
        <table>
          <thead>
            <tr>
              <th>Control</th>
              <th>Domain</th>
              <th>Priority</th>
              <th>Status</th>
              <th>Score</th>
              <th>Confidence</th>
              <th>Evidence</th>
            </tr>
          </thead>
          <tbody id="finding-rows"></tbody>
        </table>
      </section>

      <section class="section split">
        <div>
          <h2>Compliance Readiness</h2>
          <div class="kpi-strip" id="compliance-kpis"></div>
          <ul class="list" id="framework-list" style="margin-top:10px;"></ul>
        </div>
        <div>
          <h2>Remediation & Exceptions</h2>
          <div class="kpi-strip" id="remediation-kpis"></div>
          <h3 style="margin:12px 0 6px; font-size:0.9rem;">Accepted/Suppressed/Expired Exceptions</h3>
          <ul class="list" id="exception-list"></ul>
        </div>
      </section>
    </div>
    <script>
      const payload = {payload_json};
      const findings = (payload.finding_explorer && payload.finding_explorer.findings) || [];

      const byId = (id) => document.getElementById(id);
      const pct = (v) => Math.max(0, Math.min(100, Number(v || 0)));
      const fmt = (v) => Number(v || 0).toFixed(2);

      function pillClass(priority) {{
        const p = String(priority || "Monitor").toLowerCase();
        if (p === "immediate") return "pill-immediate";
        if (p === "high") return "pill-high";
        if (p === "planned") return "pill-planned";
        return "pill-monitor";
      }}

      function renderHero() {{
        const eo = payload.executive_overview || {{}};
        const cards = [
          ["Overall risk", fmt(eo.overall_risk_score), eo.risk_band || ""],
          ["Findings", eo.finding_count || 0, `Profiles: ${{eo.evaluated_profiles || 0}}`],
          ["Immediate", (eo.priority_counts || {{}}).Immediate || 0, "Must-fix band"],
          ["High", (eo.priority_counts || {{}}).High || 0, "Near-term actions"],
          ["Frameworks", eo.framework_coverage_count || 0, "Mapped references"],
          ["Providers", eo.provider_coverage_count || 0, "In current run scope"],
          ["Avg calibrated confidence", fmt((eo.confidence_summary || {{}}).avg_calibrated_confidence || 0), ""],
        ];
        byId("hero-cards").innerHTML = cards.map(([label, metric, note]) =>
          `<article class="card"><div class="label">${{label}}</div><div class="metric">${{metric}}</div><div class="label">${{note}}</div></article>`
        ).join("");
      }}

      function renderDomainBars() {{
        const scores = (payload.domain_breakdown || {{}}).scores || {{}};
        byId("domain-bars").innerHTML = Object.entries(scores).map(([domain, score]) => `
          <div class="bar-row">
            <div>${{domain}}</div>
            <div class="bar-bg"><div class="bar-fill" style="width:${{pct(score)}}%"></div></div>
            <div class="mono">${{fmt(score)}}</div>
          </div>
        `).join("");
      }}

      function renderTrend() {{
        const trend = (payload.trend || {{}}).overall || [];
        if (!trend.length) {{
          byId("overall-trend").textContent = "No trend snapshots available.";
          return;
        }}
        const scores = trend.map((row) => Number(row.overall_risk_score || 0));
        const min = Math.min(...scores, 0);
        const max = Math.max(...scores, 10);
        const width = 720;
        const height = 140;
        const left = 18;
        const right = 14;
        const top = 16;
        const bottom = 26;
        const innerW = width - left - right;
        const innerH = height - top - bottom;
        const step = innerW / Math.max(1, scores.length - 1);
        const points = scores.map((score, i) => {{
          const x = left + (i * step);
          const y = top + ((max - score) / Math.max(1, max - min)) * innerH;
          return [x, y];
        }});
        const pointString = points.map(([x, y]) => `${{x.toFixed(1)}},${{y.toFixed(1)}}`).join(" ");
        byId("overall-trend").innerHTML = `
          <svg viewBox="0 0 ${{width}} ${{height}}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;">
            <line x1="${{left}}" y1="${{top + innerH}}" x2="${{width-right}}" y2="${{top + innerH}}" stroke="rgba(149,171,193,0.34)" />
            <polyline points="${{pointString}}" fill="none" stroke="#1dc9b7" stroke-width="3" />
            ${{points.map(([x, y], i) => `<circle cx="${{x}}" cy="${{y}}" r="4" fill="#5da3ff" /><text x="${{x}}" y="${{y-8}}" text-anchor="middle" font-size="10" fill="#95abc1">${{scores[i].toFixed(1)}}</text>`).join("")}}
          </svg>
        `;

        const kpis = payload.trend || {{}};
        byId("trend-kpis").innerHTML = [
          ["New findings", kpis.new_findings_count || 0],
          ["Resolved findings", kpis.resolved_findings_count || 0],
          ["Recurring regressions", kpis.recurring_regression_count || 0],
        ].map(([label, value]) => `<div class="kpi"><div class="label">${{label}}</div><div class="metric" style="font-size:1.2rem;">${{value}}</div></div>`).join("");
      }}

      function renderGraphContext() {{
        const ctx = payload.graph_context || {{}};
        const blast = ctx.blast_radius || {{}};
        byId("graph-kpis").innerHTML = [
          ["Blast radius score", fmt(blast.score || 0)],
          ["Blast radius band", blast.band || "unknown"],
          ["Toxic combinations", (ctx.toxic_combinations || []).length],
          ["Exposure chains", (ctx.top_exposure_chains || []).length],
        ].map(([label, value]) => `<div class="kpi"><div class="label">${{label}}</div><div class="metric" style="font-size:1.2rem;">${{value}}</div></div>`).join("");
        byId("toxic-list").innerHTML = (ctx.toxic_combinations || []).map((item) =>
          `<li><strong>${{item.title}}</strong> (${{item.impact}}) - ${{item.narrative}}</li>`
        ).join("") || "<li>No toxic combinations were detected in the current run.</li>";
      }}

      function setupFilters() {{
        const priorities = ["All", ...((payload.finding_explorer || {{}}).available_priorities || [])];
        const domains = ["All", ...((payload.finding_explorer || {{}}).available_domains || [])];
        const statuses = ["All", ...((payload.finding_explorer || {{}}).available_statuses || [])];
        byId("priority-filter").innerHTML = priorities.map((p) => `<option>${{p}}</option>`).join("");
        byId("domain-filter").innerHTML = domains.map((d) => `<option>${{d}}</option>`).join("");
        byId("status-filter").innerHTML = statuses.map((s) => `<option>${{s}}</option>`).join("");

        ["search-box", "priority-filter", "domain-filter", "status-filter"].forEach((id) =>
          byId(id).addEventListener("input", renderFindingRows)
        );
      }}

      function renderFindingRows() {{
        const q = String(byId("search-box").value || "").trim().toLowerCase();
        const priority = byId("priority-filter").value;
        const domain = byId("domain-filter").value;
        const status = byId("status-filter").value;

        const rows = findings.filter((item) => {{
          const lifecycleStatus = ((item.lifecycle || {{}}).status || "open");
          const haystack = [
            item.control_id, item.title, item.category, item.organization,
            ...(Array.isArray(item.evidence) ? item.evidence : []),
          ].join(" ").toLowerCase();
          if (q && !haystack.includes(q)) return false;
          if (priority !== "All" && item.priority !== priority) return false;
          if (domain !== "All" && item.category !== domain) return false;
          if (status !== "All" && lifecycleStatus !== status) return false;
          return true;
        }});

        byId("finding-rows").innerHTML = rows.map((item) => {{
          const lifecycleStatus = ((item.lifecycle || {{}}).status || "open");
          const conf = (item.confidence_calibration || {{}}).calibrated_confidence || 0;
          const evidence = Array.isArray(item.evidence) ? item.evidence.slice(0, 2).join("; ") : "";
          return `
            <tr>
              <td><strong>${{item.control_id}}</strong><br />${{item.title || ""}}</td>
              <td>${{item.category || ""}}</td>
              <td><span class="pill ${{pillClass(item.priority)}}">${{item.priority || "Monitor"}}</span></td>
              <td><span class="pill">${{lifecycleStatus}}</span></td>
              <td class="mono">${{fmt(item.score)}}</td>
              <td class="mono">${{fmt(Number(conf) * 100)}}%</td>
              <td>${{evidence}}</td>
            </tr>
          `;
        }}).join("") || `<tr><td colspan="7">No findings match the current filters.</td></tr>`;
      }}

      function renderCompliance() {{
        const comp = payload.compliance_readiness || {{}};
        const uk = comp.uk_profile || {{}};
        const ce = comp.cyber_essentials || {{}};
        byId("compliance-kpis").innerHTML = [
          ["Frameworks covered", (comp.frameworks_covered || []).length],
          ["UK mapped controls", uk.mapped_control_count || 0],
          ["UK mapped findings", uk.mapped_finding_count || 0],
          ["Cyber Essentials", fmt(ce.overall_readiness_score || 0)],
        ].map(([label, value]) => `<div class="kpi"><div class="label">${{label}}</div><div class="metric" style="font-size:1.2rem;">${{value}}</div></div>`).join("");
        byId("framework-list").innerHTML = (comp.frameworks_covered || []).map((f) =>
          `<li>${{f}}</li>`
        ).join("") || "<li>No framework mapping data available.</li>";
      }}

      function renderRemediationAndExceptions() {{
        const remediation = payload.remediation || {{}};
        const quick = remediation.quick_wins || {{}};
        byId("remediation-kpis").innerHTML = [
          ["Quick wins", quick.quick_win_count || 0],
          ["Quick win risk total", fmt(quick.quick_win_risk_total || 0)],
          ["Exception rows", (payload.exceptions_and_governance || {{}}).exception_rows?.length || 0],
          ["Accepted risk", ((payload.exceptions_and_governance || {{}}).status_counts || {{}}).accepted_risk || 0],
        ].map(([label, value]) => `<div class="kpi"><div class="label">${{label}}</div><div class="metric" style="font-size:1.2rem;">${{value}}</div></div>`).join("");
        const exceptions = (payload.exceptions_and_governance || {{}}).exception_rows || [];
        byId("exception-list").innerHTML = exceptions.map((row) =>
          `<li><strong>${{row.control_id}}</strong> - ${{row.status}}${{row.expires_at ? ` (expires ${{row.expires_at}})` : ""}}</li>`
        ).join("") || "<li>No accepted/suppressed/expired exception entries in the current run.</li>";
      }}

      renderHero();
      renderDomainBars();
      renderTrend();
      renderGraphContext();
      setupFilters();
      renderFindingRows();
      renderCompliance();
      renderRemediationAndExceptions();
    </script>
  </body>
</html>"""


def write_dashboard_html(html: str, output_path: str | Path) -> Path:
    """Write dashboard HTML to disk."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path


def _risk_band(score: float) -> str:
    if score >= 70:
        return "critical"
    if score >= 45:
        return "elevated"
    if score >= 20:
        return "managed"
    return "contained"


def _priority_counts(prioritized: list[object]) -> dict[str, int]:
    counts = {"Immediate": 0, "High": 0, "Planned": 0, "Monitor": 0}
    for item in prioritized:
        if not isinstance(item, dict):
            continue
        label = str(item.get("priority", "Monitor"))
        counts[label] = counts.get(label, 0) + 1
    return counts


def _status_counts(prioritized: list[object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in prioritized:
        if not isinstance(item, dict):
            continue
        lifecycle = item.get("lifecycle", {})
        if not isinstance(lifecycle, dict):
            continue
        status = str(lifecycle.get("status", "open"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def _domain_counts(prioritized: list[object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in prioritized:
        if not isinstance(item, dict):
            continue
        category = str(item.get("category", "Unknown"))
        counts[category] = counts.get(category, 0) + 1
    return counts


def _confidence_stats(prioritized: list[object]) -> dict[str, float]:
    observed: list[float] = []
    calibrated: list[float] = []
    for item in prioritized:
        if not isinstance(item, dict):
            continue
        confidence = item.get("confidence_calibration", {})
        if not isinstance(confidence, dict):
            continue
        observed.append(float(confidence.get("observed_confidence", 0.0)))
        calibrated.append(float(confidence.get("calibrated_confidence", 0.0)))
    if not observed or not calibrated:
        return {
            "avg_observed_confidence": 0.0,
            "avg_calibrated_confidence": 0.0,
        }
    return {
        "avg_observed_confidence": round(mean(observed), 4),
        "avg_calibrated_confidence": round(mean(calibrated), 4),
    }


def _top_business_risks(prioritized: list[object]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in prioritized[:5]:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "control_id": item.get("control_id"),
                "title": item.get("title"),
                "score": item.get("score"),
                "priority": item.get("priority"),
            }
        )
    return rows


def _direct_inferred_unavailable_counts(
    prioritized: list[object],
) -> dict[str, int]:
    counts = {"observed": 0, "inferred": 0, "unavailable": 0}
    for item in prioritized:
        if not isinstance(item, dict):
            continue
        quality = item.get("evidence_quality", {})
        if not isinstance(quality, dict):
            continue
        observation_class = str(quality.get("observation_class", "observed"))
        counts[observation_class] = counts.get(observation_class, 0) + 1
    return counts


def _evidence_sufficiency_counts(prioritized: list[object]) -> dict[str, int]:
    """Count evidence sufficiency labels across prioritized findings."""
    counts: dict[str, int] = {}
    for item in prioritized:
        if not isinstance(item, dict):
            continue
        quality = item.get("evidence_quality", {})
        if not isinstance(quality, dict):
            continue
        sufficiency = str(quality.get("sufficiency", "unknown"))
        counts[sufficiency] = counts.get(sufficiency, 0) + 1
    return counts


def _provider_contract_summary(raw_contracts: object) -> dict[str, Any]:
    """Build compact dashboard metadata from provider evidence contracts."""
    if not isinstance(raw_contracts, dict):
        return {
            "provider_count": 0,
            "control_count": 0,
            "contract_count": 0,
            "support_status_counts": {},
        }
    return {
        "contract_schema_version": raw_contracts.get("contract_schema_version"),
        "policy_pack_version": raw_contracts.get("policy_pack_version"),
        "provider_count": int(raw_contracts.get("provider_count", 0)),
        "control_count": int(raw_contracts.get("control_count", 0)),
        "contract_count": int(raw_contracts.get("contract_count", 0)),
        "support_status_counts": raw_contracts.get("support_status_counts", {}),
    }


def _provider_contract_conformance_summary(raw_conformance: object) -> dict[str, Any]:
    """Build compact dashboard metadata from provider contract conformance."""
    if not isinstance(raw_conformance, dict):
        return {
            "passed": False,
            "provider_count": 0,
            "control_count": 0,
            "failed_contract_count": 0,
        }
    return {
        "conformance_schema_version": raw_conformance.get("conformance_schema_version"),
        "policy_pack_version": raw_conformance.get("policy_pack_version"),
        "passed": bool(raw_conformance.get("passed", False)),
        "provider_count": int(raw_conformance.get("provider_count", 0)),
        "control_count": int(raw_conformance.get("control_count", 0)),
        "active_contract_count": int(raw_conformance.get("active_contract_count", 0)),
        "planned_contract_count": int(raw_conformance.get("planned_contract_count", 0)),
        "passed_contract_count": int(raw_conformance.get("passed_contract_count", 0)),
        "failed_contract_count": int(raw_conformance.get("failed_contract_count", 0)),
    }


def _assessment_replay_summary(raw_replay: object) -> dict[str, Any]:
    """Build compact dashboard metadata from assessment replay output."""
    if not isinstance(raw_replay, dict):
        return {
            "replayable": False,
            "deterministic_match": False,
            "evidence_changed": False,
            "policy_pack_changed": False,
        }
    replay = raw_replay.get("replay", {})
    diff = raw_replay.get("evidence_diff", {})
    if not isinstance(replay, dict):
        replay = {}
    if not isinstance(diff, dict):
        diff = {}
    return {
        "snapshot_id": replay.get("snapshot_id"),
        "replayable": bool(replay.get("replayable", False)),
        "deterministic_match": bool(replay.get("deterministic_match", False)),
        "overall_risk_delta": float(replay.get("overall_risk_delta", 0.0)),
        "profile_hash_verified": bool(replay.get("profile_hash_verified", False)),
        "finding_hash_verified": bool(replay.get("finding_hash_verified", False)),
        "evidence_changed": bool(diff.get("evidence_changed", False)),
        "policy_pack_changed": bool(diff.get("policy_pack_changed", False)),
        "collector_mode_changed": bool(diff.get("collector_mode_changed", False)),
        "score_delta_reason": diff.get("score_delta_reason"),
    }


def _evidence_gap_backlog_summary(raw_backlog: object) -> dict[str, Any]:
    """Build compact dashboard metadata from the evidence gap backlog."""
    if not isinstance(raw_backlog, dict):
        return {
            "item_count": 0,
            "high_priority_count": 0,
            "provider_counts": {},
            "domain_counts": {},
        }
    return {
        "backlog_schema_version": raw_backlog.get("backlog_schema_version"),
        "item_count": int(raw_backlog.get("item_count", 0)),
        "high_priority_count": int(raw_backlog.get("high_priority_count", 0)),
        "provider_counts": raw_backlog.get("provider_counts", {}),
        "domain_counts": raw_backlog.get("domain_counts", {}),
        "top_items": raw_backlog.get("items", [])[:10]
        if isinstance(raw_backlog.get("items"), list)
        else [],
    }


def _policy_pack_changelog_summary(raw_changelog: object) -> dict[str, Any]:
    """Build compact dashboard metadata from the policy-pack changelog."""
    if not isinstance(raw_changelog, dict):
        return {
            "active_policy_pack_version": None,
            "entry_count": 0,
            "touched_control_count": 0,
            "change_type_counts": {},
        }
    entries = raw_changelog.get("entries", [])
    touched_controls: set[str] = set()
    change_type_counts: dict[str, int] = {}
    if isinstance(entries, list):
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            change_type = str(entry.get("change_type", "unknown"))
            change_type_counts[change_type] = change_type_counts.get(change_type, 0) + 1
            for control_id in entry.get("control_ids", []):
                if str(control_id).strip():
                    touched_controls.add(str(control_id))
    return {
        "changelog_schema_version": raw_changelog.get("changelog_schema_version"),
        "active_policy_pack_version": raw_changelog.get("active_policy_pack_version"),
        "entry_count": int(raw_changelog.get("entry_count", 0)),
        "touched_control_count": len(touched_controls),
        "change_type_counts": change_type_counts,
    }


def _quick_wins(report: dict[str, Any]) -> dict[str, Any]:
    remediation = report.get("budget_aware_remediation", {})
    if not isinstance(remediation, dict):
        return {"quick_win_count": 0, "quick_win_risk_total": 0.0}
    profiles = remediation.get("budget_profiles", [])
    if not isinstance(profiles, list):
        return {"quick_win_count": 0, "quick_win_risk_total": 0.0}
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        if str(profile.get("profile_id")) == "free_this_week":
            return {
                "quick_win_count": int(profile.get("total_recommended", 0)),
                "quick_win_risk_total": float(profile.get("cumulative_risk_score", 0.0)),
            }
    return {"quick_win_count": 0, "quick_win_risk_total": 0.0}


def _assessment_assurance_summary(raw_assurance: object) -> dict[str, Any]:
    """Build compact dashboard metadata from assessment assurance output."""
    if not isinstance(raw_assurance, dict):
        return {
            "assurance_score": 0.0,
            "assurance_level": "unknown",
            "risk_score_impact": "Assessment assurance is unavailable.",
        }
    return {
        "assurance_schema_version": raw_assurance.get("assurance_schema_version"),
        "assurance_score": float(raw_assurance.get("assurance_score", 0.0)),
        "assurance_level": raw_assurance.get("assurance_level", "unknown"),
        "risk_score_impact": raw_assurance.get("risk_score_impact"),
        "strength_count": len(raw_assurance.get("strengths", []))
        if isinstance(raw_assurance.get("strengths"), list)
        else 0,
        "gap_count": len(raw_assurance.get("gaps", []))
        if isinstance(raw_assurance.get("gaps"), list)
        else 0,
    }


def _control_drift_attribution_summary(raw_attribution: object) -> dict[str, Any]:
    """Build compact dashboard metadata from control drift attribution."""
    if not isinstance(raw_attribution, dict):
        return {
            "comparable": False,
            "primary_attribution": "unknown",
            "overall_risk_delta": None,
            "attribution_counts": {},
        }
    return {
        "attribution_schema_version": raw_attribution.get("attribution_schema_version"),
        "comparable": bool(raw_attribution.get("comparable", False)),
        "primary_attribution": raw_attribution.get("primary_attribution", "unknown"),
        "overall_risk_delta": raw_attribution.get("overall_risk_delta"),
        "attribution_counts": raw_attribution.get("attribution_counts", {}),
        "evidence_changed": bool(raw_attribution.get("evidence_changed", False)),
        "policy_pack_changed": bool(raw_attribution.get("policy_pack_changed", False)),
        "collector_mode_changed": bool(raw_attribution.get("collector_mode_changed", False)),
        "lifecycle_changed": bool(raw_attribution.get("lifecycle_changed", False)),
        "exception_state_changed": bool(raw_attribution.get("exception_state_changed", False)),
        "top_items": raw_attribution.get("items", [])[:10]
        if isinstance(raw_attribution.get("items"), list)
        else [],
    }


def _exception_rows(prioritized: list[object]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in prioritized:
        if not isinstance(item, dict):
            continue
        lifecycle = item.get("lifecycle", {})
        if not isinstance(lifecycle, dict):
            continue
        status = str(lifecycle.get("status", "open"))
        if status not in {"accepted_risk", "suppressed", "expired_exception"}:
            continue
        exception = lifecycle.get("exception", {})
        if not isinstance(exception, dict):
            exception = {}
        rows.append(
            {
                "control_id": item.get("control_id"),
                "status": status,
                "exception_id": exception.get("exception_id"),
                "expires_at": exception.get("expires_at"),
                "reason": exception.get("reason"),
            }
        )
    return rows


def _decision_ledger_summary(raw_ledger: object) -> dict[str, Any]:
    """Build a compact dashboard view from the report Decision Ledger."""
    if not isinstance(raw_ledger, dict):
        return {
            "event_count": 0,
            "event_type_counts": {},
            "latest_events": [],
        }
    events = raw_ledger.get("events", [])
    if not isinstance(events, list):
        events = []
    counts: dict[str, int] = {}
    for event in events:
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("event_type", "unknown"))
        counts[event_type] = counts.get(event_type, 0) + 1
    return {
        "ledger_schema_version": raw_ledger.get("ledger_schema_version"),
        "generated_at": raw_ledger.get("generated_at"),
        "current_run_id": raw_ledger.get("current_run_id"),
        "previous_run_id": raw_ledger.get("previous_run_id"),
        "current_evaluation_mode": raw_ledger.get("current_evaluation_mode"),
        "previous_evaluation_mode": raw_ledger.get("previous_evaluation_mode"),
        "comparison_basis": raw_ledger.get("comparison_basis"),
        "event_count": int(raw_ledger.get("event_count", len(events))),
        "event_type_counts": counts,
        "latest_events": events[:12],
    }


def _fallback_overall_trend(
    report: dict[str, Any],
    history_reports: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if history_reports:
        rows = []
        for row in history_reports:
            rows.append(
                {
                    "generated_at": row.get("generated_at"),
                    "collector_mode": row.get("collector_mode"),
                    "overall_risk_score": float(row.get("overall_risk_score", 0.0)),
                }
            )
        return rows
    return [
        {
            "generated_at": report.get("generated_at"),
            "collector_mode": report.get("collector_mode"),
            "overall_risk_score": float(report.get("overall_risk_score", 0.0)),
        }
    ]
