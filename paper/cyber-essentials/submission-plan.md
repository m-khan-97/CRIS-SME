# Submission Plan

## Target

Primary target:

- Computers & Security

Workshop / practitioner alternatives:

- EuroS&P workshop
- USENIX Enigma
- NCSC-adjacent UK cyber security venues
- SOUPS, if a reviewer/user study is added

## Paper Positioning

Use this title:

**Evidence-Sufficiency-Aware Cyber Essentials Pre-Population From Cloud Control-Plane Telemetry**

Avoid:

- Automated Cyber Essentials certification
- Fully automated CE self-assessment
- AI assessor

Use:

- evidence support
- pre-population
- human-reviewable answer pack
- evidence sufficiency
- explicit observability boundaries

## Current Readiness

Ready:

- 106-entry paraphrased CE mapping
- six-class evidence taxonomy
- Azure-first answer pack
- proposed answer derivation
- controlled Azure vulnerable-lab run
- AI-assisted pilot review draft
- completed human review ledger imported
- revalidation evidence pack prepared for 8 stale rows
- final merged review ledger produced and hash-bound
- paper package consistency checks in CI
- reproducible CE paper figure generation from metrics JSON
- paper tables and figures

Still required before journal submission:

- final venue formatting
- optional second reviewer or second live tenant if targeting a stronger empirical venue

## Human Review Task

Use `review-ledger-current-final.csv` as the final human-reviewed controlled-lab ledger.

Reviewer states included in the ledger are:

- `accepted`
- `overridden`
- `needs_evidence`

They should fill:

- final answer
- reviewer note
- evidence reference
- override reason when relevant

The evidence pack for revalidation is `revalidation-evidence-pack.md`. The final claim should remain bounded: reviewed agreement over CRIS-SME's cloud-evidence answer pack, not Cyber Essentials certification.

## Competitor Check

Completed in `related-work-competitor-check.md`.

- Microsoft Defender for Cloud
- Prowler
- ScoutSuite
- Vanta
- JumpCloud
- CE FastTrack
- IASME/NCSC self-assessment workflow
- ConnectWise / Datto / NinjaRMM style MSP tooling
- Axonius-style compliance mapping

Expected defensible claim:

> To our knowledge, the checked public tools do not provide the same combination of UK Cyber Essentials question-level answer pre-population, live cloud-control-plane evidence lineage, explicit evidence-sufficiency labels, and review-ledger separation between deterministic evidence and human attestation.

## Figure Plan

Use the figures in `figures/`:

- `ce-evidence-class-distribution.svg`
- `ce-proposed-answer-distribution.svg`
- `azure-category-score-comparison.svg`
- `ce-workflow.svg`

## Final Pre-Submission Checklist

- Refresh all metrics from a frozen run.
- Confirm no generated table reports AI draft acceptance as human agreement.
- Run `PYTHONPATH=src:. python scripts/validate_paper_package.py`.
- Regenerate figures with `PYTHONPATH=src:. python scripts/generate_ce_paper_figures.py` after refreshing metrics.
- Report final human agreement only over agreement-evaluable accepted/overridden rows, excluding `needs_evidence`.
- Keep IASME question text paraphrased.
- Include false-negative caveat for proposed `Yes` answers.
- Include cleanup statement for controlled Azure lab.
- Do not publish raw tenant identifiers.
- Verify all claims use absolute counts and percentages together.
- Convert Markdown citations to the target venue's required format.
- Decide whether to include the competitor-check table in the appendix or compress it into related work.
