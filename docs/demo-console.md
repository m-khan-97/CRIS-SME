# CRIS-SME Demo Console

The Demo Console is a professional interactive frontend for showing CRIS-SME as a product experience.

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

## Demo Views

- Overview
- Decision Workbench
- Provenance
- Assurance Center
- Cyber Essentials Workflow
- CE Review Workbench
- Disclosure Room
- Remediation

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

The Demo Console does not calculate or modify CRIS-SME risk scores.

It is a presentation and exploration layer over deterministic backend outputs.
