# Risk Bill of Materials

The CRIS-SME Risk Bill of Materials, or RBOM, is an integrity and provenance manifest for one assessment run.

It answers:

- what run produced this report?
- which policy pack and scoring model were used?
- which controls and findings were in scope?
- which evidence references supported decisions?
- what evidence sufficiency states were present?
- what Decision Ledger events were generated?
- which report artifacts were produced?
- what are the SHA-256 hashes of the report context and artifacts?

## Purpose

CRIS-SME is designed for evidence-driven governance. A normal report explains risk; the RBOM proves what the report was made from.

This supports:

- reproducible research
- audit and assurance workflows
- future report verification
- UKRI-style innovation claims around trustworthy cloud governance
- future cryptographic signing

## Current Fields

The RBOM includes:

- `rbom_schema_version`
- `generated_at`
- `run_id`
- `report_schema_version`
- `engine_version`
- `scoring_model`
- `policy_pack_version`
- `collector_mode`
- `providers_in_scope`
- `canonical_report_sha256`
- `control_ids`
- `finding_ids`
- `evidence_refs`
- `evidence_sufficiency_counts`
- `decision_ledger_event_counts`
- `artifacts`
- `integrity_algorithm`
- `signature_note`

## Integrity Model

The current RBOM uses SHA-256 integrity hashes.

`canonical_report_sha256` is calculated from a canonical JSON representation of the report while excluding the self-referential RBOM block.

Artifact hashes are calculated from files already written during the reporting pipeline, such as:

- HTML report
- summary report
- dashboard payload
- dashboard HTML
- insurance evidence pack
- action plan
- appendix tables
- figures

## Signature Boundary

The current RBOM is an integrity manifest, not a public-key cryptographic signature.

The next step is to add a signing workflow where the RBOM itself can be signed with a local private key, CI signing identity, or future hosted signing service.

## Output

The pipeline writes:

- `outputs/reports/cris_sme_risk_bill_of_materials.json`

The main report also embeds the RBOM under:

- `risk_bill_of_materials`

## Verification

CRIS-SME includes an RBOM verification command:

```bash
PYTHONPATH=src python3 scripts/verify_rbom.py \
  --report outputs/reports/cris_sme_report.json \
  --rbom outputs/reports/cris_sme_risk_bill_of_materials.json \
  --base-dir .
```

The verifier checks:

- the canonical report hash
- every artifact hash listed in the RBOM
- missing artifact paths
- mismatched artifact hashes

The command exits with status `0` when verification passes and `1` when integrity fails.

## Detached Signature

CRIS-SME can also create a detached HMAC-SHA256 RBOM signature:

```bash
export CRIS_SME_RBOM_SIGNING_KEY="<shared signing secret>"
PYTHONPATH=src python3 scripts/sign_rbom.py \
  --rbom outputs/reports/cris_sme_risk_bill_of_materials.json \
  --output outputs/reports/cris_sme_risk_bill_of_materials.signature.json \
  --key-id local-dev
```

Verify the report, RBOM, artifacts, and detached signature together:

```bash
PYTHONPATH=src python3 scripts/verify_rbom.py \
  --report outputs/reports/cris_sme_report.json \
  --rbom outputs/reports/cris_sme_risk_bill_of_materials.json \
  --signature outputs/reports/cris_sme_risk_bill_of_materials.signature.json \
  --base-dir .
```

The current signature mode uses a shared secret. It is useful for CI and controlled research workflows. A future public-key signing mode can be added without changing the RBOM integrity model.
