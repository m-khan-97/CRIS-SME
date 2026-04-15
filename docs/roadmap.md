# Roadmap

This document tracks implementation phases for the CRIS-SME framework and helps separate completed MVP work from the next research-grade milestones.

## Completed Foundations

- repository scaffold and Python package structure
- provider-neutral core models with Azure-first implementation
- synthetic SME posture dataset
- deterministic scoring engine with explainability
- control coverage across IAM, Network, Data, Monitoring, Compute, and Governance
- compliance mapping layer
- JSON, text, and HTML reporting
- live Azure collector with evidence across Network, Data, Monitoring, Compute, and Governance
- live Azure case-study documentation

## Near-Term Priorities

- improve live Azure budget and cost-governance collection
- accumulate repeated-run history for more meaningful longitudinal comparison
- refine evaluation and manuscript material for conference submission
- formalize AWS and GCP expansion from planning into mock-provider implementation

## Medium-Term Research Work

- evaluate scoring sensitivity across multiple SME-style environments
- compare deterministic prioritisation with later AI-assisted prioritisation approaches
- develop notebook-based experiments for category weighting and control confidence
- formalize export pipelines for conference figures and tables
- compare provider-specific observability boundaries across Azure, AWS, and GCP

## Longer-Term Platform Direction

- implement live AWS and GCP collectors behind the existing adapter architecture
- support repeated assessments and longitudinal comparison at larger scale
- explore lightweight dashboarding once the collector and scoring layers stabilize
- package CRIS-SME as a reproducible research and demo framework
