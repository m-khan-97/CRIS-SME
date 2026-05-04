# Innovation and UKRI Readiness

CRIS-SME's immediate priority is technical transformation: making the system novel, defensible, and research-grade before optimizing for customers, investors, or sales packaging.

This document frames CRIS-SME as an innovation project that could later support UKRI-style funding, especially where the work advances cloud governance for SMEs beyond generic scanning.

## Innovation Thesis

Most cloud security tools identify misconfigurations. CRIS-SME aims to do something more ambitious:

> Convert uncertain, partial, provider-specific cloud evidence into deterministic, auditable, lifecycle-aware risk decisions for SMEs.

The innovative core is the decision methodology, not the collector alone.

## What Could Be Novel

### 1. Evidence Sufficiency For Cloud Governance

CRIS-SME can formally distinguish:

- sufficient evidence
- partial evidence
- inferred evidence
- unavailable evidence
- stale evidence
- unsupported provider evidence

This is stronger than treating all missing evidence as either safe or failed.

### 2. Deterministic Risk Decisions With Confidence Calibration

CRIS-SME already separates observed confidence from calibrated confidence. The next step is a richer confidence model that accounts for:

- collector capability
- provider permission scope
- evidence freshness
- sample validation
- native-cloud disagreement
- control maturity

### 3. Risk Bill Of Materials

Inspired by SBOM thinking, CRIS-SME can create a Risk Bill of Materials:

- assessed scope
- policy-pack version
- controls evaluated
- evidence records used
- unavailable evidence
- finding IDs
- score model version
- exception state
- report hashes

This would make cloud risk reporting more reproducible and verifiable.

### 4. Decision Ledger

CRIS-SME can maintain an append-only governance record:

- when a finding first appeared
- why it scored the way it did
- who accepted or assigned it
- which exception applied
- when risk reappeared
- what evidence changed

This turns cloud assessment into governance memory.

### 5. Counterfactual Remediation Simulation

Instead of only reporting current posture, CRIS-SME can answer:

- what happens if this control is fixed?
- which three actions reduce the most risk?
- which actions improve insurance readiness fastest?
- which risks persist because evidence is still unavailable?

The simulator must remain deterministic and explainable.

### 6. AI Narration Under Deterministic Constraint

CRIS-SME can use AI only to translate deterministic outputs:

- no AI-created findings
- no AI score changes
- no invented evidence
- every narrative cites deterministic report fields

This creates a safer pattern for AI in cyber governance.

## UKRI-Style Problem Statement

SMEs face growing pressure to evidence cyber resilience to customers, insurers, supply chains, and regulators, but they often lack the budget, staff, and tooling maturity required by enterprise cloud security platforms.

Current tools commonly produce either high-volume technical alerts or static compliance checklists. Neither reliably converts partial cloud evidence into explainable, auditable, and prioritized risk decisions that SMEs can act on.

CRIS-SME addresses this gap by developing a deterministic, evidence-driven cloud risk decision methodology that records observability boundaries, calibrates confidence, tracks lifecycle state, and produces stakeholder-ready governance outputs.

## Potential Funding Themes

CRIS-SME could align with innovation themes around:

- SME cyber resilience
- trusted and explainable AI-assisted security
- cloud governance automation
- cyber insurance evidence and assurance
- supply-chain cyber readiness
- digital trust and responsible security tooling
- privacy-preserving/local-first cloud assessment

## Research Questions

1. How can cloud risk findings remain useful when evidence is partial or unavailable?
2. Can deterministic scoring produce more trusted SME remediation decisions than generic alert severity?
3. How should cloud risk confidence be calibrated across synthetic, lab, and live evidence modes?
4. Can lifecycle and exception tracking reduce repeated cloud governance regressions?
5. Can an AI narrator improve stakeholder understanding without altering deterministic cyber risk decisions?
6. Can a Risk Bill of Materials improve reproducibility and assurance in SME cloud governance?

## Technical Work Packages

### Work Package 1: Evidence Sufficiency Model

Deliverables:

- evidence sufficiency enum
- per-control evidence requirements
- dashboard confidence heatmap
- report appendix for unavailable evidence

### Work Package 2: Decision Ledger

Deliverables:

- ledger event schema
- finding lifecycle event model
- run-to-run decision diff
- exception approval history

### Work Package 3: Risk Bill Of Materials

Deliverables:

- signed manifest schema
- artifact hash generation
- evidence hash references
- verification command

### Work Package 4: Remediation Simulator

Deliverables:

- deterministic simulation API
- expected risk reduction per action
- before/after score comparison
- insurance-readiness delta

### Work Package 5: Constrained AI Narrator

Deliverables:

- source-grounded narrator prompt contract
- citation checks
- hallucination guardrails
- deterministic report authority disclaimer

### Work Package 6: Multi-Mode Evaluation

Deliverables:

- synthetic baseline dataset
- live Azure repeated runs
- vulnerable-lab runs
- comparison notebooks
- confidence calibration updates

## Evidence Needed For A Strong Funding Application

- clear prototype demo
- reproducible assessment pipeline
- documented novelty
- technical architecture
- early validation results
- SME problem evidence
- pilot plan
- ethics and security considerations
- exploitation path after R&D

## Immediate Build Priority

The strongest next implementation step is the evidence sufficiency model because it strengthens nearly every other CRIS-SME claim:

- scoring becomes more defensible
- reports become more honest
- AI narration has safer source boundaries
- UKRI novelty becomes clearer
- provider expansion becomes less risky
- insurance readiness becomes more credible
