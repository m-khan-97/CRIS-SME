# Assessment Replay and Evidence Diff

Assessment Replay lets CRIS-SME re-run deterministic decisions from a saved normalized evidence snapshot.

It answers:

- can this assessment be reproduced without recollecting cloud data?
- did score movement come from evidence drift or policy-pack change?
- did the current engine produce the same finding inputs from the same evidence?
- can historical outputs be verified as deterministic decision artifacts?

## Evidence Snapshot

Each run now emits:

`outputs/reports/cris_sme_evidence_snapshot.json`

The snapshot includes:

- normalized profile evidence
- deterministic finding inputs
- collector mode
- policy-pack version
- providers in scope
- control IDs
- SHA-256 hashes for profiles, findings, and the snapshot envelope

The snapshot is also embedded in the JSON report under:

`evidence_snapshot`

## Replay Output

Reports include:

`assessment_replay.replay`

This contains:

- `replayable`
- `deterministic_match`
- `profile_hash_verified`
- `finding_hash_verified`
- original and replayed risk scores
- category score deltas
- classified change reasons

Replay does not call Azure, AWS, GCP, or any live collector. It uses only saved normalized evidence.

## Evidence Diff

Reports also include:

`assessment_replay.evidence_diff`

This classifies:

- `evidence_changed`
- `policy_pack_changed`
- `collector_mode_changed`
- profile/finding count deltas
- added or removed controls
- `score_delta_reason`

This distinction matters because CRIS-SME should explain whether risk changed because the cloud changed, the policy pack changed, or the collector/evaluation mode changed.

## CLI

Replay the latest generated snapshot:

```bash
PYTHONPATH=src python3 scripts/replay_assessment.py \
  --snapshot outputs/reports/cris_sme_evidence_snapshot.json
```

Compare two snapshots or reports:

```bash
PYTHONPATH=src python3 scripts/replay_assessment.py \
  --snapshot outputs/reports/cris_sme_report.json \
  --previous-snapshot outputs/reports/history/cris_sme_report_YYYYMMDDTHHMMSSZ.json
```

Fail a CI job if replay does not match deterministically:

```bash
PYTHONPATH=src python3 scripts/check_replay_determinism.py \
  --snapshot outputs/reports/cris_sme_evidence_snapshot.json
```

## CI Gate

The reusable Python quality workflow checks for `cris_sme_evidence_snapshot.json` whenever the mock pipeline runs.

It then runs deterministic replay verification. Pull requests therefore prove not only that tests pass, but that generated evidence can reproduce the same control findings and risk score.

## Product Significance

This turns CRIS-SME into an auditable risk decision laboratory.

The same evidence can be replayed against the current engine, compared with prior evidence, and used to explain score movement without relying on opaque scanner state.
