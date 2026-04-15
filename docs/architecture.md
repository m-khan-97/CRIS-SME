# Architecture

CRIS-SME uses a modular architecture that separates data collection, control evaluation, risk scoring, compliance interpretation, and reporting. This separation is important both for maintainability and for research credibility, because it allows scoring assumptions and control logic to be inspected independently.

## Architectural Layers

### 1. Collectors

Collectors are responsible for loading posture information into the system.

Current state:
- `MockCollector` loads synthetic SME profiles and sample findings from local JSON data.
- `AzureCollector` exists as a placeholder for future live Azure-backed ingestion.

The collector layer is intentionally conservative at this stage so the project can validate scoring and reporting behavior before introducing provider-specific operational complexity.

### 2. Provider Adapters

Provider adapters normalize provider-specific posture into the provider-neutral `CloudProfile` model.

Current state:
- Azure is the first registered provider adapter.
- Raw profile records are routed through the adapter registry before control evaluation.

This design allows CRIS-SME to remain Azure-first without hard-wiring Azure-specific assumptions into the core scoring and reporting layers.

### 3. Control Modules

Control modules evaluate domain-specific governance and compliance conditions and produce normalized findings.

Current control domains:
- IAM
- Network
- Data Protection
- Monitoring and Logging
- Compute and Workloads
- Cost and Governance Hygiene

Each control module emits findings with:
- control identifiers
- severity
- compliance status
- evidence
- resource scope
- scoring inputs
- governance or compliance mappings

### 4. Risk Engine

The risk engine transforms findings into decision-support outputs.

Its main responsibilities are:
- assign per-finding scores
- explain the score construction
- rank non-compliant findings
- aggregate category scores
- compute the overall weighted risk score

The engine is deterministic by design in the MVP so results remain interpretable and reproducible.

### 5. Compliance Mapping

The compliance layer maps findings to external governance references and control frameworks. This does not claim formal certification readiness. Instead, it provides a lightweight interpretation layer showing where findings intersect with established standards or guidance.

### 6. Reporting

The reporting layer translates engine outputs into artifacts suitable for different audiences.

Current outputs:
- machine-readable JSON report
- concise summary text report

These outputs support:
- command-line inspection
- notebook analysis
- demo screenshots
- future dashboard and figure generation

## Internal Flow

The current pipeline is:

1. load synthetic provider records
2. normalize them through a provider adapter
3. evaluate domain controls
4. score and prioritise findings
5. map findings to compliance references
6. build report artifacts
7. write outputs to `outputs/reports/`

## Provider-Neutral Core

A key architectural choice in CRIS-SME is to keep the core framework provider-neutral while implementing Azure as the first reference provider.

Provider-neutral layers:
- finding models
- cloud profile abstraction
- scoring engine
- compliance engine
- reporting

Provider-specific layers:
- raw posture ingestion
- adapter normalization
- future cloud SDK integrations

This structure is intended to support future AWS and GCP expansion without rewriting the core framework.
