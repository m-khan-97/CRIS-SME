# CRIS-SME React Assurance Console

A React + TypeScript + Vite + Tailwind console that presents CRIS-SME's deterministic
assessment artifacts as an interactive workspace. It is a **presentation layer only**:
it never computes, re-ranks, or invents scores, findings, priorities, or confidence
values. Every figure shown is read directly from the generated report; if a field is
absent, the UI renders an empty/"not observed" state instead of guessing.

## Source

`frontend/console/`

## Local Development

```bash
cd frontend/console
npm install
npm run dev
```

The dev server proxies `/api`, `/outputs`, and `/health` to the local API runner at
`http://127.0.0.1:8787` (see `src/cris_sme/api/local_runner.py`).

## Static Build

```bash
cd frontend/console
npm run build
```

Production builds use `base: "/console/"` (see `vite.config.ts`) so the bundle can be
dropped into `dist/site/console/` alongside the existing static demo console.
`scripts/build_pages_site.py`:

- copies `frontend/console/dist/` into `dist/site/console/`
- copies every file in `outputs/reports/` into `dist/site/console/outputs/` so the
  console can fetch `cris_sme_report.json` and any `report_artifacts` (SARIF, CSV,
  remediation script pack, etc.) at runtime with no backend
- writes `dist/site/console/404.html` (copy of `index.html`) and a root
  `dist/site/vercel.json` rewrite rule (`/console/(.*) -> /console/index.html`) so
  client-side routes resolve on static hosts
- links the console from `dist/site/index.html`

`scripts/build_static_site_bundle.py` (used by CI) runs `npm run build` in
`frontend/console/` before assembling the Pages bundle.

## Data Contract

The console fetches a single artifact, `console/outputs/cris_sme_report.json`
(via `getLatestReport()` in `src/api/client.ts`), and reads top-level sections of
that report defensively via `(report ?? {}) as Record<string, any>` casts. Pages
degrade gracefully (via `EmptyState`/`Spinner`) when a section is missing, so the
console keeps working as the report schema grows.

`artifactUrl()` resolves `report_artifacts` paths (which are repo-relative, e.g.
`outputs/reports/cris_sme_report.sarif`) to `console/outputs/<file>` for direct
download links.

## Views

| Route | Page | Payload sections used |
| --- | --- | --- |
| `/` | Overview | `executive_overview`, `domain_breakdown`, `trend` |
| `/personas` | Personas | persona-specific summaries |
| `/assessment` | New Assessment | `/api/assessments/azure`, `/api/public-exposure` |
| `/findings` | Findings | `finding_explorer` |
| `/resources` | Resources | asset/resource inventory |
| `/attack-paths` | Attack Paths | `graph_context` |
| `/compliance` | Compliance | `compliance_readiness` |
| `/cyber-essentials` | Cyber Essentials | `cyber_essentials_readiness`, `cyber_essentials_self_assessment`, `cyber_essentials_evaluation_metrics`, `cyber_essentials_review_console` |
| `/remediation` | Remediation | `budget_aware_remediation`, `action_plan_30_day`, `remediation_simulation`, `report_artifacts.remediation_script_pack` |
| `/evidence` | Evidence & Provenance | `decision_provenance_graph`, `decision_review_queue`, `control_drift_attribution`, `evidence_gap_backlog`, `confidence_calibration`, `collector_coverage`, `provider_evidence_contracts` |
| `/trust` | Trust Center | `report_trust_badge`, `assurance_case`, `assessment_assurance`, `claim_bound_narrative`, `claim_verification_pack`, `risk_bill_of_materials`, `decision_ledger` |
| `/disclosure` | Disclosure Room | `selective_disclosure` |
| `/reports` | Reports & Artifacts | `report_artifacts` |
| `/trend` | Trend & History | `risk_drift_analysis`, `history_comparison` |
| `/governance` | Exceptions & Governance | `finding_lifecycle_summary`, `prioritized_risks[].lifecycle` |
| `/native-validation` | Native Validation | `native_validation` |
| `/public-exposure` | Public Exposure | `/api/public-exposure` |

### Cyber Essentials Review Workbench

The Cyber Essentials page's "Review workbench" tab is the React equivalent of the
demo console's human-review feature. For each of the ~106 entries in
`cyber_essentials_review_console.entries`, a reviewer can set a decision
(`pending` / `accepted` / `needs_evidence` / `overridden`, per
`cyber_essentials_review_console.review_policy.allowed_review_states`), add a
reviewer name and note, and (for overrides) an override reason.

- Decisions persist in the browser via `localStorage`
  (`cris_sme_ce_human_review_ledger_v1`).
- "Export JSON" / "Export CSV" produce a ledger of all 106 entries with the
  reviewer's decisions, including a `canonical_ledger_sha256` over the JSON export
  computed with `crypto.subtle.digest`.
- The workbench prominently displays
  `cyber_essentials_review_console.review_policy.score_boundary`: reviewer
  decisions change the CE review ledger only — they never change CRIS-SME's
  deterministic findings, priorities, or scores.

For signed assurance artifacts, pass the exported JSON or CSV through
`scripts/sign_ce_review_ledger.py` and verify it with
`scripts/verify_ce_review_ledger.py`. CSV export is compatible with
`scripts/import_ce_review_ledger.py`.

## Local Azure Assessment Runner

The "New Assessment" view starts a local Azure assessment through a lightweight
API runner, keeping credentials out of the browser:

```bash
PYTHONPATH=src python3 -m cris_sme.api.local_runner
```

The runner exposes `GET /health`, `GET /api/environment/azure`,
`POST /api/assessments/azure`, `POST /api/public-exposure`,
`GET /api/assessments/{run_id}`, and `GET /api/artifacts/latest`. It uses the
local machine's existing `az login` session; the console never asks for Azure
passwords, client secrets, or refresh tokens, and live collection requires an
explicit authorisation checkbox before it starts.

The "Public Exposure" view runs the same runner against explicitly authorised
domains, URLs, or public IPs (DNS/HTTP/HTTPS/TLS/header evidence only — no
exploitation, crawling, brute force, or internet-wide scanning). See
[Public Exposure Mode](public-exposure-mode.md) for scope boundaries and finding
IDs.

## Boundary

The Assurance Console does not calculate or modify CRIS-SME risk scores. It is a
presentation and exploration layer over deterministic backend outputs; if a field
is absent from the report, the UI renders an "unavailable" / "not observed" state
rather than inferring a value.
