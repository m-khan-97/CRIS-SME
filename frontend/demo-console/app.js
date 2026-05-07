const state = {
  dashboard: null,
  report: null,
  disclosure: null,
  ceAssessment: null,
  ceReview: null,
  ceMetrics: null,
  cePaperTables: "",
  findings: [],
  filteredFindings: [],
  selectedFindingId: null,
  priorityFilter: "All",
  disclosureProfile: "customer",
  selectedControls: new Set(),
};

const DATA_PATHS = {
  dashboard: "../data/cris_sme_dashboard_payload.json",
  report: "../data/cris_sme_report.json",
  disclosure: "../data/cris_sme_selective_disclosure.json",
  ceAssessment: "../data/cris_sme_ce_self_assessment.json",
  ceReview: "../data/cris_sme_ce_review_console.json",
  ceMetrics: "../data/cris_sme_ce_evaluation_metrics.json",
  cePaperTables: "../data/cris_sme_ce_paper_tables.md",
};

const fallbackPaths = {
  dashboard: "../../outputs/reports/cris_sme_dashboard_payload.json",
  report: "../../outputs/reports/cris_sme_report.json",
  disclosure: "../../outputs/reports/cris_sme_selective_disclosure.json",
  ceAssessment: "../../outputs/reports/cris_sme_ce_self_assessment.json",
  ceReview: "../../outputs/reports/cris_sme_ce_review_console.json",
  ceMetrics: "../../outputs/reports/cris_sme_ce_evaluation_metrics.json",
  cePaperTables: "../../outputs/reports/cris_sme_ce_paper_tables.md",
};

document.addEventListener("DOMContentLoaded", async () => {
  wireNavigation();
  wireSearch();
  await loadData();
  hydrate();
});

async function loadData() {
  const [dashboard, report, disclosure, ceAssessment, ceReview, ceMetrics, cePaperTables] = await Promise.all([
    fetchJson("dashboard"),
    fetchJson("report"),
    fetchJson("disclosure"),
    fetchJson("ceAssessment"),
    fetchJson("ceReview"),
    fetchJson("ceMetrics"),
    fetchText("cePaperTables"),
  ]);
  state.dashboard = dashboard;
  state.report = report;
  state.disclosure = disclosure;
  state.ceAssessment = ceAssessment;
  state.ceReview = ceReview;
  state.ceMetrics = ceMetrics;
  state.cePaperTables = cePaperTables;
  state.findings = dashboard?.finding_explorer?.findings || report?.prioritized_risks || [];
  state.filteredFindings = state.findings;
  state.selectedFindingId = state.findings[0]?.finding_id || null;
}

async function fetchJson(key) {
  for (const path of [DATA_PATHS[key], fallbackPaths[key]]) {
    try {
      const response = await fetch(path, { cache: "no-store" });
      if (response.ok) return response.json();
    } catch {
      continue;
    }
  }
  return {};
}

async function fetchText(key) {
  for (const path of [DATA_PATHS[key], fallbackPaths[key]]) {
    try {
      const response = await fetch(path, { cache: "no-store" });
      if (response.ok) return response.text();
    } catch {
      continue;
    }
  }
  return "";
}

function hydrate() {
  renderOverview();
  renderPriorityFilter();
  renderFindingTable();
  renderFindingDetail();
  renderProvenance();
  renderAssurance();
  renderCeWorkflow();
  renderDisclosureTabs();
  renderDisclosure();
  renderRemediation();
}

function wireNavigation() {
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => {
      const view = button.dataset.view;
      document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".view").forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      document.querySelector(`#view-${view}`)?.classList.add("active");
      history.replaceState(null, "", `#${view}`);
    });
  });
  const initialView = window.location.hash.replace("#", "");
  if (initialView) {
    document.querySelector(`.nav-item[data-view="${CSS.escape(initialView)}"]`)?.click();
  }
}

function wireSearch() {
  document.querySelector("#finding-search")?.addEventListener("input", (event) => {
    applyFindingFilters(event.target.value);
  });
}

function applyFindingFilters(query = document.querySelector("#finding-search")?.value || "") {
  const q = query.trim().toLowerCase();
  state.filteredFindings = state.findings.filter((finding) => {
    const matchesPriority = state.priorityFilter === "All" || finding.priority === state.priorityFilter;
    const haystack = [
      finding.control_id,
      finding.title,
      finding.priority,
      finding.category,
      finding.finding_id,
    ].join(" ").toLowerCase();
    return matchesPriority && (!q || haystack.includes(q));
  });
  if (!state.filteredFindings.some((item) => item.finding_id === state.selectedFindingId)) {
    state.selectedFindingId = state.filteredFindings[0]?.finding_id || state.findings[0]?.finding_id || null;
  }
  renderFindingTable();
  renderFindingDetail();
  renderProvenance();
}

function renderOverview() {
  const overview = state.dashboard?.executive_overview || {};
  const trust = state.dashboard?.report_trust_badge || {};
  const assurance = state.dashboard?.assessment_assurance || {};
  const replay = state.dashboard?.confidence_and_evidence?.assessment_replay || {};
  const score = Number(overview.overall_risk_score || state.report?.overall_risk_score || 0);
  text("#assessment-summary", state.report?.summary || "CRIS-SME assessment loaded from generated artifacts.");
  text("#risk-score", score.toFixed(1));
  text("#risk-band", overview.risk_band || "risk band");
  const circumference = 390;
  const offset = circumference - (Math.min(score, 100) / 100) * circumference;
  document.querySelector("#risk-ring")?.style.setProperty("stroke-dashoffset", String(offset));

  const metrics = [
    ["Findings", overview.finding_count || 0, "prioritized non-compliant decisions"],
    ["Trust", trust.label || trust.level || "Assurance available", trust.statement || "Report trust signals are available."],
    ["Assurance", fmtNumber(assurance.assurance_score), `${assurance.assurance_level || "unknown"} assessment assurance`],
    ["Replay", replay.deterministic_match ? "Verified" : "Review", replay.risk_score_impact || "Deterministic replay status"],
    ["Providers", overview.provider_coverage_count || 0, "provider coverage count"],
    ["Frameworks", overview.framework_coverage_count || 0, "mapped governance references"],
  ];
  html("#overview-metrics", metrics.map(metricCard).join(""));
  renderDomainBars();
  renderTopRisks();
}

function renderDomainBars() {
  const scores = state.dashboard?.domain_breakdown?.scores || {};
  const rows = Object.entries(scores).map(([domain, value]) => `
    <div class="bar-row">
      <strong>${escapeHtml(domain)}</strong>
      <div class="bar-track"><div class="bar-fill" style="width:${clamp(value)}%"></div></div>
      <span>${fmtNumber(value)}</span>
    </div>
  `);
  html("#domain-bars", rows.join(""));
}

function renderTopRisks() {
  const risks = state.dashboard?.executive_overview?.top_business_risks || state.findings.slice(0, 5);
  html("#top-risks", risks.map((risk) => `
    <article class="risk-item">
      <span class="pill ${priorityClass(risk.priority)}">${escapeHtml(risk.priority || "Risk")}</span>
      <div>
        <strong>${escapeHtml(risk.control_id || "")}</strong>
        <p>${escapeHtml(risk.title || "")}</p>
      </div>
      <strong>${fmtNumber(risk.score)}</strong>
    </article>
  `).join(""));
}

function renderPriorityFilter() {
  const priorities = ["All", ...new Set(state.findings.map((finding) => finding.priority).filter(Boolean))];
  html("#priority-filter", priorities.map((priority) => `
    <button class="${priority === state.priorityFilter ? "active" : ""}" type="button" data-priority="${escapeHtml(priority)}">${escapeHtml(priority)}</button>
  `).join(""));
  document.querySelectorAll("#priority-filter button").forEach((button) => {
    button.addEventListener("click", () => {
      state.priorityFilter = button.dataset.priority;
      renderPriorityFilter();
      applyFindingFilters();
    });
  });
}

function renderFindingTable() {
  html("#finding-table", state.filteredFindings.map((finding) => `
    <article class="finding-row ${finding.finding_id === state.selectedFindingId ? "active" : ""}" data-finding-id="${escapeHtml(finding.finding_id)}">
      <span class="pill ${priorityClass(finding.priority)}">${escapeHtml(finding.priority || "Risk")}</span>
      <div class="finding-title">
        <strong>${escapeHtml(finding.control_id || "")}</strong>
        <p>${escapeHtml(finding.title || "")}</p>
      </div>
      <strong>${fmtNumber(finding.score)}</strong>
    </article>
  `).join(""));
  document.querySelectorAll(".finding-row").forEach((row) => {
    row.addEventListener("click", () => {
      state.selectedFindingId = row.dataset.findingId;
      renderFindingTable();
      renderFindingDetail();
      renderProvenance();
    });
  });
}

function renderFindingDetail() {
  const finding = selectedFinding();
  if (!finding) {
    html("#finding-detail", "<h3>No finding selected</h3>");
    return;
  }
  const quality = finding.evidence_quality || {};
  const confidence = finding.confidence_calibration || {};
  html("#finding-detail", `
    <span class="eyebrow">${escapeHtml(finding.finding_id || "finding")}</span>
    <h3>${escapeHtml(finding.title || "")}</h3>
    <p>${escapeHtml(finding.decision_rationale || "Deterministic decision rationale unavailable.")}</p>
    <div class="detail-block">
      <strong>Risk decision</strong>
      <p>${escapeHtml(finding.control_id)} | ${escapeHtml(finding.category)} | ${escapeHtml(finding.severity)} | Score ${fmtNumber(finding.score)}</p>
    </div>
    <div class="detail-block">
      <strong>Evidence quality</strong>
      <p>Sufficiency: ${escapeHtml(quality.sufficiency || "unknown")} | Direct: ${quality.direct_evidence_count || 0} | Inferred: ${quality.inferred_evidence_count || 0}</p>
    </div>
    <div class="detail-block">
      <strong>Confidence</strong>
      <p>Observed ${fmtPercent(confidence.observed_confidence)} | Calibrated ${fmtPercent(confidence.calibrated_confidence)}</p>
    </div>
    <div class="detail-block">
      <strong>Remediation</strong>
      <p>${escapeHtml(finding.remediation_summary || "No remediation summary available.")}</p>
    </div>
  `);
}

function renderProvenance() {
  const finding = selectedFinding();
  const graph = state.report?.decision_provenance_graph || {};
  const paths = graph.top_decision_paths || [];
  const path = paths.find((item) => item.finding_id === finding?.finding_id) || paths[0] || {};
  text("#selected-path-label", path.control_id || finding?.control_id || "Decision path");
  const nodes = path.node_ids || [
    `finding:${finding?.finding_id || "selected"}`,
    `control:${finding?.control_id || "control"}`,
    "score:deterministic",
    "assurance:assessment",
  ];
  html("#decision-path", nodes.map((node) => `
    <article class="path-node">
      <div>
        <strong>${escapeHtml(nodeType(node))}</strong>
        <p>${escapeHtml(node)}</p>
      </div>
    </article>
  `).join(""));
  renderGraphCanvas(nodes);
}

function renderGraphCanvas(nodes) {
  const points = nodes.slice(0, 8).map((node, index) => {
    const x = 70 + (index % 4) * 170;
    const y = 70 + Math.floor(index / 4) * 140;
    return { node, x, y };
  });
  const lines = points.slice(1).map((point, index) => {
    const prev = points[index];
    return `<line x1="${prev.x}" y1="${prev.y}" x2="${point.x}" y2="${point.y}" stroke="rgba(32,213,196,.42)" stroke-width="2" />`;
  }).join("");
  const circles = points.map((point) => `
    <g>
      <circle cx="${point.x}" cy="${point.y}" r="25" fill="rgba(32,213,196,.18)" stroke="rgba(32,213,196,.72)" />
      <text x="${point.x}" y="${point.y + 48}" text-anchor="middle" fill="#dbeafe" font-size="12">${escapeHtml(nodeType(point.node))}</text>
    </g>
  `).join("");
  html("#graph-canvas", `<svg viewBox="0 0 720 360" preserveAspectRatio="xMidYMid meet">${lines}${circles}</svg>`);
}

function renderAssurance() {
  const badge = state.dashboard?.report_trust_badge || {};
  const claims = state.report?.claim_verification_pack?.claims || [];
  const caseData = state.report?.assurance_case || {};
  const rbom = state.report?.risk_bill_of_materials || {};
  const replay = state.report?.assessment_replay?.replay || {};
  const metrics = [
    ["Trust badge", badge.level || badge.label || "available", badge.statement || "Stakeholder trust summary"],
    ["Claims", claims.length, `${claims.filter((claim) => claim.verification_status === "verified").length} verified`],
    ["Assurance case", fmtNumber(caseData.assurance_score), caseData.overall_conclusion || "unknown"],
    ["RBOM", rbom.canonical_report_sha256 ? "Present" : "Missing", `${(rbom.artifacts || []).length} hashed artifacts`],
    ["Replay", replay.deterministic_match ? "Verified" : "Review", `Risk delta ${fmtNumber(replay.overall_risk_delta || 0)}`],
  ];
  html("#assurance-metrics", metrics.map(metricCard).join(""));
  html("#claim-list", claims.slice(0, 10).map((claim) => `
    <article class="claim-item">
      <span class="pill ${claim.verification_status}">${escapeHtml(claim.verification_status)}</span>
      <strong>${escapeHtml(claim.claim_type)}</strong>
      <p>${escapeHtml(claim.statement)}</p>
    </article>
  `).join(""));
  html("#argument-list", (caseData.arguments || []).map((argument) => `
    <article class="argument-item">
      <span class="pill ${argument.conclusion}">${escapeHtml(argument.conclusion)}</span>
      <strong>${escapeHtml(argument.top_claim)}</strong>
      <p>${escapeHtml(argument.reasoning)}</p>
    </article>
  `).join(""));
}

function renderCeWorkflow() {
  const metrics = state.ceMetrics || {};
  const observability = metrics.observability_metrics || {};
  const review = metrics.review_metrics || {};
  const questionSet = metrics.question_set || {};
  const gapTaxonomy = metrics.evidence_gap_taxonomy || {};
  const tables = metrics.paper_tables || {};
  const headlineMetrics = [
    ["Question set", `${questionSet.name || "CE"} ${questionSet.version || ""}`.trim(), `requirements ${questionSet.requirements_version || "unknown"}`],
    ["Mapped entries", metrics.question_count || 0, `${metrics.technical_question_count || 0} technical-control entries`],
    ["Cloud observable", `${fmtNumber(observability.cloud_supported_rate)}%`, `${observability.cloud_supported_count || 0} total entries`],
    ["Technical observable", `${fmtNumber(observability.technical_cloud_supported_rate)}%`, `${observability.technical_cloud_supported_count || 0} technical entries`],
    ["Review state", `${review.pending_count || 0} pending`, `${review.reviewed_count || 0} reviewed entries`],
    ["Agreement", `${fmtNumber(review.agreement_rate)}%`, `${review.agreement_count || 0} of ${review.agreement_evaluable_count || 0} evaluable`],
  ];
  html("#ce-metrics", headlineMetrics.map(metricCard).join(""));

  const observabilityRows = tables.observability_by_evidence_class || [];
  html("#ce-observability-bars", observabilityRows.map((row) => `
    <div class="bar-row">
      <strong>${escapeHtml(labelize(row.label))}</strong>
      <div class="bar-track"><div class="bar-fill" style="width:${clamp(row.rate)}%"></div></div>
      <span>${fmtNumber(row.count)}</span>
    </div>
  `).join(""));

  html("#ce-gap-list", Object.entries(gapTaxonomy).map(([key, detail]) => `
    <article class="risk-item">
      <span class="pill">${escapeHtml(fmtNumber(detail.rate))}%</span>
      <div>
        <strong>${escapeHtml(labelize(key))}</strong>
        <p>${escapeHtml(detail.description || "Evidence gap")}</p>
      </div>
      <strong>${escapeHtml(detail.count || 0)}</strong>
    </article>
  `).join(""));

  const reviewRows = tables.review_outcomes || [];
  const answerRows = tables.proposed_answers || [];
  html("#ce-review-bars", [
    ...answerRows.map((row) => `
    <div class="bar-row">
      <strong>Answer ${escapeHtml(row.label)}</strong>
      <div class="bar-track"><div class="bar-fill" style="width:${clamp(row.rate)}%"></div></div>
      <span>${fmtNumber(row.count)}</span>
    </div>
  `),
    ...reviewRows.map((row) => `
    <div class="bar-row">
      <strong>Review ${escapeHtml(labelize(row.label))}</strong>
      <div class="bar-track"><div class="bar-fill" style="width:${clamp(row.rate)}%"></div></div>
      <span>${fmtNumber(row.count)}</span>
    </div>
  `),
  ].join(""));

  const controls = metrics.top_controls_causing_ce_answer_failures || tables.control_failure_contribution || [];
  html("#ce-control-list", controls.slice(0, 8).map((control) => `
    <article class="risk-item">
      <span class="pill high">${escapeHtml(control.control_id || "control")}</span>
      <div>
        <strong>${escapeHtml(control.affected_question_count || 0)} affected questions</strong>
        <p>${escapeHtml((control.sample_finding_titles || []).join("; ") || "Mapped CE answer impact")}</p>
      </div>
      <strong>${fmtNumber(control.max_linked_score)}</strong>
    </article>
  `).join(""));

  html("#ce-paper-preview", renderPaperPreview(state.cePaperTables));
}

function renderDisclosureTabs() {
  const rooms = state.disclosure?.rooms || [];
  html("#disclosure-tabs", rooms.map((room) => `
    <button class="${room.profile_id === state.disclosureProfile ? "active" : ""}" type="button" data-profile="${escapeHtml(room.profile_id)}">${escapeHtml(room.profile_name)}</button>
  `).join(""));
  document.querySelectorAll("#disclosure-tabs button").forEach((button) => {
    button.addEventListener("click", () => {
      state.disclosureProfile = button.dataset.profile;
      renderDisclosureTabs();
      renderDisclosure();
    });
  });
}

function renderDisclosure() {
  const room = (state.disclosure?.rooms || []).find((item) => item.profile_id === state.disclosureProfile) || {};
  html("#disclosure-room", `
    <span class="eyebrow">${escapeHtml(room.audience || "stakeholder")}</span>
    <h3>${escapeHtml(room.profile_name || "Disclosure Room")}</h3>
    <p>${escapeHtml(room.disclosure_level || "redacted evidence view")}</p>
    <div class="metric-grid">
      ${metricCard(["Claims", room.included_claim_count || 0, "included"])}
      ${metricCard(["Evidence", room.shared_evidence_count || 0, "shared"])}
      ${metricCard(["Redactions", room.redaction_count || 0, "applied"])}
      ${metricCard(["Withheld", room.withheld_count || 0, "recorded"])}
    </div>
    ${(room.claims || []).slice(0, 6).map((claim) => `
      <article class="disclosure-card">
        <span class="pill ${claim.verification_status}">${escapeHtml(claim.verification_status)}</span>
        <strong>${escapeHtml(claim.claim_type)}</strong>
        <p>${escapeHtml(claim.statement)}</p>
      </article>
    `).join("")}
  `);
  const redactions = (room.redactions || []).slice(0, 8);
  const withheld = (room.withheld_items || []).slice(0, 8);
  html("#redaction-register", `
    ${redactions.map((item) => `
      <article class="disclosure-card">
        <strong>${escapeHtml(item.redaction_type)}</strong>
        <p>${escapeHtml(item.field_path)}</p>
      </article>
    `).join("")}
    ${withheld.map((item) => `
      <article class="disclosure-card">
        <strong>Withheld</strong>
        <p>${escapeHtml(item.replacement_summary)}</p>
      </article>
    `).join("")}
  `);
}

function renderRemediation() {
  const candidates = state.findings.slice(0, 10);
  html("#simulator-list", candidates.map((finding) => `
    <label class="sim-option">
      <input type="checkbox" value="${escapeHtml(finding.control_id)}" />
      <span>
        <strong>${escapeHtml(finding.control_id)} ${escapeHtml(finding.title)}</strong>
        <p>${escapeHtml(finding.remediation_summary || "Remediate this control gap.")}</p>
      </span>
      <strong>${fmtNumber(finding.score)}</strong>
    </label>
  `).join(""));
  document.querySelectorAll(".sim-option input").forEach((input) => {
    input.addEventListener("change", () => {
      if (input.checked) state.selectedControls.add(input.value);
      else state.selectedControls.delete(input.value);
      renderSimulationResult();
    });
  });
  renderSimulationResult();
}

function renderSimulationResult() {
  const base = Number(state.dashboard?.executive_overview?.overall_risk_score || state.report?.overall_risk_score || 0);
  const selected = state.findings.filter((finding) => state.selectedControls.has(finding.control_id));
  const reduction = Math.min(24, selected.reduce((sum, finding) => sum + Number(finding.score || 0) * 0.035, 0));
  const projected = Math.max(0, base - reduction);
  text("#simulated-score", projected.toFixed(1));
  text("#simulated-summary", selected.length
    ? `${selected.length} control remediation candidate(s) selected. Projected reduction: ${reduction.toFixed(1)} points.`
    : "Select remediation candidates to model risk reduction.");
  html("#impact-bars", selected.map((finding) => `
    <div class="bar-row">
      <strong>${escapeHtml(finding.control_id)}</strong>
      <div class="bar-track"><div class="bar-fill" style="width:${Math.min(100, Number(finding.score || 0))}%"></div></div>
      <span>${fmtNumber(Number(finding.score || 0) * 0.035)}</span>
    </div>
  `).join(""));
}

function selectedFinding() {
  return state.findings.find((finding) => finding.finding_id === state.selectedFindingId);
}

function metricCard([label, value, note]) {
  return `
    <article class="metric-card">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
      <p>${escapeHtml(note)}</p>
    </article>
  `;
}

function renderPaperPreview(markdown) {
  if (!markdown) return '<p class="muted">Paper tables are not available in this bundle.</p>';
  const lines = markdown.split("\n").slice(0, 42);
  return `<pre>${escapeHtml(lines.join("\n"))}</pre>`;
}

function labelize(value) {
  return String(value || "").replaceAll("_", " ");
}

function nodeType(node) {
  return String(node).split(":")[0].replaceAll("_", " ");
}

function priorityClass(priority) {
  const text = String(priority || "").toLowerCase();
  if (text.includes("immediate")) return "immediate";
  if (text.includes("high")) return "high";
  return "";
}

function fmtNumber(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value ?? "--");
  return number % 1 === 0 ? String(number) : number.toFixed(2);
}

function fmtPercent(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "--";
  return `${Math.round(number * 100)}%`;
}

function clamp(value) {
  return Math.max(0, Math.min(100, Number(value) || 0));
}

function text(selector, value) {
  const element = document.querySelector(selector);
  if (element) element.textContent = value;
}

function html(selector, value) {
  const element = document.querySelector(selector);
  if (element) element.innerHTML = value;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
