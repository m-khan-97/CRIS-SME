# Methodology

CRIS-SME is designed as an evidence-driven, deterministic methodology for SME cloud risk decisions.

## Method Principles

1. **Deterministic before opaque**
   - score logic is formula-based and inspectable
2. **Evidence before narrative**
   - findings derive from collected posture evidence
3. **Explicit observability boundaries**
   - unavailable signals are recorded as unavailable, not silently assumed
4. **Actionability for SME constraints**
   - remediation planning includes budget-aware profiles
5. **Repeatability for research**
   - run snapshots and drift comparisons are first-class outputs

## End-to-End Method Flow

1. collect profile evidence (`mock` or `azure`)
2. normalize into provider-neutral posture model
3. evaluate controls per domain
4. score non-compliant findings deterministically
5. calibrate confidence using empirical control metadata
6. map controls/findings to frameworks
7. attach traceability and lifecycle metadata
8. build graph-context signals
9. generate reporting + dashboard artifacts
10. archive run and compute trend/drift comparisons

## Evidence Classes

- **Observed**: directly visible via collector evidence
- **Inferred**: reasoned from partial evidence
- **Unavailable**: evidence required but not observable in scope

This classification is carried into finding outputs to improve honesty and trust.

## Lifecycle Method

Findings are enriched with:

- first seen / last seen
- new vs existing classification
- status (`open`, `accepted_risk`, `suppressed`, etc.)
- optional exception linkage with expiry semantics

## Context-Aware Prioritization Method

CRIS-SME adds lightweight graph context to deterministic scoring by surfacing:

- toxic control combinations
- blast-radius estimate
- exposure chain summaries

This is intentionally pragmatic and transparent.  
It does not claim full adversarial attack-path simulation.

## Research Positioning

The methodology is suitable for:

- reproducible local studies (synthetic)
- live case-study validation (authorized Azure)
- trend/drift analysis across repeated runs
- paper-friendly export artifacts and appendices
