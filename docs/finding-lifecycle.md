# Finding Lifecycle

CRIS-SME supports lifecycle-aware findings and exception enrichment.

## Lifecycle Statuses

- `open`
- `accepted_risk`
- `in_progress`
- `resolved`
- `suppressed`
- `expired_exception`

## Lifecycle Enrichment Fields

Per finding:

- `first_seen`
- `last_seen`
- `previous_seen`
- `is_new`
- `seen_count`
- `recurrence_count`
- optional `exception` metadata

Report-level:

- `finding_lifecycle_summary`
  - status counts
  - new/existing counts
  - exception application counts

## Exception Registry

Exceptions are loaded from:

- `data/finding_exceptions.json`

Fields include:

- exception ID
- control ID
- provider/scope
- reason
- approved by
- status
- expiry
- compensating control

Expired exceptions are surfaced as `expired_exception`.
