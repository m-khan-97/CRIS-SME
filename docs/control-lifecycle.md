# Control Lifecycle

CRIS-SME control governance is catalog + spec driven.

## Control Sources

- **Control catalog** (`data/control_catalog.json`):
  - control IDs
  - category
  - title
  - remediation metadata
  - baseline mappings

- **Control specs** (`src/cris_sme/policies/control_specs.py` + overrides):
  - intent
  - applicability
  - evidence requirements
  - provider support state
  - known limitations
  - confidence penalty guidance
  - version metadata

## Lifecycle Philosophy

1. Define control in catalog.
2. Attach governance metadata in control spec.
3. Evaluate deterministically in domain module.
4. Emit finding with rule version + trace metadata.
5. Track lifecycle over historical runs.

## Versioning

- Policy pack version is emitted in report `run_metadata.policy_pack`.
- Each finding carries `rule_version`.
- Version increments should be documented when logic materially changes.
