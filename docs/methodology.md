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

## Three-Mode Evaluation Design

The current paper-facing methodology treats three evidence modes as equal first-class parts of the evaluation:

- synthetic baseline profiles for controlled reproducibility
- live Azure assessment snapshots for authorized real-cloud feasibility
- controlled Azure vulnerable-lab snapshots for lawful stress testing

This framing is deliberate. It avoids overstating any single run as the whole evaluation story and instead separates three different methodological roles:

- controlled regression and score-behavior testing
- real-tenant observability and feasibility validation
- higher-variance control-path stress testing in an explicitly authorized environment

## Why Synthetic Profiles First

Synthetic profiles remain useful because they provide a reproducible baseline for evaluating score behavior, reporting outputs, and regression stability before moving into noisier live-cloud conditions.

## Lifecycle Method

Findings are enriched with:

- first seen / last seen
- new vs existing classification
- status (`open`, `accepted_risk`, `suppressed`, etc.)
- optional exception linkage with expiry semantics

This is a methodological choice, not a claim that synthetic posture is sufficient long term. CRIS-SME now also supports live Azure-backed collection and intentionally vulnerable-lab collection, which allows all three modes to be compared explicitly through archived report history.

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
- vulnerable-lab stress testing in an explicitly allowed environment
- trend/drift analysis across repeated runs
- paper-friendly export artifacts and appendices

This is especially important for IAM. The current collector can observe privileged assignment posture and some Entra-adjacent signals, but it does not claim full tenant-wide identity governance visibility unless that evidence is actually accessible.

## Repeated-Run and Cross-Mode Comparison

Each CRIS-SME execution now archives a timestamped JSON snapshot under `outputs/reports/history/`. This enables:

- synthetic-versus-live comparison
- live-versus-vulnerable-lab comparison
- paper-facing three-mode summary tables
- longitudinal score comparison over time
- category-level delta tracking
- paper-ready figure generation from repeated runs

This archived-run model is important for research credibility because it supports explicit comparison rather than anecdotal interpretation of single-point assessments.

## Research Artifacts

The current methodology produces several artifact types from the same assessment pipeline:

- JSON, HTML, and summary reports
- SVG figure exports for categories, priorities, and run-history comparison
- appendix-ready markdown and CSV tables
- notebooks for figure generation and methodology/results analysis

## AI Positioning

CRIS-SME uses the term **AI-assisted prioritisation** carefully. In the current stage, AI is not the foundation of the framework. It is a future enhancement to a system that already has:

- explicit controls
- structured findings
- deterministic risk scoring
- reportable outputs

This positioning is important for research credibility and avoids overstating the maturity of the intelligence layer.
