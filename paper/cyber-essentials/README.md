# Cyber Essentials Paper Package

This folder is the working paper package for:

**Evidence-Sufficiency-Aware Cyber Essentials Pre-Population From Cloud Control-Plane Telemetry**

## Contents

- `main.md` - first full manuscript draft
- `references.bib` - starter bibliography and related-work sources to verify
- `related-work-competitor-check.md` - checked competitor/related-work notes and defensible novelty claim
- `submission-plan.md` - venue plan, remaining blockers, and claim discipline
- `review-ledger-template.csv` - 28 cloud-supported entries for independent human review
- `review-ledger-completed.csv` - imported reviewer workbook, normalized from the completed review spreadsheet
- `review-ledger-validation.md` - validation status for the completed review against the current controlled-lab answer pack
- `review-ledger-revalidation-required.csv` - rows whose original reviewer entries require revalidation
- `review-ledger-revalidation-with-evidence.csv` - reviewer-facing revalidation CSV with linked CRIS-SME evidence
- `review-ledger-revalidation-marked-whole-set.csv` - normalized final human cross-check workbook supplied after evidence review
- `review-ledger-current-final.csv` - merged 28-row final review ledger using the revalidated rows
- `review-ledger-revalidation-summary.md` - import summary and interpretation of the revalidation workbook
- `revalidation-evidence-pack.md` - readable evidence pack for the revalidation rows
- `tables/results-summary.md` - frozen paper tables from current artifacts
- `tables/results-summary.csv` - CSV version of headline results
- `figures/` - four SVG figures for paper drafting

## Current Status

Paper readiness:

- strong workshop draft
- journal draft still needs final venue formatting; a second reviewer or second live tenant would strengthen the evaluation

The completed reviewer ledger and final human cross-check workbook have been imported. The merged final ledger has `23` accepted rows and `5` needs-evidence rows. All `23` accepted rows match the current CRIS-SME proposed answers.

## Immediate Next Step

Use `review-ledger-current-final.csv` as the reviewed ledger for the controlled-lab evaluation.

The final reviewer result is empirically reportable as `23` of `23` accepted answers agreeing with CRIS-SME, with `5` rows remaining as needs-evidence rather than agreement-evaluable decisions.

## Consistency Checks

The paper package is checked in CI with:

```bash
PYTHONPATH=src:. python scripts/validate_paper_package.py
```

The validator parses paper SVGs and CSVs, checks local Markdown links, blocks stale provisional-review wording, and verifies that final human agreement remains separated from AI-assisted draft acceptance.

Import the completed ledger with:

```bash
PYTHONPATH=src python3 scripts/import_ce_review_ledger.py \
  --answer-pack outputs/reports/azure_controlled_lab/cris_sme_ce_self_assessment.json \
  --ledger paper/cyber-essentials/review-ledger-current-final.csv \
  --output-dir outputs/reports/azure_controlled_lab/ce_review_final
```

Then create a hash-bound reviewer ledger for reproducibility:

```bash
PYTHONPATH=src python3 scripts/sign_ce_review_ledger.py \
  --answer-pack outputs/reports/azure_controlled_lab/cris_sme_ce_self_assessment.json \
  --ledger paper/cyber-essentials/review-ledger-current-final.csv \
  --output outputs/reports/azure_controlled_lab/ce_review_final/cris_sme_ce_review_ledger_final.signed.json \
  --reviewer-name "Reviewer-CRIS-SME-01" \
  --reviewer-role "CE-knowledgeable human reviewer"
```

Verification:

```bash
PYTHONPATH=src python3 scripts/verify_ce_review_ledger.py \
  --ledger outputs/reports/azure_controlled_lab/ce_review_final/cris_sme_ce_review_ledger_final.signed.json \
  --answer-pack outputs/reports/azure_controlled_lab/cris_sme_ce_self_assessment.json
```

Set `CRIS_SME_CE_REVIEW_SIGNING_KEY` when an HMAC signature is required. Hash-bound ledgers are enough for reproducibility; signed ledgers add shared-secret authenticity for controlled assurance workflows.
