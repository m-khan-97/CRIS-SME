# Frontend Gap Analysis (historical)

> **Status: superseded.** `frontend/demo-console/` has been removed and
> `frontend/console/` (the React Assurance Console) now covers the gaps
> identified below, including Trend & History (`/trend`), Exceptions &
> Governance (`/governance`), and Native Validation (`/native-validation`).
> See [frontend-console.md](frontend-console.md) for the current console.
> This document is kept as a record of the original Phase 0 audit.

Phase 0 audit for the CRIS-SME console rebuild. Covers: (A) what the current
UIs render vs. what the deterministic artifacts already contain, (B) a
capability-by-capability benchmark against Wiz, Vanta, Drata, and Microsoft
Defender for Cloud, and (C) an honest verdict with the highest-leverage next
steps.

There are currently **two** frontends in the repo:

- `frontend/demo-console/` — static vanilla HTML/CSS/JS, reads JSON files
  copied into `dist/site/data/`, ships in the Pages bundle via
  `scripts/build_pages_site.py`. Covered by `tests/test_demo_console_assets.py`.
- `frontend/console/` — Vite + React + TypeScript + Tailwind, talks to the
  local API runner (`cris_sme.api.local_runner`) plus `getLatestReport()` for
  `outputs/reports/cris_sme_report.json`. Routes today: Overview, New
  Assessment, Findings, Resources, Attack Paths, Personas, Compliance, Public
  Exposure. Not yet built into `dist/site`.

Both read from the same underlying deterministic artifacts
(`cris_sme_report.json` / `cris_sme_dashboard_payload.json`), so the gap
analysis below treats "the console" as the union of capability that needs to
exist in `frontend/console/` to reach (and exceed) demo-console parity, since
that is the React app this build will extend.

---

## A. Internal inventory — payload contract vs. what is rendered

`docs/dashboard.md` defines 8 payload sections; the actual
`cris_sme_dashboard_payload.json` has grown to 22 top-level sections. Mapping
each against the two existing UIs:

| Payload section | demo-console | frontend/console (React) | Notes |
|---|---|---|---|
| `executive_overview` | `renderOverview` — score, band, top business risks, priority counts | `Overview.tsx` — overall score, category scores, top risks | React lacks `risk_band`, `framework_coverage_count`, `provider_coverage_count`, `confidence_summary` |
| `domain_breakdown` | `renderDomainBars` | `Overview.tsx` category score list | React doesn't show per-domain finding counts |
| `trend` | `renderRiskTrendSparkline` | **none** | `history_comparison` / `risk_drift_analysis` exist in `cris_sme_report.json` but no React view consumes them |
| `finding_explorer` | `renderFindingTable` + `renderFindingDetail` + `renderScoreBreakdownGrid` | `Findings.tsx` — sortable/filterable table + drawer | React drawer lacks `evidence_quality` full breakdown (direct/inferred/unavailable counts), lifecycle status, confidence rationale fields present in `PrioritizedRisk` |
| `compliance_readiness` | `renderCeWorkflow` + framework view | `Compliance.tsx` — frameworks_covered, findings_by_framework, control_reference_counts | React doesn't surface `uk_profile` (Cyber Essentials/DSPT/FCA SYSC/UK GDPR) or CE pillar readiness as a dedicated view (only partial in `Personas.tsx` owner briefing) |
| `confidence_and_evidence` | partially via `renderScoreBreakdownGrid` | **none** | Confidence calibration status counts, evidence sufficiency counts, collector coverage, provider evidence contract summary — not surfaced anywhere in React |
| `graph_context` | `renderGraphCanvas` (toxic combos, exposure chains) | `AttackPaths.tsx` — assets/relationships graph + blast radius drawer | React graph doesn't list `toxic_combinations` or `top_exposure_chains` as text/cards, only embeds them implicitly via the asset graph |
| `remediation` | `renderRemediation` + `renderSimulationResult` | **none** | Budget profiles, 30-day action plan, remediation simulation scenarios, quick wins — all backend-complete (`remediation_simulation`, `budget_aware_remediation`, `action_plan_30_day`, `report_artifacts.remediation_script_pack`) but **zero** React surface |
| `exceptions_and_governance` | status counts only | **none** | `finding_lifecycle_summary`, mute rules (`data/mute_rules.json`), `adjusted_risk_scores`, exception registry — backend-complete (this session's earlier work, items 6/11/12), no UI |
| `decision_ledger` | `renderProvenance` (partial) | **none** | Event counts, latest events — not shown |
| `decision_review_queue` | `renderProvenance` (partial) | **none** | 128 review items, priority/decision-type breakdowns — not shown |
| `decision_provenance_graph` | `renderProvenance` + `renderGraphCanvas` | **none** | 233 nodes / 354 edges of provenance — not shown |
| `claim_verification_pack` | `renderAssurance` | **none** | 21 claims, verification status — not shown |
| `assurance_case` | `renderAssurance` | **none** | Argument-level assurance case — not shown |
| `claim_bound_narrative` | `renderAssurance` | **none** | Narrative sections cited to claims — not shown |
| `control_drift_attribution` | `renderProvenance` (partial) | **none** | Drift attribution vs. previous run — not shown |
| `assessment_assurance` | `renderAssurance` | `Personas.tsx` assessor briefing (partial) | Only assurance score/level shown; signals list with pass/gap not in React |
| `report_trust_badge` | `renderAssurance` | `Personas.tsx` (badge label/level only) | Full badge fields (replay_verified, rbom_present, provider_conformance_passed, high_priority_evidence_gaps) not shown |
| `native_validation` | `renderProvenance` (partial) | **none** | Defender-for-Cloud cross-validation — not shown |
| `artifacts` / `report_artifacts` | `renderReportsHub` | **none** | Full artifact hub (24+ generated files incl. SARIF, OCSF, CSV, remediation script pack) — no React equivalent |
| `selective_disclosure` (separate JSON) | `renderDisclosure` + `renderDisclosureTabs` | **none** | 5 disclosure rooms, share manifest, RBOM hash, guardrails — not shown |
| `cyber_essentials_self_assessment` / `_review_console` / `_evaluation_metrics` | `renderCeWorkflow`, `renderCeReviewWorkbench` (+ localStorage human-review ledger, CSV/JSON export with SHA-256) | **none** | 106-question CE pack, interactive human review workbench with persisted decisions and signed export — entirely absent from React |
| `evidence_gap_backlog` | not rendered in either | **none** | 110-item backlog with priority/domain breakdowns — unused by both UIs |
| MCP tools (item 11, this session) | n/a | n/a | Backend-only; no UI consumption expected (AI/agent surface, not a console view) |

**Headline finding:** `frontend/console/` (React) currently covers roughly
**2 of 22** payload sections at meaningful depth (Findings, partial Overview)
plus a differentiated Personas layer that demo-console doesn't have. The
remaining ~18 sections — most notably **Remediation**, **Trust/Assurance**,
**Provenance**, **Evidence Room/Disclosure**, **Cyber Essentials + Review
Workbench**, and **Confidence & Evidence** — exist in the deterministic
artifacts and are rendered by demo-console but have no React equivalent yet.

---

## B. Benchmark against industry standard

### Wiz (CNAPP)

| Wiz capability | CRIS-SME has the data? | Surfaced today? | Gap | Priority |
|---|---|---|---|---|
| Security graph that humanises risk visually | Yes — `resource_context.assets` + `relationships`, `graph_context` | Partial (`AttackPaths.tsx`, React only) | Toxic combinations / exposure chains not rendered as first-class cards; not in static bundle | P1 |
| Single prioritised issues list ranked by business impact | Yes — `prioritized_risks` with score/priority | Yes (`Findings.tsx`) | Missing lifecycle status & confidence-driven "why this rank" explanation | P2 |
| Explicit "best next action" | Yes — `remediation_summary`, `action_plan_30_day`, `decision_review_queue.recommended_decision` | No | No remediation/action view at all | P1 |
| Unified multi-cloud posture + compliance dashboards | Partial — provider-neutral model, Azure-first live data | Partial (`Compliance.tsx` covers generic frameworks only) | UK profile (CE/DSPT/FCA SYSC/UK GDPR) and CE pillar readiness not shown | P1 |
| Blast-radius / exposure-chain context | Yes — `graph_context.blast_radius`, `toxic_combinations`, `top_exposure_chains` | Partial (blast radius drawer only) | Toxic combos & exposure chains missing | P2 |

### Vanta

| Vanta capability | Data exists? | Surfaced? | Gap | Priority |
|---|---|---|---|---|
| Live controls dashboard, pass/fail per control with monitoring status | Yes — `prioritized_risks` per `control_id`, `finding_lifecycle_summary` | No dedicated control-status view | Need a controls table (control_id → status → last evaluated → lifecycle) | P1 |
| Framework crosswalk views | Yes — `compliance.frameworks_covered`, `findings_by_framework`, `uk_profile` | Partial (`Compliance.tsx`, generic only) | UK crosswalk + CE pillar mapping missing | P1 |
| Public Trust Center | Yes — `report_trust_badge`, `assurance_case`, `claim_bound_narrative`, RBOM hash | No | This is the single biggest "credibility" gap vs. competitors | P1 |
| Security-questionnaire auto-answer | Yes — `cyber_insurance_evidence.questions`, CE self-assessment pack | Partial (Personas insurer briefing only) | No dedicated questionnaire/answer-pack view | P2 |

### Drata

| Drata capability | Data exists? | Surfaced? | Gap | Priority |
|---|---|---|---|---|
| Centralised Audit Hub (evidence + docs + collaboration) | Yes — `selective_disclosure`, `report_artifacts`, `resource_context.evidence_records` | No | No evidence/artifact hub in React | P1 |
| Real-time evidence collection with freshness | Yes — `collector_coverage`, `evidence_snapshot`, `run_metadata` | No | Not shown | P2 |
| Alerting on control drift | Yes — `control_drift_attribution`, `decision_ledger` | No | Not shown; this is a strong CRIS differentiator (deterministic drift attribution) currently invisible | P1 |

### Microsoft Defender for Cloud

| Defender capability | Data exists? | Surfaced? | Gap | Priority |
|---|---|---|---|---|
| Secure-score gauge | Yes — `overall_risk_score`, `report_trust_badge.assurance_score` | Yes, basic ring (`Overview.tsx`, `Personas.tsx`) | No band/trend context alongside the gauge | P3 |
| Recommendations grouped by control | Yes — `prioritized_risks` grouped by `control_id`/`category` | Partial (flat table only) | No control-grouped view | P2 |
| Regulatory compliance view | Yes — `compliance`, `cyber_essentials_readiness`, `native_validation` | Partial | Native validation (Defender cross-check) entirely unused | P2 |

---

## C. Honest verdict

**Where CRIS-SME sits below industry standard today:**

The React console (`frontend/console/`) is a solid, well-structured start —
its component library (`ui.tsx`), data-fetching pattern, and the new Personas
layer are genuinely good and *better* than what demo-console offers for
role-based framing. But as a whole product it is **not yet at parity with
demo-console**, let alone the benchmark tools, because:

1. There is **no Trust Center / Assurance view**. This is the single highest
   credibility gap — Vanta's entire pitch is built around it, and CRIS-SME
   already computes everything needed (`report_trust_badge`, `assurance_case`,
   `claim_bound_narrative`, `assessment_assurance`, RBOM hash).
2. There is **no Remediation / "best next action" view**. Wiz's headline
   feature and CRIS-SME's stated SME differentiator (affordability-aware
   remediation) are fully computed (`budget_aware_remediation`,
   `remediation_simulation`, `action_plan_30_day`,
   `report_artifacts.remediation_script_pack`) but invisible.
3. There is **no Evidence/Provenance/Disclosure hub**. Drata's Audit Hub
   analogue — `selective_disclosure`, `decision_provenance_graph`,
   `decision_review_queue`, `evidence_gap_backlog` — all exist, none rendered.
4. **Cyber Essentials is only partially surfaced** (readiness ring in
   Personas), and the **CE Review Workbench — a genuinely novel,
   audit-grade interaction (human review + signed export ledger) — has no
   React equivalent at all**.
5. **Confidence & evidence quality** (calibration status, direct vs inferred,
   provider evidence contracts) — a core "we don't hide uncertainty"
   differentiator per `docs/security-trust-model.md` — has no view.
6. The React console is **not in the static build** (`scripts/build_pages_site.py`
   only knows about `frontend/demo-console/`), so even what exists today can't
   replace the static site yet.

**The 6 highest-leverage changes, in order:**

1. **Trust/Assurance Center** — `report_trust_badge` + `assurance_case` +
   `claim_bound_narrative` + `assessment_assurance` + RBOM integrity. Closes
   the single biggest credibility gap vs. Vanta with data that is 100% ready.
2. **Remediation view** — budget profiles, 30-day action plan, simulation
   scenarios, quick wins, link to remediation script pack. This is Wiz's
   "best next action" and CRIS-SME's stated SME differentiator.
3. **Evidence & Provenance hub** — `decision_provenance_graph` summary,
   `decision_review_queue`, `control_drift_attribution`, `evidence_gap_backlog`,
   collector coverage / confidence calibration. Drata-equivalent, evidence-first.
4. **Cyber Essentials + Review Workbench** — readiness pillars, self-assessment
   coverage, evaluation metrics, and the interactive human-review ledger with
   localStorage persistence + signed CSV/JSON export (the most novel CRIS-SME
   UI feature, currently locked inside demo-console only).
5. **Selective Disclosure / Evidence Room** — the 5 disclosure profiles +
   share manifest, framed for auditors/insurers/MSPs — ties directly into the
   Personas layer already built.
6. **Reports & Artifacts hub + static build wiring** — surface
   `report_artifacts` as a browsable hub, and get `frontend/console/` building
   into `dist/site` so it can eventually replace `frontend/demo-console/`
   without losing the asset-contract guarantees in
   `tests/test_demo_console_assets.py`.

Two secondary gaps worth tracking but not blocking: trend/drift sparkline
(`trend` section) and a control-grouped findings view (Defender-style).

**Recommendation:** build items 1–4 as new routes in `frontend/console/`
first (highest data-readiness, highest differentiation), then 5–6. Only
remove `frontend/demo-console/` once the React console reaches functional
parity on all 22 payload sections it can reasonably host *and* the static
build is wired up — per the constraint to keep demo-console working until
parity is reached.
