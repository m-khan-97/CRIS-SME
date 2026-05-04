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

## Demo Views

- Overview
- Decision Workbench
- Provenance
- Assurance Center
- Disclosure Room
- Remediation

## Boundary

The Demo Console does not calculate or modify CRIS-SME risk scores.

It is a presentation and exploration layer over deterministic backend outputs.
