# CRIS-SME

**Cloud Risk Intelligence System for Small & Medium Enterprises**

CRIS-SME is an evidence-driven cloud risk decision engine for SMEs.  
It combines deterministic control evaluation, explainable scoring, lifecycle-aware findings, lightweight graph-context prioritization, compliance crosswalks, historical drift analysis, and budget-aware remediation planning.

The system is Azure-first in live collection, provider-neutral in core modeling, and designed to be runnable in a home lab.

---

## Why This Project Exists

Most SME cloud estates sit between two bad options:

- heavyweight enterprise security platforms that are often too expensive/complex
- lightweight scanners that produce raw findings without enough decision context

CRIS-SME is built to close that gap with:

- deterministic and explainable risk logic
- explicit evidence lineage and observability boundaries
- practical action planning constrained by SME budgets
- executive- and insurer-friendly outputs in the same pipeline

---

## Product Positioning

CRIS-SME is not just "a scanner that exports reports."

It is a **cloud risk decision platform** that turns posture evidence into:

1. traceable control decisions
2. prioritized findings with rationale and confidence
3. compliance/readiness interpretation
4. actionable remediation plans
5. trend and drift intelligence over time

---

## Key Capabilities

- Provider-normalized posture ingestion (`mock`, `azure`)
- Deterministic control evaluation across 6 domains / 26 controls
- Deterministic scoring with confidence calibration
- Evidence lineage fields (`finding_id`, `rule_version`, trace, observation class)
- Finding lifecycle support (`open`, `accepted_risk`, `suppressed`, etc.)
- Exception registry support with expiry awareness
- Graph-context reasoning:
  - blast-radius estimate
  - toxic combination detection
  - exposure chain summaries
- Compliance mapping across 13 frameworks
- UK-facing readiness outputs (Cyber Essentials, UK profile summary)
- Budget-aware remediation packs and 30-day action plan
- Historical drift analysis:
  - score deltas
  - new/resolved findings
  - recurring regressions
- Rich output artifacts:
  - JSON / HTML / text summary
  - appendix markdown + CSV
  - SVG/PNG figures
  - executive pack
  - cyber insurance evidence pack
  - benchmark scaffold exports
  - dashboard payload + interactive dashboard HTML
- Optional narrator for plain-language translation (non-authoritative)

---

## Architecture Overview

CRIS-SME is organized into three internal layers plus export surfaces:

1. **Evidence Layer**
   - Raw and normalized evidence records
   - Collector coverage and observability boundaries

2. **Asset/Context Layer**
   - Normalized assets and relationships
   - Lightweight graph-context model for risk chains

3. **Decision Layer**
   - Control decisions, findings, confidence, lifecycle, exceptions
   - Compliance mappings, action items, historical snapshots

4. **Reporting & Experience Layer**
   - Technical artifacts, executive artifacts, and interactive dashboard

---

## Dashboard Experience

The pipeline now generates:

- `outputs/reports/cris_sme_dashboard_payload.json`
- `outputs/reports/cris_sme_dashboard.html`

The dashboard includes:

- executive risk overview
- domain score breakdown
- trend and drift panel
- filterable finding explorer
- compliance and readiness view
- confidence/evidence quality section
- graph-context risk section
- remediation and exceptions summary

If you do not have screenshots checked in yet, use these placeholders in docs/slides:

- `docs/assets/dashboard-overview-placeholder.png`
- `docs/assets/dashboard-explorer-placeholder.png`

---

## Repository Structure

```text
CRIS-SME/
├── data/
├── docs/
├── notebooks/
├── outputs/
├── scripts/
├── src/cris_sme/
│   ├── collectors/
│   ├── controls/
│   ├── engine/
│   ├── models/
│   ├── policies/
│   ├── reporting/
│   └── main.py
├── tests/
├── requirements.txt
└── pyproject.toml
```

---

## Quickstart

### 1) Setup

```bash
git clone https://github.com/m-khan-97/CRIS-SME.git
cd CRIS-SME
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Run Mock Mode (default)

```bash
PYTHONPATH=src python3 -m cris_sme.main
```

### 3) Run Azure Mode

```bash
export CRIS_SME_COLLECTOR=azure
export AZURE_SUBSCRIPTION_ID=<your-subscription-id>   # optional filter
PYTHONPATH=src python3 -m cris_sme.main
```

### 4) Run Optional Narrator (never changes deterministic scoring)

```bash
export CRIS_SME_ENABLE_NARRATOR=true
export ANTHROPIC_API_KEY=<key>
PYTHONPATH=src python3 -m cris_sme.main
```

### 5) Run Tests

```bash
PYTHONPATH=src pytest
```

---

## Scripted Runs

Repeatable snapshot:

```bash
python3 scripts/run_assessment_snapshot.py --collector mock
```

AzureGoat-tagged run metadata:

```bash
python3 scripts/run_azuregoat_assessment.py
```

---

## Output Artifacts

Main report outputs:

- `outputs/reports/cris_sme_report.json`
- `outputs/reports/cris_sme_report.html`
- `outputs/reports/cris_sme_summary.txt`
- `outputs/reports/cris_sme_dashboard_payload.json`
- `outputs/reports/cris_sme_dashboard.html`

Actionability and governance:

- `outputs/reports/cris_sme_30_day_action_plan.{md,json}`
- `outputs/reports/cris_sme_executive_pack.{md,json}`
- `outputs/reports/cris_sme_cyber_insurance_evidence.{md,json}`

Research and appendix artifacts:

- `outputs/reports/results_appendix.md`
- `outputs/reports/prioritized_risks.csv`
- `outputs/reports/cris_sme_benchmark_observation.json`
- `outputs/reports/cris_sme_benchmark_comparison.md`
- `outputs/reports/history/*.json`

Figures:

- `outputs/figures/live_category_scores.{svg,png}`
- `outputs/figures/live_priority_distribution.{svg,png}`
- `outputs/figures/risk_trend.{svg,png}`
- `outputs/figures/run_comparison.{svg,png}`

---

## Deterministic Scoring Principles

CRIS-SME keeps scoring deterministic and explainable.

- Severity weights are fixed and explicit.
- Modifiers are formula-driven (exposure, data sensitivity, confidence, remediation effort).
- Confidence calibration is transparent and recorded.
- Narrator output is optional translation only; it is not scoring authority.

See: [docs/scoring-model.md](/Users/vishnuajith/Downloads/CRIS-SME/docs/scoring-model.md)

---

## Current Provider Coverage

- **Azure**: active (mock + live collection path)
- **AWS**: planned (adapter scaffolding only)
- **GCP**: planned (adapter scaffolding only)

CRIS-SME does not claim live multicloud parity yet.

See: [docs/provider-capability-matrix.md](/Users/vishnuajith/Downloads/CRIS-SME/docs/provider-capability-matrix.md)

---

## Current Maturity and Known Limits

Strong today:

- deterministic control/scoring pipeline
- evidence lineage fields and lifecycle model
- rich output and dashboard surfaces
- historical drift comparisons
- robust automated tests

Still conservative/partial:

- full tenant-wide identity observability in all environments
- some budget/governance live evidence paths
- AWS/GCP live collectors
- full attack-path simulation (graph context is lightweight and explicit about scope)

---

## Design Principles

- Deterministic before probabilistic
- Evidence-backed before narrative
- Honest about observability boundaries
- Provider-neutral core, Azure-first execution
- Actionability over alert volume
- Home-lab runnable by default

---

## Documentation Index

Core:

- [docs/project-overview.md](/Users/vishnuajith/Downloads/CRIS-SME/docs/project-overview.md)
- [docs/architecture.md](/Users/vishnuajith/Downloads/CRIS-SME/docs/architecture.md)
- [docs/methodology.md](/Users/vishnuajith/Downloads/CRIS-SME/docs/methodology.md)
- [docs/scoring-model.md](/Users/vishnuajith/Downloads/CRIS-SME/docs/scoring-model.md)
- [docs/compliance-mapping.md](/Users/vishnuajith/Downloads/CRIS-SME/docs/compliance-mapping.md)
- [docs/dashboard.md](/Users/vishnuajith/Downloads/CRIS-SME/docs/dashboard.md)

Platform internals:

- [docs/data-model.md](/Users/vishnuajith/Downloads/CRIS-SME/docs/data-model.md)
- [docs/evidence-lineage.md](/Users/vishnuajith/Downloads/CRIS-SME/docs/evidence-lineage.md)
- [docs/control-lifecycle.md](/Users/vishnuajith/Downloads/CRIS-SME/docs/control-lifecycle.md)
- [docs/finding-lifecycle.md](/Users/vishnuajith/Downloads/CRIS-SME/docs/finding-lifecycle.md)
- [docs/history-and-drift.md](/Users/vishnuajith/Downloads/CRIS-SME/docs/history-and-drift.md)
- [docs/frontend-architecture.md](/Users/vishnuajith/Downloads/CRIS-SME/docs/frontend-architecture.md)
- [docs/provider-capability-matrix.md](/Users/vishnuajith/Downloads/CRIS-SME/docs/provider-capability-matrix.md)

Roadmap:

- [docs/multi-cloud-expansion.md](/Users/vishnuajith/Downloads/CRIS-SME/docs/multi-cloud-expansion.md)
- [docs/roadmap.md](/Users/vishnuajith/Downloads/CRIS-SME/docs/roadmap.md)

---

## Contribution Notes

- Keep control logic deterministic and reviewable.
- Do not hide missing evidence as compliant.
- Update docs when behavior changes.
- Add/adjust tests for any scoring, lifecycle, or reporting contract change.

---

## License

MIT License
