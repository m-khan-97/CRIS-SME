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
- paper tables and figures

Still required before journal submission:

- one independent CE-knowledgeable review of the 28 cloud-supported entries
- competitor/tool check
- related-work tightening
- final venue formatting

## Human Review Task

Ask one reviewer to complete `review-ledger-template.csv`.

Reviewer should mark each of the 28 cloud-supported entries as:

- `accepted`
- `overridden`
- `needs_evidence`

They should fill:

- final answer
- reviewer note
- evidence reference
- override reason when relevant

The reviewer does not need to be a certified CE assessor, but should understand the NCSC Cyber Essentials requirements and the distinction between cloud evidence and final attestation.

## Competitor Check

Check these before making novelty claims:

- Microsoft Defender for Cloud
- Prowler
- ScoutSuite
- JumpCloud
- IASME/NCSC self-assessment workflow
- ConnectWise / Datto / NinjaRMM style MSP tooling
- Axonius-style compliance mapping

Expected defensible claim:

> To our knowledge, existing tools provide readiness guidance, compliance-control mapping, or resource-level compliance assessments, but do not generate a question-level Cyber Essentials answer pack from live cloud telemetry with explicit evidence-sufficiency labels and human-verification boundaries.

## Figure Plan

Use the figures in `figures/`:

- `ce-evidence-class-distribution.svg`
- `ce-proposed-answer-distribution.svg`
- `azure-category-score-comparison.svg`
- `ce-workflow.svg`

## Final Pre-Submission Checklist

- Refresh all metrics from a frozen run.
- Confirm no generated table reports AI draft acceptance as human agreement.
- Keep IASME question text paraphrased.
- Include false-negative caveat for proposed `Yes` answers.
- Include cleanup statement for controlled Azure lab.
- Do not publish raw tenant identifiers.
- Verify all claims use absolute counts and percentages together.
