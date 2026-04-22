# Architecture

CRIS-SME uses a layered architecture that separates **evidence ingestion**, **asset/context modeling**, and **decision logic**.

This keeps the system explainable and extensible without introducing unnecessary enterprise complexity.

## Layer 1: Evidence

Purpose:
- gather provider posture signals
- preserve collection provenance
- record observability limits explicitly

Main components:
- collectors (`mock`, `azure`)
- provider adapters and registry
- collector coverage metadata

Outputs:
- normalized `CloudProfile` instances
- collection detail fields (mode, source type, auth basis, evidence counts)

## Layer 2: Asset and Context

Purpose:
- normalize assessed estate into meaningful assets/relationships
- support context-aware prioritization

Main components:
- platform schemas (`Asset`, `AssetRelationship`, `EvidenceRecord`)
- lightweight context graph builder

Outputs:
- asset/relationship summaries
- blast-radius estimate
- toxic combinations
- exposure chain hints

## Layer 3: Decision

Purpose:
- evaluate controls and produce deterministic risk decisions

Main components:
- domain control modules (IAM/Network/Data/Monitoring/Compute/Governance)
- deterministic scoring engine
- confidence calibration
- compliance mapping
- lifecycle/enrichment (status, first/last seen, exceptions)

Outputs:
- scored prioritized findings with traceability
- lifecycle-aware finding records
- remediation/action plans
- readiness profiles

## Layer 4: Reporting and Experience

Purpose:
- expose decision outputs for technical, executive, and research users

Main components:
- JSON report schema
- HTML report
- interactive dashboard bundle (`dashboard_payload` + dashboard HTML)
- figures, appendix exports, executive/insurance packs
- historical drift comparison utilities

## Data and Policy Governance

CRIS-SME governs control behavior through:

- central control catalog (title, mappings, remediation metadata)
- control spec metadata pack (intent, applicability, support, limitations, penalties)
- explicit schema versioning in reports

## Determinism and Explainability Guarantees

- Scoring remains deterministic and formula-based.
- Narration is optional and non-authoritative.
- Findings keep evidence lineage and confidence rationale.
- Partial observability is surfaced, not hidden.

## Provider Strategy

- Azure: active first-class path
- AWS/GCP: planned adapters and expansion path

The architecture is provider-neutral by design, Azure-first by implementation maturity.
