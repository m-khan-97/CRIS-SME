# Project Overview

CRIS-SME is a cloud risk governance platform for SMEs that converts posture evidence into explainable, defensible risk decisions.

It is intentionally built around deterministic engineering and explicit evidence boundaries, not opaque AI-first scoring.

Tagline:

> Evidence in. Decisions out.

## Core Goal

Transform cloud posture into decision-quality outputs that SMEs can actually use:

1. collect posture evidence
2. evaluate deterministic controls
3. score and prioritize risk
4. map to governance/compliance references
5. produce action plans and stakeholder-ready outputs
6. track drift over time

## Product Position

CRIS-SME is the decision layer between cloud evidence and accountable risk action.

It sits between:

- enterprise CNAPP/CSPM platforms (often too heavy for SMEs)
- simple scanners (often high volume, low decision context)
- GRC and insurance workflows that demand proof but often lack live cloud evidence

CRIS-SME focuses on:

- explainability
- affordability-aware remediation
- UK-oriented governance framing
- practical local execution
- insurance and board-ready assurance outputs
- lifecycle-aware risk ownership

## Current System Shape

- Azure-first live collector path
- Provider-neutral core models
- 6 domains / 26 controls
- Deterministic scoring with confidence calibration
- Finding lifecycle + exception support
- Lightweight graph-context prioritization
- Historical drift outputs
- Interactive dashboard output and technical export suite
- GitHub Actions CI/CD with Vercel-ready static hosting path

## Current Maturity

Production-shaped in architecture and outputs, still pragmatic in scope:

- active live support: Azure
- planned live support: AWS, GCP
- explicit partial-observability handling in identity/governance areas where needed

CRIS-SME does not claim complete multicloud parity today.

## Product North Star

CRIS-SME should become the cloud risk decision system of record for SMEs and MSPs.

The next product stage is to add:

- Decision Ledger
- Risk Bill of Materials
- Assessment Replay and Evidence Diff
- Assessment Assurance
- Evidence Gap Backlog
- Control Drift Attribution
- Policy Pack Changelog
- remediation simulator
- evidence sufficiency model
- signed report manifests
- SaaS/API layer
- role-based dashboard views
- AI narrator layer that never changes deterministic results
