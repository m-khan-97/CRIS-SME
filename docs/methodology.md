# Methodology

The CRIS-SME methodology is designed to balance practical engineering utility with research defensibility. The MVP does not begin with machine learning or opaque prioritisation. Instead, it starts with deterministic controls and explainable scoring.

## Methodological Principles

The implementation follows five core principles:

- realism over hype
- explainability over opacity
- modularity over monolithic tooling
- iterative validation over premature platform complexity
- SME suitability over enterprise-only assumptions

## Current MVP Method

The current method follows this sequence:

1. define a normalized cloud posture model
2. collect either synthetic or live Azure-first posture evidence
3. evaluate domain controls against that posture
4. generate normalized findings
5. score findings using deterministic formulas
6. aggregate findings into category and overall risk views
7. map findings to selected governance and compliance references
8. archive report snapshots for repeated-run comparison
9. generate report, figure, and appendix artifacts for analysis and communication

## Why Synthetic Profiles First

Synthetic profiles are used in the MVP for three reasons:

- they allow repeatable testing and demonstrations
- they reduce dependency on live cloud access during early development
- they support transparent scoring experiments without collection noise

This is a methodological choice, not a claim that synthetic posture is sufficient long term. CRIS-SME now also supports live Azure-backed collection, which allows synthetic and live runs to be compared explicitly through archived report history.

## Explainable Risk Scoring

The scoring model is intentionally deterministic. This makes it easier to:

- justify prioritisation decisions
- inspect how a score was formed
- compare scoring changes across experiments
- support academic discussion of assumptions and limitations

## Live Evidence and Observability Boundaries

The live collector does not treat all cloud control areas as equally observable. This is deliberate.

- subscription-scoped Azure evidence is collected where practical and stable
- Entra and tenant-wide identity signals are incorporated cautiously
- observability limits are reported explicitly rather than hidden

This is especially important for IAM. The current collector can observe privileged assignment posture and some Entra-adjacent signals, but it does not claim full tenant-wide identity governance visibility unless that evidence is actually accessible.

## Repeated-Run Comparison

Each CRIS-SME execution now archives a timestamped JSON snapshot under `outputs/reports/history/`. This enables:

- mock-versus-live comparison
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
