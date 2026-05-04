# Decision Ledger

The CRIS-SME Decision Ledger is an append-only governance-memory layer for assessment runs.

It records what changed, what recurred, what was resolved, and which lifecycle or exception decisions affected a finding.

## Purpose

Cloud risk governance fails when each scan is treated as a standalone snapshot. SMEs need to know:

- when a finding first appeared
- whether it is new or recurring
- whether its score changed
- whether it was resolved
- whether an exception was applied or expired
- which evidence references supported the decision

The Decision Ledger gives CRIS-SME that memory.

## Event Types

- `assessment_recorded`: one assessment run was recorded
- `finding_opened`: a finding is present now and absent from the previous run
- `finding_recurred`: a finding is present in both current and previous runs
- `finding_resolved`: a previous finding is absent from the current run
- `score_changed`: a recurring finding's score changed
- `lifecycle_status_changed`: a finding's lifecycle state changed
- `exception_applied`: an accepted-risk or suppression record affected the finding
- `exception_expired`: an exception exists but has expired

## Ledger Fields

Each event includes:

- event ID
- event type
- event time
- run ID
- finding ID
- control ID
- provider
- organization
- resource scope
- previous/current score
- previous/current status
- summary
- evidence refs
- metadata such as priority, sufficiency, and exception ID

## Innovation Value

The ledger turns CRIS-SME from a report generator into a risk decision memory system.

This is important for the project direction because it supports:

- longitudinal governance
- recurring-regression analysis
- accepted-risk accountability
- evidence-backed assurance
- future audit and UKRI-style evaluation

## Current Implementation

The ledger is built from the current report plus archived history.

The current report includes:

- `decision_ledger.ledger_schema_version`
- `decision_ledger.current_run_id`
- `decision_ledger.previous_run_id`
- `decision_ledger.current_evaluation_mode`
- `decision_ledger.previous_evaluation_mode`
- `decision_ledger.comparison_basis`
- `decision_ledger.event_count`
- `decision_ledger.events`

The dashboard payload also includes a compact `decision_ledger` summary for future UI rendering.

## Mode-Aware Comparison

CRIS-SME supports multiple evaluation modes:

- synthetic baseline
- live Azure
- intentionally vulnerable lab
- other archived assessment modes

The Decision Ledger defaults to `same_evaluation_mode` comparison. This means a synthetic run is compared with the latest previous synthetic run, a live Azure run is compared with the latest previous live Azure run, and so on.

This avoids misleading ledger events when a user switches between mock, live, and lab assessments.

Future API or research workflows can still request `latest_any` comparison when chronological cross-mode comparison is intentionally required.
