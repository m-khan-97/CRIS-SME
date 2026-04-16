# CRIS-SME

**Cloud Risk Intelligence System for Small & Medium Enterprises**

## Overview

CRIS-SME is a research-oriented cloud risk intelligence framework designed to help small and medium enterprises (SMEs) identify, assess, score, and manage governance and compliance risks in cloud environments.

The current reference implementation focuses on Microsoft Azure, while the core scoring, reporting, and compliance layers are being designed to remain provider-neutral. This supports a realistic delivery path: Azure-first for MVP credibility, with a clean architectural route toward broader multi-cloud support later.

CRIS-SME addresses a practical gap in cloud security for SMEs. Enterprise-grade governance tooling is often too expensive, too complex, or too operationally heavy for smaller organisations. CRIS-SME aims to provide a lightweight, explainable, and scalable alternative that supports both engineering practice and applied research.

## Problem Statement

UK SMEs migrating to cloud environments frequently lack structured governance frameworks, automated compliance validation mechanisms, and risk intelligence systems tailored to their scale. Existing enterprise-grade cloud security tools are either cost-prohibitive or overly complex for SMEs. This creates a measurable governance and compliance gap in the UK commercial sector.

CRIS-SME responds to this challenge through a framework that combines:

- Governance control validation
- Deterministic risk scoring and prioritisation
- Compliance mapping
- UK-specific regulatory interpretation for SME-relevant controls
- Budget-aware remediation action packs for SME decision-making
- Explainable outputs for decision support
- AI-assisted prioritisation as a later enhancement

## Research and Engineering Positioning

This repository is being developed as a serious technical and research asset. The design priorities are:

- Explainable and defensible scoring
- Modular architecture for iterative experimentation
- Maintainable Python implementation
- SME-focused realism rather than enterprise-only assumptions
- Clear outputs suitable for demos, reports, and future academic publication

## Current MVP Capabilities

The current MVP is no longer just a scoring prototype. It includes:

- Synthetic SME cloud posture profiles
- Provider-normalized collection through an adapter layer
- Domain control evaluation across six categories
- Deterministic, explainable risk scoring
- Compliance mapping to selected governance frameworks
- UK SME regulatory profile covering Cyber Essentials, UK GDPR, FCA SYSC, and DSPT
- Budget-aware remediation planning across free, lean, and broader SME budget bands
- JSON, HTML, and summary report export suitable for demos and notebooks
- Archived report history, comparison figures, and appendix-ready outputs
- Live Azure-backed assessment support behind the collector layer

### Implemented Control Domains

- IAM
- Network
- Data Protection
- Monitoring and Logging
- Compute and Workloads
- Cost and Governance Hygiene

## Architecture

CRIS-SME follows a modular structure:

1. **Collectors**  
   Gather posture data from mock datasets first, then real provider integrations later.

2. **Provider Adapters**  
   Normalize provider-specific data into a common internal profile model.

3. **Controls**  
   Evaluate governance and compliance checks across key risk domains.

4. **Risk Engine**  
   Score findings, prioritise issues, aggregate category risk, and provide explainability.

5. **Reporting**  
   Produce structured JSON outputs and concise executive-style summaries.

### Provider Strategy

The framework uses a provider-neutral core with an Azure-first implementation path:

- Core models, scoring, reporting, and compliance logic are cloud-agnostic
- Azure is the first supported provider in the adapter layer
- Mock collection currently drives the MVP pipeline
- Real Azure-backed collection is the next integration step
- AWS and GCP can be added later through additional adapters

## Initial Risk Model

The MVP risk engine uses a deterministic and explainable scoring model.

Severity weights:

- Critical = 10
- High = 7
- Medium = 4
- Low = 1

Modifier directions:

- `likelihood_factor = 0.8 + 0.8 * exposure`
- `data_factor = 0.8 + 0.8 * data_sensitivity`
- `confidence_factor = 0.7 + 0.3 * confidence`

The engine produces:

- Per-finding risk scores
- Category-level scores
- Weighted overall risk score out of 100
- Ranked risk outputs with scoring explanations

## Repository Structure

```text
cris-sme/
├── README.md
├── LICENSE
├── .gitignore
├── requirements.txt
├── pyproject.toml
├── env.example
├── docs/
├── data/
├── src/cris_sme/
├── notebooks/
├── tests/
├── outputs/
└── .github/
```

## Current Output Artifacts

Running the CLI currently generates:

- `outputs/reports/cris_sme_report.json`
- `outputs/reports/cris_sme_report.html`
- `outputs/reports/cris_sme_summary.txt`
- `outputs/reports/history/*.json`
- `outputs/reports/results_appendix.md`
- `outputs/reports/prioritized_risks.csv`
- `outputs/figures/*.svg`
- `outputs/figures/*.png`

These outputs are intended to support:

- engineering inspection
- demo walkthroughs
- notebook ingestion
- later dashboard and figure generation

## Current Implementation Status

Implemented in this phase:

- Core repository scaffold
- Pydantic v2 data models
- Synthetic SME posture datasets
- Provider adapter routing
- Domain control evaluation across six categories
- Deterministic scoring engine
- Compliance mapping engine
- JSON, HTML, and text reporting
- SVG and PNG figure generation
- archived run comparison and appendix exports
- CLI entrypoint for MVP execution
- Automated test coverage across scoring, controls, reporting, compliance, and adapters
- Live Azure assessment artifacts and documented case-study evidence

Next:

- deeper tenant-level identity and budget-governance collection
- repeated-run evaluation across more environments and time windows
- future AI-assisted prioritisation experiments
- broader provider expansion through AWS and GCP adapters and collectors

## Getting Started

### Requirements

- Python 3.10+
- `pip`

### Installation

```bash
git clone https://github.com/m-khan-97/CRIS-SME.git
cd CRIS-SME
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run the MVP

```bash
PYTHONPATH=src python -m cris_sme.main
```

### Run a Repeatable Archived Snapshot

```bash
python scripts/run_assessment_snapshot.py --collector mock
```

### Run Tests

```bash
PYTHONPATH=src pytest
```

## Use Cases

- SME cloud governance assessments
- Applied research in cloud risk intelligence
- Demonstrations of explainable risk scoring
- Prototyping of governance automation workflows
- Early-stage compliance mapping experiments

## Documentation

- `docs/project-overview.md`
- `docs/architecture.md`
- `docs/methodology.md`
- `docs/scoring-model.md`
- `docs/compliance-mapping.md`
- `docs/live-azure-case-study.md`
- `docs/evaluation-results-draft.md`
- `docs/paper-outline.md`
- `docs/manuscript-draft.md`
- `docs/submission-checklist.md`
- `docs/multi-cloud-expansion.md`
- `docs/roadmap.md`

## License

MIT License

## Acknowledgements

This project is developed as part of ongoing research into cloud governance, risk intelligence, and SME digital resilience.
