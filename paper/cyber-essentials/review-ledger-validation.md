# Human Review Ledger Validation

Source workbook: `/home/muhammad-ibrahim/Downloads/review-ledger-completed.xlsx`

Normalized ledger: `paper/cyber-essentials/review-ledger-completed.csv`

Validated against answer pack: `outputs/reports/azure_controlled_lab/cris_sme_ce_self_assessment.json`

## Summary

- Reviewed rows: `28`
- Accepted rows in reviewer ledger: `18`
- Needs-evidence rows in reviewer ledger: `10`
- Rows aligned with current controlled-lab answer pack: `20`
- Rows requiring revalidation: `8`

## Interpretation

The reviewer completed the 28-row cloud-supported ledger, but `8` row(s) do not match the current controlled-lab answer pack's `evidence_class`, `proposed_status`, or `proposed_answer`. These rows must not be counted as final human agreement for the controlled-lab paper results until the reviewer re-confirms them against the current answer pack.

A revalidation CSV has been written to `paper/cyber-essentials/review-ledger-revalidation-required.csv`.

Reviewer-facing evidence has also been prepared:

- Markdown evidence pack: `paper/cyber-essentials/revalidation-evidence-pack.md`
- CSV evidence pack: `paper/cyber-essentials/review-ledger-revalidation-with-evidence.csv`

These evidence packs include the current proposed answer, evidence class, mapped controls, linked finding IDs, finding titles, scores, evidence statements, and source artifact paths for each of the `8` rows requiring revalidation.

## Aligned Rows

The aligned subset contains `20` row(s). For the controlled-lab answer pack, this subset contains `15` accepted row(s) and `5` needs-evidence row(s).

## Revalidation Workbook Received

The workbook `/home/muhammad-ibrahim/Downloads/review-ledger-revalidation-marked-whole-set.xlsx` was normalized to `paper/cyber-essentials/review-ledger-revalidation-marked-whole-set.csv`.

It marks all `8` revalidation rows as `accepted` with final answer `No`, matching the current controlled-lab answer pack. The user has clarified that this workbook is the final human cross-check. A merged final 28-row ledger has been written to `paper/cyber-essentials/review-ledger-current-final.csv`.

The final import produced:

- Accepted rows: `23`
- Needs-evidence rows: `5`
- Accepted rows matching CRIS-SME proposed answer: `23` of `23`
- Hash-bound ledger verification: `passed`

## Paper Claim

The final human cross-check supports reporting `23` accepted agreement-evaluable rows, all matching the current CRIS-SME proposed answer, with `5` rows held as `needs_evidence`. The agreement claim should remain bounded to the controlled-lab answer pack and the cloud evidence surfaced in the review ledger; it is not a Cyber Essentials certification claim.
