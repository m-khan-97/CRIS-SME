# CRIS-IoMT Expert Review Pack

This folder is a compact expert-review bundle for:

**CRIS-IoMT: Evidence-Driven Cloud Governance Assessment for Cloud-Connected Healthcare IoT Systems**

The pack is designed for a healthcare IoT, sensing, biomedical engineering, cyber-physical systems, or cyber assurance expert to review the work without reading the full repository.

## Suggested Review Order

1. `00-cover-brief.md`
2. `01-paper-summary.md`
3. `02-control-matrix.md`
4. `03-evidence-boundary.md`
5. `04-evaluation-results.md`
6. `05-related-work-comparison.md`
7. `06-expert-review-ledger.csv`
8. `07-review-request-message.md`

## Review Objective

The requested review is not a full paper peer review. The goal is to validate whether the CRIS-IoMT control model, evidence boundary, and candidate NHS DSPT / NCSC CAF mappings are scientifically and healthcare-operationally credible.

## Preferred Feedback

Please focus on:

- whether the `IOT-*` controls are meaningful healthcare IoT governance signals
- whether the evidence classes are appropriately bounded
- whether candidate DSPT/CAF mappings are reasonable or need revision
- what would make the work stronger for IEEE JBHI, IEEE Sensors, IEEE IoT Journal, HealthCom, or a healthcare cyber venue

## Review Ledger Values

Use the following values in `06-expert-review-ledger.csv` where possible:

- `healthcare_relevance`: `high`, `medium`, `low`
- `evidence_sufficiency`: `sufficient`, `partial`, `insufficient`
- `dspt_caf_mapping_validity`: `valid`, `needs_revision`, `invalid`
- `review_decision`: `accept`, `revise`, `reject`

Free-text comments are welcome in `reviewer_comment`, especially where a control or mapping should be reframed.
