# Data Model

CRIS-SME now uses production-shaped schema concepts in `src/cris_sme/models/platform.py`.

## Core Schema Groups

### Evidence and Collection

- `EvidenceRecord`
- `CollectorCoverage`
- `RunMetadata`

### Assets and Relationships

- `Asset`
- `AssetRelationship`

### Decision and Traceability

- `FindingTrace`
- `ConfidenceAssessment`
- `FrameworkMapping`
- `ActionItem`

### Lifecycle and Governance

- `FindingStatus`
- `ExceptionRecord`
- `HistoricalSnapshot`
- `PolicyPackMetadata`

## Existing Core Models (still active)

- `CloudProfile` (provider-normalized posture model)
- `Finding` (control decision output)
- `ComplianceAssessmentResult` (mapping summary)
- `ScoringResult` (prioritized deterministic score output)

## Design Notes

- CRIS-SME keeps backwards-friendly report keys while adding richer schema fields.
- New schema fields are additive and traceability-oriented.
- Deterministic scoring contracts remain stable.
