# Compliance Mapping

CRIS-SME includes a machine-readable compliance interpretation layer.

## Purpose

Translate technical findings into governance context without claiming formal certification.

The mapping layer supports:

- framework coverage summaries
- control-to-framework traceability
- findings-by-framework counts
- UK-focused profile reporting for SME relevance

## Data Sources

- `data/compliance_mappings.json`
- `data/control_catalog.json`

## Current Coverage

Mappings currently span 13 frameworks/guidance sets, including:

- ISO 27001
- NIST CSF 2.0
- Cyber Essentials
- UK GDPR
- FCA SYSC
- DSPT
- CIS/Azure/FinOps references

## UK SME Profile

CRIS-SME derives a UK-oriented summary from mapped findings:

- frameworks covered
- mapped control count
- mapped finding count
- finding counts per UK-relevant framework

This is a governance crosswalk, not legal advice.

## Mapping Contract

Each mapped finding includes:

- control ID
- title/category
- compliance state
- provider/provider scope
- list of mapped references

## Limit Boundaries

The mapping layer:

- is useful for interpretation and reporting
- is not a compliance certification engine
- does not replace formal audit evidence collection
