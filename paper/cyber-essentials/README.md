# Cyber Essentials Paper Package

This folder is the working paper package for:

**Evidence-Sufficiency-Aware Cyber Essentials Pre-Population From Cloud Control-Plane Telemetry**

## Contents

- `main.md` - first full manuscript draft
- `references.bib` - starter bibliography and related-work sources to verify
- `submission-plan.md` - venue plan, remaining blockers, and claim discipline
- `review-ledger-template.csv` - 28 cloud-supported entries for independent human review
- `review-ledger-completed.csv` - imported reviewer workbook, normalized from the completed review spreadsheet
- `review-ledger-validation.md` - validation status for the completed review against the current controlled-lab answer pack
- `review-ledger-revalidation-required.csv` - rows whose original reviewer entries require revalidation
- `review-ledger-revalidation-with-evidence.csv` - reviewer-facing revalidation CSV with linked CRIS-SME evidence
- `review-ledger-revalidation-marked-whole-set.csv` - normalized revalidation workbook supplied after evidence review
- `review-ledger-current-provisional.csv` - merged 28-row provisional ledger using the revalidated rows
- `review-ledger-revalidation-summary.md` - import summary and interpretation of the revalidation workbook
- `revalidation-evidence-pack.md` - readable evidence pack for the revalidation rows
- `tables/results-summary.md` - frozen paper tables from current artifacts
- `tables/results-summary.csv` - CSV version of headline results
- `figures/` - four SVG figures for paper drafting

## Current Status

Paper readiness:

- strong workshop draft
- journal draft still needs external reviewer cross-check and competitor check

Do not claim final independent reviewer agreement yet. A completed reviewer ledger and a revalidation workbook have been imported, and the merged provisional ledger now has `23` accepted rows and `5` needs-evidence rows. However, the revalidation workbook states that external human cross-check is still pending, so this should be reported as provisional revalidation rather than final independent agreement.

## Immediate Next Step

Ask the CE-knowledgeable reviewer to externally cross-check `review-ledger-current-provisional.csv` against `revalidation-evidence-pack.md`.

That cross-check turns the provisional merged ledger into a final empirically reportable controlled-lab result.

Import the completed ledger with:

```bash
PYTHONPATH=src python3 scripts/import_ce_review_ledger.py \
  --answer-pack outputs/reports/azure_controlled_lab/cris_sme_ce_self_assessment.json \
  --ledger paper/cyber-essentials/review-ledger-template.csv \
  --output-dir outputs/reports/azure_controlled_lab/ce_review_import
```

Then create a hash-bound reviewer ledger for reproducibility:

```bash
PYTHONPATH=src python3 scripts/sign_ce_review_ledger.py \
  --answer-pack outputs/reports/azure_controlled_lab/cris_sme_ce_self_assessment.json \
  --ledger paper/cyber-essentials/review-ledger-template.csv \
  --output outputs/reports/azure_controlled_lab/cris_sme_ce_human_review_ledger.signed.json \
  --reviewer-name "Reviewer Name" \
  --reviewer-role "CE-knowledgeable reviewer"
```

Verification:

```bash
PYTHONPATH=src python3 scripts/verify_ce_review_ledger.py \
  --ledger outputs/reports/azure_controlled_lab/cris_sme_ce_human_review_ledger.signed.json \
  --answer-pack outputs/reports/azure_controlled_lab/cris_sme_ce_self_assessment.json
```

Set `CRIS_SME_CE_REVIEW_SIGNING_KEY` when an HMAC signature is required. Hash-bound ledgers are enough for reproducibility; signed ledgers add shared-secret authenticity for controlled assurance workflows.
