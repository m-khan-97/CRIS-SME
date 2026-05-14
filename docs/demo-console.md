# CRIS-SME Assurance Console

The Assurance Console is a professional interactive frontend for showing CRIS-SME as a unified product experience.

It is intentionally static-first: the deterministic engine still owns assessment generation, scoring, claims, provenance, assurance, and disclosure. The frontend reads generated artifacts and presents them as an interactive SaaS-style workspace.

## Source

`frontend/demo-console/`

## Published Static Site

`dist/site/demo/index.html`

The site builder copies the console into the static bundle and links it from `dist/site/index.html`.

## Data Inputs

The console reads:

- `dist/site/data/cris_sme_dashboard_payload.json`
- `dist/site/data/cris_sme_report.json`
- `dist/site/data/cris_sme_selective_disclosure.json`
- `dist/site/data/cris_sme_ce_self_assessment.json`
- `dist/site/data/cris_sme_ce_review_console.json`
- `dist/site/data/cris_sme_ce_evaluation_metrics.json`
- `dist/site/data/cris_sme_ce_paper_tables.md`

## Console Views

- Command Center
- New Assessment
- Public Exposure
- Findings
- Cyber Essentials
- Human Review
- Evidence Room
- Reports & Artifacts
- Trust Center
- Provenance
- Remediation

## Reports & Artifacts Hub

The console now treats the standalone HTML, JSON, and markdown outputs as governed artifacts inside one product shell. The separate files still exist for export, sharing, and static hosting, but the primary demo path is the unified console.

The artifact hub links to:

- executive and technical reports
- assurance portal
- evidence room
- CE answer pack
- CE review console
- CE evaluation metrics
- machine-readable JSON payloads
- manuscript-ready CE paper tables

## Local Azure Assessment Runner

The console can start a local Azure assessment through a lightweight API runner. This is the first step toward a SaaS-style connect-and-run workflow while keeping credentials out of the browser.

Start the API runner:

```bash
PYTHONPATH=src python3 -m cris_sme.api.local_runner
```

Then open the Assurance Console and use **New Assessment**. The console automatically checks the local runner and current Azure CLI session when the New Assessment view opens. Use **Refresh Azure Connection** only when you have changed `az login`, tenant, subscription, or want to re-run the pre-flight check.

The runner exposes:

- `GET /health`
- `GET /api/environment/azure`
- `POST /api/assessments/azure`
- `POST /api/public-exposure`
- `GET /api/assessments/{run_id}`
- `GET /api/artifacts/latest`

The MVP uses the local machine's existing `az login` session. The frontend never asks for Azure passwords, client secrets, or refresh tokens. Connection checks are automatic, but the assessment itself still requires an explicit authorisation checkbox and manual start action before any live Azure collection begins.

API responses are intentionally structured for the frontend:

- environment checks include `status`, `message`, `error`, `azure_cli_available`, `authenticated`, and `account`
- Azure runs include `run_id`, `status`, `message/error` where relevant, stdout/stderr tails, and artifact paths
- validation errors return `status=failed`, `message`, and `error`
- public exposure runs return `status=completed`, a human-readable `message`, scope notes, findings, targets, and artifact paths

Common states:

- runner unavailable: the browser cannot reach `127.0.0.1:8787`
- CLI missing: Azure CLI is not installed or not on `PATH`
- login needed: Azure CLI exists but `az account show` failed
- run failed: the CRIS-SME subprocess returned a non-zero status; inspect the `stderr_tail` shown in the console

## Public Exposure Mode

The console includes a **Public Exposure** view for explicitly authorised domains, URLs, or public IPs. This view records DNS, HTTP, HTTPS, TLS, redirect, and security-header evidence through the local runner. It does not perform exploitation, crawling, brute force, form submission, or internet-wide scanning.

Outputs are written to:

- `outputs/reports/cris_sme_public_exposure.json`
- `outputs/reports/cris_sme_public_exposure.md`

See [Public Exposure Mode](public-exposure-mode.md) for scope boundaries and finding IDs.

## Cyber Essentials Workflow

The CE workflow view turns the research pipeline into a demo-ready product surface:

- mapped CE question counts
- technical-control coverage
- direct and inferred cloud observability
- endpoint, policy, manual, and not-observable gap taxonomy
- human review state counts
- agreement-rate placeholder for completed reviewer ledgers
- top CRIS-SME controls contributing to CE answer-impact findings
- preview of manuscript-ready CE paper tables

Linked full artifacts:

- `dist/site/ce-self-assessment.html`
- `dist/site/ce-review-console.html`
- `dist/site/ce-evaluation.html`

## CE Review Workbench

The CE Review Workbench is the interactive human-verification surface for the paper workflow.

It loads the generated CE review-console JSON, lets a reviewer accept, override, request evidence, or leave entries pending, and stores decisions locally in the browser. JSON export includes deterministic SHA-256 metadata for the exported browser ledger. CSV export is compatible with `scripts/import_ce_review_ledger.py`.

For signed assurance artifacts, pass the exported JSON or CSV through `scripts/sign_ce_review_ledger.py` and verify it with `scripts/verify_ce_review_ledger.py`.

## Boundary

The Assurance Console does not calculate or modify CRIS-SME risk scores.

It is a presentation and exploration layer over deterministic backend outputs.
