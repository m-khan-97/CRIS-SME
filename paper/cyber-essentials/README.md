# Cyber Essentials Paper Package

This folder is the working paper package for:

**Evidence-Sufficiency-Aware Cyber Essentials Pre-Population From Cloud Control-Plane Telemetry**

## Contents

- `main.md` - first full manuscript draft
- `references.bib` - starter bibliography and related-work sources to verify
- `submission-plan.md` - venue plan, remaining blockers, and claim discipline
- `review-ledger-template.csv` - 28 cloud-supported entries for independent human review
- `tables/results-summary.md` - frozen paper tables from current artifacts
- `tables/results-summary.csv` - CSV version of headline results
- `figures/` - four SVG figures for paper drafting

## Current Status

Paper readiness:

- strong workshop draft
- journal draft still needs independent human review and competitor check

Do not claim independent reviewer agreement yet. The AI-assisted ledger is reported only as draft acceptance.

## Immediate Next Step

Ask one CE-knowledgeable reviewer to complete `review-ledger-template.csv`.

That single review pass turns the evaluation section from pilot-only to empirically reportable.

Import the completed ledger with:

```bash
PYTHONPATH=src python3 scripts/import_ce_review_ledger.py \
  --answer-pack outputs/reports/azure_controlled_lab/cris_sme_ce_self_assessment.json \
  --ledger paper/cyber-essentials/review-ledger-template.csv \
  --output-dir outputs/reports/azure_controlled_lab/ce_review_import
```
