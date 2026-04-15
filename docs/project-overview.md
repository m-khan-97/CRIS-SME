# Project Overview

CRIS-SME is a cloud risk intelligence framework for SMEs, with an initial implementation focus on Azure governance and compliance assessment.

The project is motivated by a practical and research-relevant problem: many SMEs adopting cloud services do not have access to structured governance practices, automated control validation, or lightweight risk intelligence tooling that fits their scale. CRIS-SME is intended to bridge that gap with a framework that is technically useful, explainable, and suitable for iterative research.

## Core Objective

The objective of CRIS-SME is to transform cloud posture observations into decision-useful risk intelligence through a repeatable pipeline:

- collect or ingest provider posture data
- normalize that data into a common internal model
- evaluate governance and compliance controls
- score findings in an explainable way
- aggregate results into category and overall views
- generate outputs suitable for engineering, demos, and research communication

## Current MVP Scope

The current MVP uses synthetic SME posture data and mock collection to validate the framework design before live cloud integration. This keeps the early system:

- easier to test
- easier to reason about
- suitable for rapid scoring experiments
- credible as a research prototype without overstating production readiness

## Implemented MVP Domains

The current control coverage spans six governance areas:

- IAM
- Network
- Data Protection
- Monitoring and Logging
- Compute and Workloads
- Cost and Governance Hygiene

Each domain produces structured findings that can be scored, prioritised, and mapped to external governance references.

## Research Positioning

CRIS-SME is designed to support several parallel outcomes:

- a practical engineering framework for SME-oriented cloud posture assessment
- a defensible scoring model for explainable risk prioritisation
- a demonstrable platform for conference papers, posters, and technical demos
- a foundation for later AI-assisted prioritisation research

## Delivery Philosophy

The implementation strategy is intentionally conservative:

- deterministic scoring first
- mock and synthetic data before live provider integration
- modular controls before dashboard work
- explainability before AI claims
- provider-neutral core before broader multi-cloud expansion

This approach keeps the project academically credible and engineering-friendly at the same time.
