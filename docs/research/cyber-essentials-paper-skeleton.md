# Paper Skeleton: Automated Cyber Essentials Self-Assessment From Cloud Telemetry

Working title:
**Evidence-Sufficiency-Aware Cyber Essentials Pre-Population From Cloud Control-Plane Telemetry**

## Core Claim

CRIS-SME does not automate Cyber Essentials certification. It pre-populates candidate Cyber Essentials answer states from cloud evidence, classifies evidence sufficiency question by question, and records where human, endpoint, policy, or manual evidence is still required.

The defensible contribution is:

> A deterministic method for mapping cloud control-plane telemetry to paraphrased Cyber Essentials question-level answer support, with explicit observability boundaries and human verification workflow.

## Abstract Skeleton

Cyber Essentials is a widely used UK baseline security scheme, but SMEs often complete the self-assessment manually despite already operating cloud environments that contain relevant control-plane evidence. Existing cloud security tools report technical misconfigurations or framework-level compliance mappings, but they do not produce question-level Cyber Essentials pre-population with explicit evidence sufficiency boundaries.

This paper presents CRIS-SME, a deterministic cloud risk decision engine extended with a Cyber Essentials pre-assessment workflow. CRIS-SME maps paraphrased Cyber Essentials questions to cloud control evidence, classifies each question as directly cloud-observable, inferred from cloud posture, endpoint-required, policy-required, or manual-required, and emits a human-reviewable answer pack. A review console records accepted answers, overrides, evidence requests, and reviewer notes without changing deterministic risk scores. An evaluation metrics pack reports observability, evidence gaps, review outcomes, and agreement rates.

In the current Azure-first implementation, CRIS-SME maps 106 Cyber Essentials preparation entries, including 62 technical-control entries. From cloud control-plane evidence alone, 28 entries are cloud-supported overall and 22 technical entries are cloud-supported. The remaining entries are explicitly classified as endpoint, policy, or manual evidence gaps rather than silently inferred. These results show that cloud telemetry can materially reduce CE evidence retrieval work while preserving human accountability and certification boundaries.

## Research Questions

RQ1. What proportion of Cyber Essentials preparation questions can be supported from cloud control-plane telemetry alone?

RQ2. Which evidence classes dominate the remaining unanswered questions: endpoint, policy, manual, or unavailable cloud evidence?

RQ3. How often do reviewers accept, override, or request more evidence for CRIS-SME proposed answer states?

RQ4. Which CRIS-SME controls most frequently contribute to Cyber Essentials answer-impact findings?

## Contributions

1. A question-level Cyber Essentials mapping model that avoids reproducing proprietary IASME wording by storing paraphrased descriptions and stable local question identifiers.
2. A deterministic answer-pack generator that links CE entries to CRIS-SME controls, findings, evidence snippets, and caveats.
3. An evidence sufficiency taxonomy for CE pre-population: direct cloud, inferred cloud, endpoint required, policy required, manual required, and not observable.
4. A human review console that records accepted answers, overrides, evidence requests, reviewer notes, and final reviewed status without altering deterministic scores.
5. A reproducible evaluation metrics and paper-table export pipeline for observability, evidence gaps, review outcomes, section coverage, and control contribution.

## System Overview

CRIS-SME takes cloud evidence from the Azure collector or mock collector, normalizes it into provider-neutral posture profiles, evaluates deterministic controls, scores non-compliant findings, and produces traceable reports.

The CE workflow is a downstream layer:

1. `data/ce_question_mapping.json` defines paraphrased CE entries and evidence classes.
2. `build_ce_self_assessment_pack()` links mapped entries to CRIS-SME findings.
3. `build_ce_review_console()` creates a human-verification ledger.
4. `build_ce_evaluation_metrics()` calculates observability and review metrics.
5. `write_ce_paper_exports()` emits manuscript-ready Markdown, CSV, and chart JSON artifacts.

## Method

### Question Mapping

Each mapped entry includes:

- local question ID
- CE section
- research scope
- paraphrased question summary
- evidence class
- supporting CRIS-SME control IDs
- current CRIS-SME signals
- planned evidence paths
- human review requirement

The mapping intentionally paraphrases the official preparation questions and does not reproduce full IASME wording.

### Evidence Classification

Direct cloud:
The answer can be supported by observed Azure control-plane evidence.

Inferred cloud:
The answer can be partially supported from cloud posture, but the final answer requires interpretation or reviewer confirmation.

Endpoint required:
The question requires device, MDM, EDR, local firewall, anti-malware, or patch evidence outside subscription telemetry.

Policy required:
The question requires business process, approval, documented policy, or contractual evidence.

Manual required:
The question requires applicant context, organisation metadata, scoping judgement, or final attestation.

Not observable:
The required signal is outside current CRIS-SME evidence paths.

### Human Verification

The review console initializes every entry as pending. A reviewer can mark entries as:

- accepted
- overridden
- needs evidence
- pending

Reviewer decisions affect only the CE review ledger. They do not alter CRIS-SME findings, priorities, scores, or control outcomes.

## Evaluation Design

### Datasets

Minimum planned datasets:

1. Synthetic CRIS-SME mock assessment.
2. Controlled live Azure subscription.
3. Vulnerable lab or AzureGoat-style environment.

Preferred extension:

- one real SME tenant, assessed with explicit written authorization.

### Metrics

Primary metrics:

- cloud-supported question count
- cloud-supported rate
- technical cloud-supported count
- technical cloud-supported rate
- evidence gap counts by class
- reviewed count
- reviewer accepted count
- reviewer override count
- needs-evidence count
- agreement rate over accepted and overridden entries

Secondary metrics:

- section-level cloud support
- top CRIS-SME controls contributing to CE answer-impact findings
- evidence retrieval workload reduction, measured as number of questions with generated evidence references

## Current Baseline Results

Generated from the current CRIS-SME pipeline:

- mapped entries: `106`
- technical-control entries: `62`
- cloud-supported entries: `28` (`26.42%`)
- technical cloud-supported entries: `22` (`35.48%`)
- non-cloud evidence required: `78`

Evidence gap counts:

- endpoint required: `24`
- policy required: `19`
- manual required: `35`
- not observable: `0`

Reviewer agreement is currently `0%` because no completed human review ledger has been imported yet. This is correct for the pre-review baseline and should be reported as pending rather than as disagreement.

## Threats To Validity

The CE question mapping uses paraphrased preparation entries rather than official certification wording. This protects licensing boundaries but requires careful documentation.

The current implementation is Azure-first. AWS, GCP, Intune, Defender for Endpoint, and MDM integrations would increase observability for endpoint and device questions.

The initial metrics are generated from CRIS-SME artifacts rather than from a multi-organisation user study. Agreement and time-saved claims require reviewer-completed ledgers.

Cyber Essentials certification remains a human attestation workflow. CRIS-SME must be framed as pre-population and evidence support, not certification automation.

## Target Venues

Most realistic:

- Computers & Security
- SOUPS if a reviewer study is added
- EuroS&P workshop
- NCSC-adjacent practitioner venues

Less realistic as a first target:

- USENIX Security main track
- IEEE S&P main track
- ACM CCS main track

## Artifact Checklist

- `outputs/reports/cris_sme_ce_self_assessment.json`
- `outputs/reports/cris_sme_ce_self_assessment.html`
- `outputs/reports/cris_sme_ce_review_console.json`
- `outputs/reports/cris_sme_ce_review_console.html`
- `outputs/reports/cris_sme_ce_evaluation_metrics.json`
- `outputs/reports/cris_sme_ce_evaluation_metrics.html`
- `outputs/reports/cris_sme_ce_paper_tables.md`
- `outputs/reports/cris_sme_ce_paper_tables.csv`
- `outputs/reports/cris_sme_ce_chart_data.json`
