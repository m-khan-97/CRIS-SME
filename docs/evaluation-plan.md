# Evaluation Plan

## Purpose

This document defines the paper-first evaluation strategy for CRIS-SME. Its role is to turn the current engineering system into a defensible research artifact with explicit research questions, datasets, baselines, procedures, and limitations.

The evaluation is designed to answer a practical research problem:

UK SMEs adopting cloud services often lack lightweight, explainable, and cost-sensitive governance tooling. CRIS-SME aims to bridge that gap by combining deterministic risk scoring, UK-oriented compliance mapping, budget-aware prioritization, and provenance-aware reporting.

## Research Questions

The current paper should be organized around four research questions:

1. Can CRIS-SME generate explainable governance findings and interpretable risk scores from both synthetic and live Azure evidence?
2. How closely do CRIS-SME findings align with Microsoft Defender for Cloud recommendations where comparable controls exist?
3. Does CRIS-SME provide more SME-usable prioritization by combining deterministic scoring with remediation-cost context rather than severity-only ranking?
4. Does UK-specific compliance framing improve the relevance of cloud posture outputs for UK SME governance use cases?

These questions are intentionally narrow enough to be answerable with the current system, while still strong enough to support a conference paper or extended abstract.

## Evaluation Design

The evaluation should be executed in three layers.

### Layer 1: System Validation

This layer demonstrates that the framework works as intended.

Inputs:

- synthetic SME posture profiles
- live Azure-backed assessment data
- intentionally vulnerable Azure lab data
- archived report history

Outputs:

- category and overall risk scores
- prioritized findings
- UK compliance mappings
- action plans, executive pack, and insurance evidence

Questions answered:

- does the system run end-to-end?
- are the outputs structurally coherent and reproducible?
- can the model remain explainable across mock and live modes?

### Layer 2: Baseline Comparison

This layer compares CRIS-SME with Azure-native posture signals.

Baseline:

- Microsoft Defender for Cloud recommendations and unhealthy assessments

Current comparison target:

- mapped CRIS-SME controls in `native_validation`

Measures:

- number of mapped controls
- agreement count
- CRIS-only count
- native-only count
- qualitative explanation of mismatches

Questions answered:

- where does CRIS-SME agree with Azure-native posture logic?
- where does CRIS-SME add distinct value?
- where is observability constrained?

### Layer 3: SME Actionability

This layer evaluates whether CRIS-SME produces outputs that are more usable for SMEs than raw scanner output.

Focus areas:

- budget-aware remediation packs
- 30-day action plan
- executive pack
- cyber insurance evidence pack
- Cyber Essentials readiness

Measures:

- number of zero-cost actions surfaced
- cumulative risk covered by free and low-cost packs
- top actions under each budget profile
- board-/insurer-ready output availability

Questions answered:

- can the framework translate posture into affordable next steps?
- does the output structure support non-specialist decision-making?

## Datasets

The paper should explicitly separate four dataset classes.

### A. Synthetic SME Dataset

Source:

- `data/synthetic_sme_profiles.json`

Purpose:

- repeatable control testing
- scoring experiments
- regression testing
- baseline category comparison

Strengths:

- fully reproducible
- supports controlled scenarios
- safe to publish and share

Limitations:

- not real operational drift
- not representative of all SME cloud estates

### B. Live Azure Case Study

Source:

- authenticated Azure assessment runs
- archived report history under `outputs/reports/history/`

Purpose:

- demonstrate live-cloud feasibility
- compare CRIS-SME with Defender recommendations
- evaluate provenance, observability, and actionability

Current reference live snapshot:

- Azure-backed run with overall risk score `32.79`
- `18` non-compliant findings
- Defender comparison showing `7` mapped controls, `0` agreements, `6` CRIS-only findings, and `0` native-only findings in the selected reference snapshot

Limitations:

- currently one live subscription
- live results are case-study evidence, not broad population evidence

### C. Vulnerable-Lab Azure Dataset

Source:

- AzureGoat-derived assessment runs executed in an isolated, explicitly authorized subscription context

Purpose:

- stress-test control coverage against intentionally vulnerable cloud resources
- provide a lawful middle ground between synthetic posture and production-adjacent live assessment
- increase risk variance in evaluation without relying on arbitrary public infrastructure

Current reference vulnerable-lab snapshot:

- Azure-backed vulnerable-lab run with overall risk score `32.79`
- `18` non-compliant findings
- dataset source type `vulnerable_lab`
- authorization basis `intentionally_vulnerable_lab`

Important methodological note:

- the current AzureGoat deployment is a constrained variant, not a stock lab rollout
- tenant location policy, Automation Account restrictions, and regional VM-capacity limits prevented a full unmodified deployment
- this is still a valid research dataset because the environment remains intentionally vulnerable and explicitly authorized, but the deployment constraints should be disclosed

### D. Historical Comparison Dataset

Source:

- archived JSON snapshots

Purpose:

- run comparison
- mock-versus-live contrast
- future longitudinal analysis

Current use:

- compare the latest mock baseline against the latest live Azure baseline
- study control deltas between environments

## Baselines

The paper should use three baselines or reference modes, each with a different purpose.

### Baseline 1: Synthetic Mock Baseline

Use:

- controlled reference scenario
- internal validation of scoring and prioritization behavior

Role in paper:

- establishes repeatable baseline posture
- supports methodology and scoring discussion

### Baseline 2: Microsoft Defender for Cloud

Use:

- external cloud-native comparison point

Role in paper:

- supports confidence calibration
- supports agreement/mismatch analysis
- helps justify the claim that CRIS-SME is not merely inventing arbitrary posture findings

Important framing:

CRIS-SME is not evaluated as a replacement for Defender for Cloud. The comparison is used to understand overlap, divergence, and SME-facing interpretability.

### Baseline 3: Vulnerable-Lab Stress Track

Use:

- control-coverage stress testing
- deliberate exposure of risky storage, network, and application patterns
- bridge between synthetic scenarios and real subscription evidence

Role in paper:

- demonstrates that CRIS-SME can operate against intentionally vulnerable cloud environments without relying on unauthorized public scanning
- strengthens the claim that the framework supports multiple evidence classes, not just one live tenant

## Metrics

The paper should report the following metrics.

### Risk and Posture Metrics

- overall risk score
- category scores
- number of non-compliant findings
- priority distribution

### Agreement Metrics

- mapped control count
- agreement count
- CRIS-only count
- native-only count

### SME Actionability Metrics

- free-fix action count
- under-GBP200 action count
- cumulative risk covered by each budget profile
- top actions by remediation value score

### UK Governance Metrics

- UK mapped control count
- UK mapped finding count
- Cyber Essentials readiness score
- insurance readiness score

## Procedure

The paper evaluation should be run in the following order.

1. Generate the latest mock report from `synthetic_sme_profiles.json`.
2. Generate the latest live Azure report with the Azure collector.
3. Archive both snapshots and verify the historical comparison output.
4. Extract category scores, priority distributions, and budget-aware packs.
5. Extract `native_validation` and summarize agreement outcomes.
6. Export paper-facing tables and figures.
7. Write the evaluation/results section using the mock run as baseline and the Azure run as the main case study.

## Paper Figures and Tables

The minimum paper artifact set should include:

- overall/category score comparison table for mock vs live
- Defender comparison table
- top prioritized findings table
- budget-aware action-pack table
- Cyber Essentials readiness table
- risk trend figure
- run comparison figure

The current paper-facing table set should live in `docs/paper-results-tables.md`.

## Threats to Validity

The paper should explicitly acknowledge the following threats.

### Internal Validity

- some confidence values are calibrated from lightweight empirical evidence rather than broad population studies
- certain live collector domains still rely on limited observability

### External Validity

- a single live Azure case study is not representative of the whole UK SME population
- synthetic profiles are useful for reproducibility, but not a substitute for multi-organization field data

### Construct Validity

- actionability is currently inferred from deterministic remediation planning rather than formal user-study data
- UK mapping is implementation-grounded but not yet validated through interviews with regulated SMEs

## Near-Term Evaluation Extensions

The strongest next evaluation improvements are:

1. collect additional real or consented SME-like Azure assessments
2. deepen Defender-grounded control agreement analysis
3. add sensitivity analysis for scoring weights
4. compare severity-only ranking against budget-aware ranking in a formal appendix
5. document SME stakeholder interpretation through a small qualitative study

## Recommended Paper Framing

For the first paper, CRIS-SME should be framed as:

- an explainable cloud risk intelligence framework
- targeted at UK SME governance needs
- validated through synthetic experiments, live Azure case-study evidence, and Defender-grounded comparison

That framing is more defensible than claiming broad market replacement or general-purpose multicloud superiority at this stage.
