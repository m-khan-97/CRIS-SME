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
  ceReviewDecisions: {},
  ceReviewFilter: "Cloud supported",
  ceReviewQuery: "",
  selectedCeQuestionId: null,
  azureEnvironment: null,
  azureEnvironmentLoading: false,
  azureEnvironmentChecked: false,
  azureRun: null,
  azureRunPoller: null,
  publicExposure: null,
  publicExposureLoading: false,
};

const CE_REVIEW_STORAGE_KEY = "cris_sme_ce_review_decisions_v1";
const CE_REVIEW_FILTERS = ["Cloud supported", "Pending", "Accepted", "Overridden", "Needs evidence", "All"];
const LOCAL_API_BASE = ["http:", "//127.0.0.1:8787"].join("");

const PLATFORM_MODULES = [
  ["New Assessment", "Start a local Azure run from the console.", "assessment"],
  ["Public Exposure", "Authorised DNS, HTTP, HTTPS, and TLS checks.", "public-exposure"],
  ["Findings", "Prioritized cloud risk decisions with evidence quality.", "workbench"],
  ["Cyber Essentials", "Question-level CE answer impact and observability.", "ce-workflow"],
  ["Human Review", "Reviewer ledger for CE accept, override, or evidence requests.", "ce-review-workbench"],
  ["Evidence Room", "Shareable stakeholder assurance with redaction controls.", "disclosure"],
  ["Reports", "Executive, technical, research, and machine-readable outputs.", "reports"],
  ["Trust Center", "Claims, replay, RBOM, signatures, and assurance arguments.", "assurance"],
];

const ARTIFACT_GROUPS = {
  primary: [
    ["Executive Report", "../report.html", "HTML", "Technical report with prioritized risks and deterministic score context."],
    ["Assurance Portal", "../assurance.html", "HTML", "Customer-facing assurance view for trust conversations."],
    ["Evidence Room", "../evidence-room.html", "HTML", "Selective disclosure room with redactions and share manifest."],
    ["Dashboard Payload", "../data/cris_sme_dashboard_payload.json", "JSON", "Data backing this unified console."],
    ["Canonical Report JSON", "../data/cris_sme_report.json", "JSON", "Machine-readable report for API and audit workflows."],
    ["Selective Disclosure JSON", "../data/cris_sme_selective_disclosure.json", "JSON", "Redacted stakeholder package data."],
  ],
  assurance: [
    ["CE Answer Pack", "../ce-self-assessment.html", "HTML", "Pre-populated Cyber Essentials answer-impact pack."],
    ["CE Review Console", "../ce-review-console.html", "HTML", "Generated human-review ledger view."],
    ["CE Evaluation Metrics", "../ce-evaluation.html", "HTML", "Paper and evaluation metrics generated from artifacts."],
    ["CE Answer Pack JSON", "../data/cris_sme_ce_self_assessment.json", "JSON", "Question-level CE output for research and automation."],
    ["CE Review JSON", "../data/cris_sme_ce_review_console.json", "JSON", "Review-console ledger source data."],
    ["CE Paper Tables", "../data/cris_sme_ce_paper_tables.md", "MD", "Manuscript-ready tables derived from metrics JSON."],
  ],
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
  state.ceReviewDecisions = loadCeReviewDecisions();
  state.selectedCeQuestionId = filteredCeReviewEntries()[0]?.question_id || ceReview?.entries?.[0]?.question_id || null;
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
  renderStatusBar();
  renderAzureAssessmentWizard();
  renderPublicExposure();
  renderPriorityFilter();
  renderFindingTable();
  renderFindingDetail();
  renderProvenance();
  renderAssurance();
  renderCeWorkflow();
  renderCeReviewWorkbench();
  renderDisclosureTabs();
  renderDisclosure();
  renderReportsHub();
  renderRemediation();
}

function renderStatusBar() {
  const report = state.report || state.dashboard;
  if (!report) return;
  const orgs = report.organizations || [];
  const org = orgs[0]?.organization_name || "CRIS-SME";
  const provider = orgs[0]?.provider || "azure";
  const ts = report.generated_at;
  const nonCompliant = report.evaluation_context?.non_compliant_findings ?? (state.findings.length);
  text("#status-org", org);
  text("#status-provider", provider.charAt(0).toUpperCase() + provider.slice(1));
  text("#status-findings", `${nonCompliant} non-compliant finding${nonCompliant !== 1 ? "s" : ""}`);
  if (ts) {
    const d = new Date(ts);
    const fmt = d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
      + " " + d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
    text("#status-run-time", "Last run: " + fmt);
  }
}

function toast(message, type = "ok") {
  const shelf = document.getElementById("toast-shelf");
  if (!shelf) return;
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  shelf.appendChild(el);
  setTimeout(() => el.remove(), 3200);
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
      if (view === "assessment") {
        ensureAzureEnvironmentPreflight();
      }
    });
  });
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener("click", (event) => {
      const view = link.getAttribute("href")?.replace("#", "");
      const navButton = view ? document.querySelector(`.nav-item[data-view="${CSS.escape(view)}"]`) : null;
      if (navButton) {
        event.preventDefault();
        navButton.click();
      }
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
  document.querySelector("#ce-review-search")?.addEventListener("input", (event) => {
    state.ceReviewQuery = event.target.value;
    renderCeReviewWorkbench();
  });
  document.querySelector("#ce-export-json")?.addEventListener("click", () => {
    exportCeReviewJson();
  });
  document.querySelector("#ce-export-csv")?.addEventListener("click", () => {
    exportCeReviewCsv();
  });
  document.querySelector("#azure-env-refresh")?.addEventListener("click", () => {
    refreshAzureEnvironment({ force: true });
  });
  document.querySelector("#azure-assessment-form")?.addEventListener("submit", (event) => {
    event.preventDefault();
    startAzureAssessmentRun();
  });
  document.querySelector("#public-exposure-form")?.addEventListener("submit", (event) => {
    event.preventDefault();
    startPublicExposureAssessment();
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
  const circumference = 415;
  const offset = circumference - (Math.min(score, 100) / 100) * circumference;
  document.querySelector("#risk-ring")?.style.setProperty("stroke-dashoffset", String(offset));
  renderRiskTrendSparkline();
  renderCePillarBars();

  const metrics = [
    ["Findings", overview.finding_count || 0, "prioritized non-compliant decisions"],
    ["Trust", trust.label || trust.level || "Assurance available", trust.statement || "Report trust signals are available."],
    ["Assurance", fmtNumber(assurance.assurance_score), `${assurance.assurance_level || "unknown"} assessment assurance`],
    ["Replay", replay.deterministic_match ? "Verified" : "Review", replay.risk_score_impact || "Deterministic replay status"],
    ["Providers", overview.provider_coverage_count || 0, "provider coverage count"],
    ["Frameworks", overview.framework_coverage_count || 0, "mapped governance references"],
  ];
  html("#overview-metrics", metrics.map(metricCard).join(""));
  renderPlatformModules();
  renderDomainBars();
  renderTopRisks();
}

function renderPlatformModules() {
  html("#platform-modules", PLATFORM_MODULES.map(([title, note, view]) => `
    <button class="module-card" type="button" data-module-view="${escapeHtml(view)}">
      <strong>${escapeHtml(title)}</strong>
      <span>${escapeHtml(note)}</span>
    </button>
  `).join(""));
  document.querySelectorAll(".module-card").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelector(`.nav-item[data-view="${CSS.escape(button.dataset.moduleView)}"]`)?.click();
    });
  });
}

function renderAzureAssessmentWizard() {
  const env = state.azureEnvironment;
  const run = state.azureRun;
  const account = env?.account || {};
  const envStatus = env
    ? env.authenticated ? "Authenticated" : env.azure_cli_available ? "Login needed" : "CLI missing"
    : state.azureEnvironmentLoading ? "Checking" : "Not checked";
  const runStatus = run?.status || "idle";
  const metrics = [
    ["Local API", env ? "Reachable" : state.azureEnvironmentLoading ? "Checking" : "Not checked", "runner at 127.0.0.1:8787"],
    ["Azure CLI", envStatus, env?.message || (state.azureEnvironmentLoading ? "Inspecting local Azure CLI session." : "Open this view to auto-check Azure CLI.")],
    ["Subscription", account.subscription_name || account.subscription_id || "Not selected", "detected or manually entered"],
    ["Run", runStatus, run?.run_id || "no active run"],
  ];
  html("#azure-run-metrics", metrics.map(metricCard).join(""));
  renderAzureStepTracker();
  html("#azure-env-status", `
    <article class="connection-card">
      <span class="pill ${env?.authenticated ? "verified" : "high"}">${escapeHtml(envStatus)}</span>
      <strong>${escapeHtml(env?.message || (state.azureEnvironmentLoading ? "Checking local Azure CLI authentication..." : "Azure CLI will be checked automatically when this view opens."))}</strong>
      <p>CRIS-SME never asks for Azure passwords or client secrets in the browser. Local mode uses your existing <code>az login</code> session.</p>
    </article>
  `);
  if (account.subscription_id && !document.querySelector("#azure-subscription-id")?.value) {
    document.querySelector("#azure-subscription-id").value = account.subscription_id;
  }
  if (account.tenant_id && !document.querySelector("#azure-tenant-id")?.value) {
    document.querySelector("#azure-tenant-id").value = account.tenant_id;
  }
  renderAzureRunStatus();
}

function renderAzureStepTracker() {
  const env = state.azureEnvironment;
  const run = state.azureRun;
  const hasConfig = Boolean(
    document.querySelector("#azure-subscription-id")?.value ||
    env?.account?.subscription_id
  );
  const running = ["queued", "running", "started"].includes(String(run?.status || "").toLowerCase());
  const completed = String(run?.status || "").toLowerCase() === "completed";
  const failed = String(run?.status || "").toLowerCase() === "failed";
  const steps = [
    ["Authenticate", Boolean(env?.authenticated), state.azureEnvironmentLoading && !env, failed && !env?.authenticated],
    ["Connect", Boolean(env?.azure_cli_available), state.azureEnvironmentLoading, Boolean(env && !env.azure_cli_available)],
    ["Configure", hasConfig, Boolean(env?.authenticated && !hasConfig), false],
    ["Run", completed || running, running, failed],
    ["Review", completed, false, false],
  ];
  html("#azure-step-track", steps.map(([label, done, active, error], index) => `
    <div class="step-item">
      <div class="step-num ${error ? "error" : done ? "done" : active ? "active" : ""}" aria-label="Step ${index + 1} ${error ? "error" : done ? "complete" : active ? "active" : "pending"}">${index + 1}</div>
      <span class="step-label ${error ? "error" : done ? "done" : active ? "active" : ""}">${escapeHtml(label)}</span>
    </div>
    ${index < steps.length - 1 ? `<div class="step-connector ${done ? "done" : ""}"></div>` : ""}
  `).join(""));
}

function ensureAzureEnvironmentPreflight() {
  if (state.azureEnvironmentChecked || state.azureEnvironmentLoading) return;
  refreshAzureEnvironment({ quiet: true });
}

async function refreshAzureEnvironment({ force = false, quiet = false } = {}) {
  if (state.azureEnvironmentLoading) return;
  if (state.azureEnvironmentChecked && !force) return;
  state.azureEnvironmentLoading = true;
  renderAzureAssessmentWizard();
  try {
    state.azureEnvironment = await apiGet("/api/environment/azure");
    if (!quiet) toast("Azure connection refreshed.");
  } catch (error) {
    state.azureEnvironment = {
      azure_cli_available: false,
      authenticated: false,
      message: `Local runner is not reachable: ${error.message}`,
    };
    if (!quiet) toast("Local runner is not reachable.", "warn");
  } finally {
    state.azureEnvironmentLoading = false;
    state.azureEnvironmentChecked = true;
  }
  renderAzureAssessmentWizard();
}

async function startAzureAssessmentRun() {
  const payload = {
    subscription_id: document.querySelector("#azure-subscription-id")?.value || "",
    tenant_id: document.querySelector("#azure-tenant-id")?.value || "",
    authorization_confirmed: Boolean(document.querySelector("#azure-authorized")?.checked),
  };
  if (!payload.authorization_confirmed) {
    toast("Confirm assessment authorisation before starting.", "warn");
    return;
  }
  try {
    state.azureRun = await apiPost("/api/assessments/azure", payload);
    toast("Azure assessment started.");
    pollAzureRun(state.azureRun.run_id);
  } catch (error) {
    state.azureRun = { status: "failed", error: error.message };
    toast("Azure assessment could not start.", "warn");
  }
  renderAzureAssessmentWizard();
}

async function pollAzureRun(runId) {
  if (state.azureRunPoller) clearInterval(state.azureRunPoller);
  state.azureRunPoller = setInterval(async () => {
    try {
      state.azureRun = await apiGet(`/api/assessments/${encodeURIComponent(runId)}`);
      renderAzureRunStatus();
      if (["completed", "failed"].includes(state.azureRun.status)) {
        clearInterval(state.azureRunPoller);
        state.azureRunPoller = null;
        toast(state.azureRun.status === "completed" ? "Azure assessment completed." : "Azure assessment failed.", state.azureRun.status === "completed" ? "ok" : "warn");
      }
    } catch (error) {
      state.azureRun = { run_id: runId, status: "failed", error: error.message };
      renderAzureRunStatus();
      clearInterval(state.azureRunPoller);
      state.azureRunPoller = null;
    }
  }, 2500);
}

function renderAzureRunStatus() {
  const run = state.azureRun;
  text("#azure-run-label", run?.run_id || "No active run");
  if (!run) {
    html("#azure-run-status", '<p class="muted">Start a run to see live collector status here.</p>');
    return;
  }
  html("#azure-run-status", `
    <article class="connection-card">
      <span class="pill ${run.status === "completed" ? "verified" : run.status === "failed" ? "immediate" : "high"}">${escapeHtml(run.status || "unknown")}</span>
      <strong>${escapeHtml(run.run_id || "local run")}</strong>
      <p>Output directory: ${escapeHtml(run.output_dir || "outputs/reports")}</p>
      ${run.error ? `<p class="error-text">${escapeHtml(run.error)}</p>` : ""}
      ${run.stderr_tail ? `<pre>${escapeHtml(run.stderr_tail)}</pre>` : ""}
    </article>
  `);
}

function renderPublicExposure() {
  const report = state.publicExposure;
  const summary = report?.summary || {};
  const metrics = [
    ["Targets", summary.target_count ?? 0, "authorised public targets"],
    ["Resolved", summary.resolved_target_count ?? 0, "DNS A/AAAA observed"],
    ["HTTPS", summary.https_available_count ?? 0, "targets with HTTPS response"],
    ["Findings", summary.finding_count ?? 0, `${summary.high_finding_count ?? 0} high`],
  ];
  html("#public-exposure-metrics", metrics.map(metricCard).join(""));
  text("#public-exposure-label", report ? report.generated_at || "Latest run" : "No public exposure run");
  if (state.publicExposureLoading) {
    html("#public-exposure-results", `
      <article class="connection-card">
        <span class="pill high">running</span>
        <strong>Checking authorised public targets...</strong>
        <p>CRIS-SME is collecting DNS, HTTP, HTTPS, and TLS metadata for the supplied scope.</p>
      </article>
    `);
    return;
  }
  if (!report) {
    html("#public-exposure-results", '<p class="muted">Run a public exposure check to see endpoint evidence here.</p>');
    return;
  }
  const findings = report.findings || [];
  const targets = report.targets || [];
  html("#public-exposure-results", `
    <div class="content-grid two compact-grid">
      <div>
        <h4>Findings</h4>
        ${findings.length ? findings.map((finding) => `
          <article class="risk-item">
            <span class="pill ${publicExposureSeverityClass(finding.severity)}">${escapeHtml(finding.severity || "info")}</span>
            <div>
              <strong>${escapeHtml(finding.id || "")} ${escapeHtml(finding.title || "")}</strong>
              <p>${escapeHtml(finding.target || "")} · ${escapeHtml(finding.evidence_summary || "")}</p>
            </div>
          </article>
        `).join("") : '<p class="muted">No public exposure findings were generated for this scoped run.</p>'}
      </div>
      <div>
        <h4>Targets</h4>
        ${targets.map((target) => `
          <article class="connection-card">
            <span class="pill ${target.https?.reachable ? "verified" : "high"}">${target.https?.reachable ? "HTTPS" : "Review"}</span>
            <strong>${escapeHtml(target.host || "")}</strong>
            <p>DNS: ${escapeHtml((target.dns?.addresses || []).join(", ") || "unresolved")}</p>
            <p>HTTP ${escapeHtml(target.http?.status || "n/a")} · HTTPS ${escapeHtml(target.https?.status || "n/a")} · TLS ${escapeHtml(target.tls?.protocol || "n/a")}</p>
          </article>
        `).join("")}
      </div>
    </div>
  `);
}

async function startPublicExposureAssessment() {
  const targets = document.querySelector("#public-exposure-targets")?.value || "";
  const authorizationConfirmed = Boolean(document.querySelector("#public-exposure-authorized")?.checked);
  if (!authorizationConfirmed) {
    toast("Confirm target authorisation before starting.", "warn");
    return;
  }
  state.publicExposureLoading = true;
  renderPublicExposure();
  try {
    state.publicExposure = await apiPost("/api/public-exposure", {
      targets,
      authorization_confirmed: authorizationConfirmed,
    });
    toast("Public exposure assessment completed.");
  } catch (error) {
    state.publicExposure = {
      generated_at: new Date().toISOString(),
      summary: { target_count: 0, finding_count: 1 },
      targets: [],
      findings: [{
        id: "PE-RUN",
        title: "Public exposure check failed",
        severity: "high",
        target: "local runner",
        evidence_summary: error.message,
      }],
    };
    toast("Public exposure assessment failed.", "warn");
  } finally {
    state.publicExposureLoading = false;
  }
  renderPublicExposure();
}

async function apiGet(path) {
  const response = await fetch(`${LOCAL_API_BASE}${path}`, { cache: "no-store" });
  return parseApiResponse(response);
}

async function apiPost(path, payload) {
  const response = await fetch(`${LOCAL_API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return parseApiResponse(response);
}

async function parseApiResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `API request failed with status ${response.status}`);
  }
  return payload;
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

function renderRiskTrendSparkline() {
  const points = getRiskTrendPoints().slice(-7);
  if (points.length < 2) {
    html("#risk-trend-card", '<p class="muted">At least two assessment snapshots are needed for a trajectory.</p>');
    text("#risk-trend-label", "Insufficient history");
    return;
  }
  const values = points.map((point) => Number(point.overall_risk_score || point.score || 0));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(max - min, 1);
  const width = 260;
  const height = 70;
  const path = values.map((value, index) => {
    const x = values.length === 1 ? width / 2 : (index / (values.length - 1)) * width;
    const y = height - ((value - min) / range) * (height - 12) - 6;
    return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const latest = values[values.length - 1];
  const previous = values[values.length - 2];
  const delta = latest - previous;
  text("#risk-trend-label", `${delta >= 0 ? "+" : ""}${delta.toFixed(2)} since prior`);
  html("#risk-trend-card", `
    <svg class="sparkline" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Risk score trajectory">
      <path class="sparkline-area" d="${path} L${width},${height} L0,${height} Z"></path>
      <path class="sparkline-line" d="${path}"></path>
    </svg>
    <div class="sparkline-meta">
      <span>${escapeHtml(points.length)} runs</span>
      <strong>${fmtNumber(latest)}</strong>
    </div>
  `);
}

function renderCePillarBars() {
  const readiness = state.report?.cyber_essentials_readiness
    || state.dashboard?.compliance_readiness?.cyber_essentials
    || {};
  const pillars = Array.isArray(readiness.pillars) ? readiness.pillars : [];
  if (!pillars.length) {
    html("#ce-pillar-bars", '<p class="muted">Cyber Essentials readiness data is not available in this artifact set.</p>');
    return;
  }
  html("#ce-pillar-bars", pillars.map((pillar) => {
    const score = Number(pillar.readiness_score || 0);
    const status = String(pillar.status || "unknown").toLowerCase();
    return `
      <div class="ce-pillar-row">
        <div>
          <strong>${escapeHtml(pillar.pillar_name || "Pillar")}</strong>
          <span class="pill ${ceStatusClass(status)}">${escapeHtml(status)}</span>
        </div>
        <div class="bar-track"><div class="bar-fill ${ceStatusClass(status)}" style="width:${clamp(score)}%"></div></div>
        <span>${fmtNumber(score)}%</span>
      </div>
    `;
  }).join(""));
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
  const breakdown = finding.score_breakdown || {};
  html("#finding-detail", `
    <span class="eyebrow">${escapeHtml(finding.finding_id || "finding")}</span>
    <h3>${escapeHtml(finding.title || "")}</h3>
    <p>${escapeHtml(finding.decision_rationale || "Deterministic decision rationale unavailable.")}</p>
    <div class="detail-actions">
      <button class="ghost-button" id="finding-markdown-export" type="button">Export markdown</button>
    </div>
    <div class="detail-block">
      <strong>Risk decision</strong>
      <p>${escapeHtml(finding.control_id)} | ${escapeHtml(finding.category)} | ${escapeHtml(finding.severity)} | Score ${fmtNumber(finding.score)}</p>
    </div>
    <div class="detail-block">
      <strong>Deterministic score breakdown</strong>
      ${renderScoreBreakdownGrid(breakdown)}
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
  document.querySelector("#finding-markdown-export")?.addEventListener("click", () => {
    exportFindingMarkdown(finding);
  });
}

function renderScoreBreakdownGrid(breakdown) {
  if (!breakdown || typeof breakdown !== "object" || !Object.keys(breakdown).length) {
    return '<p class="muted">Score factor data is unavailable for this finding.</p>';
  }
  const cells = [
    ["Severity", breakdown.base_severity],
    ["Likelihood", breakdown.likelihood_factor],
    ["Data", breakdown.data_factor],
    ["Confidence", breakdown.confidence_factor],
    ["Effort", breakdown.remediation_factor],
    ["Raw score", breakdown.raw_score],
  ];
  return `
    <div class="score-breakdown-grid">
      ${cells.map(([label, value]) => `
        <div class="score-breakdown-cell">
          <span>${escapeHtml(label)}</span>
          <strong>${fmtNumber(value)}</strong>
        </div>
      `).join("")}
    </div>
    <p>Normalized score: ${fmtNumber(breakdown.normalized_score)} / 100 · Calibration: ${escapeHtml(breakdown.calibration_status || "unknown")}</p>
  `;
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

function renderReportsHub() {
  const rbom = state.report?.risk_bill_of_materials || {};
  const metrics = [
    ["HTML reports", 5, "technical, assurance, evidence, CE, evaluation"],
    ["Machine JSON", 6, "report, dashboard, CE, review, disclosure, metrics"],
    ["RBOM", rbom.canonical_report_sha256 ? "Present" : "Missing", `${(rbom.artifacts || []).length} hashed artifacts`],
    ["CE tables", state.cePaperTables ? "Ready" : "Missing", "generated paper table markdown"],
  ];
  html("#artifact-metrics", metrics.map(metricCard).join(""));
  html("#primary-artifacts", ARTIFACT_GROUPS.primary.map(artifactCard).join(""));
  html("#assurance-artifacts", ARTIFACT_GROUPS.assurance.map(artifactCard).join(""));
}

function renderCeReviewWorkbench() {
  renderCeReviewMetrics();
  renderCeReviewFilter();
  renderCeReviewList();
  renderCeReviewDetail();
}

function renderCeReviewMetrics() {
  const entries = state.ceReview?.entries || [];
  const decisions = entries.map((entry) => entryDecision(entry));
  const reviewed = decisions.filter((decision) => decision.state && decision.state !== "pending").length;
  const accepted = decisions.filter((decision) => decision.state === "accepted").length;
  const overridden = decisions.filter((decision) => decision.state === "overridden").length;
  const needsEvidence = decisions.filter((decision) => decision.state === "needs_evidence").length;
  const cloudSupported = entries.filter(isCloudSupported).length;
  const draftAcceptCandidates = entries.filter((entry) => {
    const answer = String(entry.proposed_answer || "");
    return entry.evidence_class === "direct_cloud" || (entry.evidence_class === "inferred_cloud" && answer === "No");
  }).length;
  const metrics = [
    ["Human reviewed", reviewed, `${entries.length - reviewed} pending`],
    ["Human accepted", accepted, "reviewer-confirmed answers"],
    ["Overrides", overridden, "human correction ledger"],
    ["Needs evidence", needsEvidence, "explicit evidence requests"],
    ["Cloud-supported", cloudSupported, "answerable from cloud telemetry"],
    ["AI draft candidates", draftAcceptCandidates, "not counted as human agreement"],
  ];
  html("#ce-review-workbench-metrics", metrics.map(metricCard).join(""));
}

function renderCeReviewFilter() {
  html("#ce-review-filter", CE_REVIEW_FILTERS.map((filter) => `
    <button class="${filter === state.ceReviewFilter ? "active" : ""}" type="button" data-ce-filter="${escapeHtml(filter)}">${escapeHtml(filter)}</button>
  `).join(""));
  document.querySelectorAll("#ce-review-filter button").forEach((button) => {
    button.addEventListener("click", () => {
      state.ceReviewFilter = button.dataset.ceFilter;
      const entries = filteredCeReviewEntries();
      state.selectedCeQuestionId = entries[0]?.question_id || state.selectedCeQuestionId;
      renderCeReviewWorkbench();
    });
  });
}

function renderCeReviewList() {
  const entries = filteredCeReviewEntries();
  if (!entries.some((entry) => entry.question_id === state.selectedCeQuestionId)) {
    state.selectedCeQuestionId = entries[0]?.question_id || null;
  }
  if (!entries.length) {
    html("#ce-review-list", '<p class="muted">No review entries match the current filter.</p>');
    return;
  }
  html("#ce-review-list", entries.map((entry) => {
    const decision = entryDecision(entry);
    const answerClass = String(entry.proposed_answer || "").toLowerCase().replaceAll(" ", "-");
    const answerHint = ceAnswerHint(entry);
    return `
      <article class="ce-review-row ${entry.question_id === state.selectedCeQuestionId ? "active" : ""} answer-${answerClass}" data-question-id="${escapeHtml(entry.question_id)}">
        <span class="pill ${reviewPillClass(decision.state)}">${escapeHtml(reviewLabel(decision.state))}</span>
        <div>
          <strong>${escapeHtml(entry.question_id)} ${escapeHtml(entry.section || "")}</strong>
          <p>${escapeHtml(entry.short_paraphrase || "")}</p>
          <p class="answer-hint">${escapeHtml(answerHint)}</p>
        </div>
        <span class="answer-chip ${answerClass}" title="${escapeHtml(answerHint)}">${escapeHtml(entry.proposed_answer || "Cannot determine")}</span>
      </article>
    `;
  }).join(""));
  document.querySelectorAll(".ce-review-row").forEach((row) => {
    row.addEventListener("click", () => {
      state.selectedCeQuestionId = row.dataset.questionId;
      renderCeReviewList();
      renderCeReviewDetail();
    });
  });
}

function renderCeReviewDetail() {
  const entry = selectedCeReviewEntry();
  if (!entry) {
    html("#ce-review-detail", "<h3>No CE review entry selected</h3>");
    return;
  }
  const decision = entryDecision(entry);
  const linkedFindings = entry.linked_findings || [];
  const evidenceItems = entry.evidence || [];
  const answerAdvisory = ceAnswerAdvisory(entry);
  const answerClass = String(entry.proposed_answer || "").toLowerCase().replaceAll(" ", "-");
  html("#ce-review-detail", `
    <div class="ce-detail-heading">
      <span class="eyebrow">${escapeHtml(entry.question_id)} | ${escapeHtml(labelize(entry.section))}</span>
      <h3>${escapeHtml(entry.short_paraphrase || "")}</h3>
    </div>
    <div class="answer-strip">
      ${answerBox("Proposed answer", entry.proposed_answer || "Cannot determine", answerClass)}
      ${answerBox("Evidence class", labelize(entry.evidence_class))}
      ${answerBox("Proposed status", labelize(entry.proposed_status))}
    </div>
    <div class="detail-block answer-advisory ${answerClass}">
      <strong>${escapeHtml(answerAdvisory.title)}</strong>
      <p>${escapeHtml(answerAdvisory.body)}</p>
    </div>
    <div class="detail-block caveat-box">
      <strong>Answer basis</strong>
      <p>${escapeHtml(entry.answer_basis || "No answer basis supplied.")}</p>
      <p>${escapeHtml(entry.caveat || "Human verification remains required.")}</p>
    </div>
    <form class="review-form" id="ce-review-form">
      <label>
        <span>Review state</span>
        <select id="ce-review-state-input">
          ${reviewStateOption("pending", decision.state)}
          ${reviewStateOption("accepted", decision.state)}
          ${reviewStateOption("overridden", decision.state)}
          ${reviewStateOption("needs_evidence", decision.state)}
        </select>
      </label>
      <label>
        <span>Final answer</span>
        <select id="ce-final-answer-input">
          ${answerOption("pending_human_review", decision.final_answer)}
          ${answerOption("Yes", decision.final_answer)}
          ${answerOption("No", decision.final_answer)}
          ${answerOption("Cannot determine", decision.final_answer)}
        </select>
      </label>
      <label>
        <span>Reviewer</span>
        <input id="ce-reviewer-input" type="text" value="${escapeHtml(decision.reviewer || "")}" placeholder="Reviewer name or initials" />
      </label>
      <label>
        <span>Evidence reference</span>
        <input id="ce-evidence-reference-input" type="text" value="${escapeHtml(decision.additional_evidence_reference || "")}" placeholder="Ticket, file, interview note, portal path" />
      </label>
      <label class="wide-field">
        <span>Reviewer note</span>
        <textarea id="ce-reviewer-note-input" rows="3" placeholder="Why this answer is acceptable or what remains uncertain">${escapeHtml(decision.reviewer_note || "")}</textarea>
      </label>
      <label class="wide-field">
        <span>Override reason</span>
        <textarea id="ce-override-reason-input" rows="2" placeholder="Required when overriding the proposed answer">${escapeHtml(decision.override_reason || "")}</textarea>
      </label>
      <div class="form-actions">
        <button type="button" id="ce-quick-accept">Accept proposal</button>
        <button type="button" id="ce-quick-evidence">Needs evidence</button>
        <button type="submit">Save review</button>
      </div>
    </form>
    <div class="content-grid two compact-grid">
      <section class="detail-block">
        <strong>Linked findings</strong>
        ${linkedFindings.length ? linkedFindings.map((finding) => `
          <article class="mini-evidence-card">
            <span class="pill ${priorityClass(finding.priority)}">${escapeHtml(finding.priority || "risk")}</span>
            <div>
              <strong>${escapeHtml(finding.control_id || "")} ${escapeHtml(finding.title || "")}</strong>
              <p>Score ${fmtNumber(finding.score)} | ${escapeHtml(finding.finding_id || "")}</p>
            </div>
          </article>
        `).join("") : '<p class="muted">No mapped CRIS-SME findings are linked to this entry.</p>'}
      </section>
      <section class="detail-block">
        <strong>Evidence and next paths</strong>
        ${[...evidenceItems, ...(entry.planned_evidence_paths || [])].slice(0, 8).map((item) => `
          <p class="evidence-line">${escapeHtml(item)}</p>
        `).join("") || '<p class="muted">No evidence text supplied.</p>'}
      </section>
    </div>
  `);
  wireCeReviewForm(entry);
}

function wireCeReviewForm(entry) {
  document.querySelector("#ce-review-form")?.addEventListener("submit", (event) => {
    event.preventDefault();
    saveCeReviewDecision(entry, collectCeReviewFormDecision(entry));
  });
  document.querySelector("#ce-quick-accept")?.addEventListener("click", () => {
    const proposedAnswer = entry.proposed_answer || "Cannot determine";
    saveCeReviewDecision(entry, {
      state: "accepted",
      final_status: entry.proposed_status || "accepted",
      final_answer: proposedAnswer,
      reviewer: document.querySelector("#ce-reviewer-input")?.value || "",
      reviewer_note: document.querySelector("#ce-reviewer-note-input")?.value || "Accepted proposed answer after human review.",
      override_reason: "",
      additional_evidence_reference: document.querySelector("#ce-evidence-reference-input")?.value || "",
    });
  });
  document.querySelector("#ce-quick-evidence")?.addEventListener("click", () => {
    saveCeReviewDecision(entry, {
      state: "needs_evidence",
      final_status: "needs_evidence",
      final_answer: "Cannot determine",
      reviewer: document.querySelector("#ce-reviewer-input")?.value || "",
      reviewer_note: document.querySelector("#ce-reviewer-note-input")?.value || "Additional evidence required before this CE answer can be accepted.",
      override_reason: "",
      additional_evidence_reference: document.querySelector("#ce-evidence-reference-input")?.value || "",
    });
  });
}

function collectCeReviewFormDecision(entry) {
  const stateValue = document.querySelector("#ce-review-state-input")?.value || "pending";
  const finalAnswer = document.querySelector("#ce-final-answer-input")?.value || "pending_human_review";
  return {
    state: stateValue,
    final_status: stateValue === "pending" ? "pending_human_review" : stateValue,
    final_answer: finalAnswer,
    reviewer: document.querySelector("#ce-reviewer-input")?.value || "",
    reviewed_at: new Date().toISOString(),
    reviewer_note: document.querySelector("#ce-reviewer-note-input")?.value || "",
    override_reason: document.querySelector("#ce-override-reason-input")?.value || "",
    additional_evidence_reference: document.querySelector("#ce-evidence-reference-input")?.value || "",
    proposed_answer: entry.proposed_answer || "Cannot determine",
    proposed_status: entry.proposed_status || "",
    evidence_class: entry.evidence_class || "",
  };
}

function saveCeReviewDecision(entry, decision) {
  const current = entryDecision(entry);
  state.ceReviewDecisions[entry.question_id] = {
    ...current,
    ...decision,
    reviewed_at: decision.reviewed_at || new Date().toISOString(),
  };
  persistCeReviewDecisions();
  renderCeReviewWorkbench();
  const label = decision.state === "accepted" ? "Accepted"
    : decision.state === "needs_evidence" ? "Flagged for evidence"
    : decision.state === "overridden" ? "Override saved"
    : "Review saved";
  toast(`${label} — ${entry.question_id}`, decision.state === "accepted" ? "ok" : "warn");
}

function filteredCeReviewEntries() {
  const entries = state.ceReview?.entries || [];
  const query = state.ceReviewQuery.trim().toLowerCase();
  return entries.filter((entry) => {
    const decision = entryDecision(entry);
    const matchesFilter =
      state.ceReviewFilter === "All" ||
      (state.ceReviewFilter === "Cloud supported" && isCloudSupported(entry)) ||
      (state.ceReviewFilter === "Pending" && decision.state === "pending") ||
      (state.ceReviewFilter === "Accepted" && decision.state === "accepted") ||
      (state.ceReviewFilter === "Overridden" && decision.state === "overridden") ||
      (state.ceReviewFilter === "Needs evidence" && decision.state === "needs_evidence");
    const haystack = [
      entry.question_id,
      entry.section,
      entry.short_paraphrase,
      entry.evidence_class,
      entry.proposed_answer,
      entry.proposed_status,
      decision.state,
    ].join(" ").toLowerCase();
    return matchesFilter && (!query || haystack.includes(query));
  });
}

function selectedCeReviewEntry() {
  return (state.ceReview?.entries || []).find((entry) => entry.question_id === state.selectedCeQuestionId);
}

function entryDecision(entry) {
  const base = entry.review_decision || {};
  return {
    state: "pending",
    final_status: "pending_human_review",
    final_answer: "pending_human_review",
    reviewer: "",
    reviewed_at: "",
    reviewer_note: "",
    override_reason: "",
    additional_evidence_reference: "",
    ...base,
    ...(state.ceReviewDecisions[entry.question_id] || {}),
  };
}

function loadCeReviewDecisions() {
  try {
    return JSON.parse(localStorage.getItem(CE_REVIEW_STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

function persistCeReviewDecisions() {
  localStorage.setItem(CE_REVIEW_STORAGE_KEY, JSON.stringify(state.ceReviewDecisions));
}

async function exportCeReviewJson() {
  const body = {
    schema_version: "0.1.0",
    ledger_type: "cris_sme_ce_human_review_ledger",
    source_console: state.ceReview?.console_name || "CRIS-SME Cyber Essentials Evidence Review Console",
    exported_at: new Date().toISOString(),
    reviewer_model: "human_local_browser",
    note: "Human reviewer decisions only. AI draft acceptance is not counted as human agreement.",
    review_decisions: buildCeReviewExportRows(),
  };
  const payload = {
    ...body,
    integrity: {
      hash_algorithm: "sha256",
      canonical_ledger_sha256: await sha256Stable(body),
      canonical_decisions_sha256: await sha256Stable(body.review_decisions),
      source_review_console_sha256: await sha256Stable(state.ceReview || {}),
      signature_boundary: "Browser export provides deterministic hashes only. Use scripts/sign_ce_review_ledger.py for HMAC signing.",
    },
  };
  downloadText("cris_sme_ce_human_review_ledger.json", JSON.stringify(payload, null, 2), "application/json");
}

function exportCeReviewCsv() {
  const headers = [
    "question_id",
    "review_state",
    "final_answer",
    "final_status",
    "reviewer",
    "reviewed_at",
    "reviewer_note",
    "evidence_reference",
    "override_reason",
  ];
  const rows = buildCeReviewExportRows().map((row) => headers.map((header) => csvCell(row[header] || "")).join(","));
  downloadText("cris_sme_ce_human_review_ledger.csv", [headers.join(","), ...rows].join("\n"), "text/csv");
}

function buildCeReviewExportRows() {
  return (state.ceReview?.entries || []).map((entry) => {
    const decision = entryDecision(entry);
    return {
      question_id: entry.question_id,
      review_state: decision.state || "pending",
      final_answer: decision.final_answer || "pending_human_review",
      final_status: decision.final_status || "pending_human_review",
      reviewer: decision.reviewer || "",
      reviewed_at: decision.reviewed_at || "",
      reviewer_note: decision.reviewer_note || "",
      evidence_reference: decision.additional_evidence_reference || "",
      override_reason: decision.override_reason || "",
    };
  });
}

function downloadText(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function isCloudSupported(entry) {
  return entry.evidence_class === "direct_cloud" || entry.evidence_class === "inferred_cloud";
}

function answerBox(label, value, modifier = "") {
  return `
    <div class="${modifier ? `answer-box-${escapeHtml(modifier)}` : ""}">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `;
}

function ceAnswerHint(entry) {
  const answer = String(entry.proposed_answer || "Cannot determine");
  if (answer === "Yes") {
    return "Bounded evidence support only; no mapped cloud-control-plane issue was observed and human verification is still required.";
  }
  if (answer === "No") {
    return "Mapped CRIS-SME finding evidence supports a conservative No for review.";
  }
  return "Cloud telemetry cannot determine this answer; use endpoint, policy, or manual evidence.";
}

function ceAnswerAdvisory(entry) {
  const answer = String(entry.proposed_answer || "Cannot determine");
  if (answer === "Yes") {
    return {
      title: "Proposed Yes is bounded evidence support",
      body: "CRIS-SME found no mapped cloud-control-plane issue for this question in the available telemetry. This is not proof of Cyber Essentials compliance and still needs human corroboration for scope, endpoint coverage, policy evidence, and false-negative risk.",
    };
  }
  if (answer === "No") {
    return {
      title: "Proposed No is linked to mapped findings",
      body: "The candidate No is supported by CRIS-SME findings or inferred cloud evidence. Review the linked findings and evidence text before accepting or overriding it.",
    };
  }
  return {
    title: "Cannot determine from cloud telemetry",
    body: "This question needs endpoint, MDM, EDR, policy, interview, or administrative evidence before a Cyber Essentials answer can be proposed.",
  };
}

function reviewStateOption(value, selected) {
  return `<option value="${escapeHtml(value)}" ${value === selected ? "selected" : ""}>${escapeHtml(reviewLabel(value))}</option>`;
}

function answerOption(value, selected) {
  return `<option value="${escapeHtml(value)}" ${value === selected ? "selected" : ""}>${escapeHtml(value)}</option>`;
}

function reviewLabel(value) {
  return labelize(value || "pending");
}

function reviewPillClass(value) {
  if (value === "accepted") return "verified";
  if (value === "overridden") return "high";
  if (value === "needs_evidence") return "immediate";
  return "";
}

function csvCell(value) {
  return `"${String(value ?? "").replaceAll('"', '""')}"`;
}

async function sha256Stable(value) {
  const encoded = new TextEncoder().encode(stableStringify(value));
  const digest = await crypto.subtle.digest("SHA-256", encoded);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

function stableStringify(value) {
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableStringify(item)).join(",")}]`;
  }
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
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

function getRiskTrendPoints() {
  const dashboardTrend = state.dashboard?.trend?.overall;
  if (Array.isArray(dashboardTrend) && dashboardTrend.length) return dashboardTrend;
  const reportTrend = state.report?.history_comparison?.overall_trend;
  if (Array.isArray(reportTrend) && reportTrend.length) return reportTrend;
  return [];
}

function ceStatusClass(status) {
  const text = String(status || "").toLowerCase();
  if (text.includes("ready")) return "verified";
  if (text.includes("partial")) return "high";
  if (text.includes("gap")) return "immediate";
  return "info";
}

function buildFindingMarkdown(finding) {
  const breakdown = finding.score_breakdown || {};
  const evidence = Array.isArray(finding.evidence) ? finding.evidence : [];
  const mapping = Array.isArray(finding.mapping) ? finding.mapping : [];
  return [
    `# ${finding.control_id || "Finding"} - ${finding.title || "CRIS-SME finding"}`,
    "",
    `- Finding ID: ${finding.finding_id || "n/a"}`,
    `- Severity: ${finding.severity || "n/a"}`,
    `- Priority: ${finding.priority || "n/a"}`,
    `- Score: ${fmtNumber(finding.score)}`,
    `- Category: ${finding.category || "n/a"}`,
    "",
    "## Evidence",
    evidence.length ? evidence.map((item) => `- ${item}`).join("\n") : "- No evidence statements available.",
    "",
    "## Deterministic Score Breakdown",
    `- Base severity: ${fmtNumber(breakdown.base_severity)}`,
    `- Likelihood factor: ${fmtNumber(breakdown.likelihood_factor)}`,
    `- Data factor: ${fmtNumber(breakdown.data_factor)}`,
    `- Confidence factor: ${fmtNumber(breakdown.confidence_factor)}`,
    `- Remediation factor: ${fmtNumber(breakdown.remediation_factor)}`,
    `- Raw score: ${fmtNumber(breakdown.raw_score)}`,
    `- Normalized score: ${fmtNumber(breakdown.normalized_score)}`,
    "",
    "## Remediation",
    finding.remediation_summary || "No remediation summary available.",
    "",
    "## Mapping",
    mapping.length ? mapping.map((item) => `- ${item}`).join("\n") : "- No mapping available.",
  ].join("\n");
}

async function exportFindingMarkdown(finding) {
  const markdown = buildFindingMarkdown(finding);
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(markdown);
      toast("Finding markdown copied.");
      return;
    }
  } catch {
    // Fall through to file download.
  }
  const blob = new Blob([markdown], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${finding.control_id || "cris-finding"}-${finding.finding_id || "brief"}.md`;
  link.click();
  URL.revokeObjectURL(url);
  toast("Finding markdown exported.");
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

function artifactCard([title, href, type, note]) {
  return `
    <a class="artifact-card" href="${escapeHtml(href)}">
      <span class="artifact-type">${escapeHtml(type)}</span>
      <strong>${escapeHtml(title)}</strong>
      <p>${escapeHtml(note)}</p>
    </a>
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

function publicExposureSeverityClass(severity) {
  const text = String(severity || "").toLowerCase();
  if (text === "high") return "immediate";
  if (text === "medium") return "high";
  if (text === "low") return "verified";
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
