# Scoring Model

CRIS-SME uses a deterministic and explainable scoring model for the MVP. The purpose of the model is not to imitate enterprise vendor scoring systems, but to provide a transparent method for turning governance findings into prioritised risk outputs.

## Finding Inputs

Each finding includes a set of fields used by the scoring engine, including:

- severity
- exposure
- data sensitivity
- confidence
- remediation effort
- compliance status
- category
- evidence and resource scope for interpretation

## Severity Weights

The current base severity weights are:

- Critical = 10
- High = 7
- Medium = 4
- Low = 1

These values intentionally create meaningful separation between high-impact and low-impact issues while remaining simple enough to defend in documentation and experiments.

## Modifier Logic

The current MVP uses three primary score modifiers and one implementation-oriented adjustment:

- `likelihood_factor = 0.8 + 0.8 * exposure`
- `data_factor = 0.8 + 0.8 * data_sensitivity`
- `confidence_factor = 0.7 + 0.3 * confidence`
- a bounded remediation-effort adjustment is applied so operationally difficult issues remain visible in prioritisation

This approach keeps the model:
- interpretable
- reproducible
- suitable for experimentation
- easy to compare across later revisions

## Aggregation Model

The engine produces:

- per-finding risk scores
- ranked non-compliant findings
- category-level average scores
- weighted overall risk score out of 100

The current category weighting model is:

- IAM = 25%
- Network = 20%
- Data = 20%
- Monitoring/Logging = 15%
- Compute/Workloads = 10%
- Cost/Governance Hygiene = 10%

These weights reflect an SME-oriented initial posture model in which identity, network exposure, and data protection have the strongest effect on overall governance risk.

## Explainability

Each scored finding retains an explanation payload describing the score inputs and factor contributions. This is a core part of CRIS-SME's design and is intended to support:

- user trust
- engineering validation
- research transparency
- future comparison with AI-assisted prioritisation methods
