# Paper Outline

This document provides a working manuscript structure for turning CRIS-SME into a conference or workshop paper.

## Title Options

- CRIS-SME: An Explainable Cloud Risk Intelligence Framework for SME Cloud Governance
- CRIS-SME: Deterministic Cloud Risk Scoring and Governance Assessment for Small and Medium Enterprises
- CRIS-SME: A Provider-Neutral Cloud Governance Assessment Framework with an Azure-First Reference Implementation

## Abstract

Use [conference-abstract-draft.md](/home/muhammad-ibrahim/Github/CRIS-SME/docs/conference-abstract-draft.md) as the starting point.

## 1. Introduction

Core goals for this section:

- define the governance and compliance gap faced by SMEs moving to cloud environments
- explain why enterprise tooling is often a poor fit for SME contexts
- position CRIS-SME as a lightweight, explainable, research-backed framework
- state the Azure-first but provider-neutral strategy

Suggested subsection flow:

1. cloud adoption and SME governance pressure
2. limitations of current enterprise-centric cloud security tooling
3. motivation for explainable and affordable risk intelligence
4. research objective and contribution summary

## 2. Problem Statement and Research Motivation

Recommended content:

- formalize the SME cloud governance gap
- emphasize explainability, affordability, and operational usability
- justify deterministic scoring as the first stage before AI-assisted prioritisation
- connect the problem directly to resilience and governance automation

## 3. Related Work

Suggested comparison themes:

- CSPM and enterprise cloud governance platforms
- compliance automation frameworks
- risk scoring and prioritisation in cloud security
- explainable security analytics
- SME digital resilience and governance research

Useful framing:

- CRIS-SME is not trying to replace enterprise CSPM breadth
- CRIS-SME focuses on a more accessible, explainable, research-friendly operating point

## 4. Framework Architecture

Base this on [architecture.md](/home/muhammad-ibrahim/Github/CRIS-SME/docs/architecture.md).

Recommended structure:

1. collectors
2. provider adapters
3. control evaluation layer
4. risk engine
5. compliance mapping
6. reporting and research artifacts

Include the provider-neutral core and Azure-first implementation argument.

## 5. Methodology

Base this on [methodology.md](/home/muhammad-ibrahim/Github/CRIS-SME/docs/methodology.md).

Recommended themes:

- deterministic scoring and explainability
- synthetic-first development strategy
- live Azure collection as validation
- observability boundaries, especially for IAM and Entra
- archived-run comparison and reproducibility

## 6. Scoring Model

Base this on [scoring-model.md](/home/muhammad-ibrahim/Github/CRIS-SME/docs/scoring-model.md).

Key elements:

- severity weighting
- exposure, data sensitivity, confidence, and remediation modifiers
- category aggregation
- overall score calculation
- why deterministic scoring is methodologically defensible

## 7. Implementation

Recommended implementation narrative:

- Python 3.10+ core engine
- Pydantic v2 models
- modular control domains
- JSON, HTML, SVG, PNG, and appendix exports
- archived report history and repeated-run comparison support

## 8. Evaluation and Results

Base this on the live report and [live-azure-case-study.md](/home/muhammad-ibrahim/Github/CRIS-SME/docs/live-azure-case-study.md).

Suggested structure:

1. synthetic baseline assessment
2. live Azure case study
3. score and category analysis
4. top prioritized findings
5. comparison across archived runs
6. identity observability interpretation

## 9. Discussion

Recommended discussion themes:

- why explainability matters for SME governance adoption
- tradeoffs between breadth and defensibility
- limitations of tenant-wide identity visibility
- how CRIS-SME differs from hype-driven AI security narratives

## 10. Limitations

Current limitations that should be stated clearly:

- Azure-first implementation
- limited live dataset
- tenant permission constraints for some Entra controls
- early-stage multi-cloud support
- deterministic scoring assumptions still subject to calibration

## 11. Future Work

Use this section to bridge to the next repo phase:

- deeper Entra and live identity evidence
- AWS and GCP provider adapters
- repeated-run longitudinal evaluation
- AI-assisted prioritisation experiments
- broader empirical validation across environments

## 12. Conclusion

The conclusion should reinforce:

- CRIS-SME is a credible engineering and research framework
- it is explainable and SME-oriented
- it already supports live evidence and repeatable outputs
- it provides a realistic base for future multi-cloud and AI-assisted work
