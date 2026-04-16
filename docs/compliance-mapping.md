# Compliance Mapping

CRIS-SME includes a lightweight compliance mapping layer that connects findings to relevant governance references and standards. The purpose is to provide interpretive context rather than to claim formal audit readiness or automated certification.

## Purpose

The mapping layer helps answer questions such as:

- which governance frameworks are touched by a finding
- which standards are most frequently implicated in an assessment
- how technical findings can be translated into policy-oriented language

This is useful for SME decision-makers, technical demonstrations, and research communication.

## Current Approach

The current MVP stores mappings in `data/compliance_mappings.json` and evaluates them against generated findings.

Each mapping entry can describe:
- the control identifier
- the target framework or reference
- provider scope
- category alignment
- descriptive metadata for reporting

The engine then aggregates:
- matched frameworks
- mapped finding counts
- finding-to-framework associations
- a dedicated UK SME regulatory profile summary

## Current Positioning

The current mapping layer should be understood as:

- a governance interpretation aid
- a traceability mechanism between findings and references
- a research-friendly way to discuss alignment with external standards

It should not be described as:

- a compliance certification engine
- a substitute for formal audit evidence
- a complete implementation of any named framework

## UK SME Regulatory Profile

CRIS-SME now includes a UK-focused interpretation layer intended to strengthen the project's practical and research relevance for British SMEs. The current profile highlights controls that map into:

- Cyber Essentials
- UK GDPR
- FCA SYSC
- DSPT

This is intentionally positioned as a lightweight regulatory crosswalk rather than legal advice or certification automation. The goal is to show where cloud posture findings intersect with UK-relevant obligations and assurance schemes that matter in SME settings.

The UK summary is designed to answer questions such as:

- which findings are relevant to Cyber Essentials readiness
- which controls intersect with UK GDPR security-of-processing expectations
- which findings are especially relevant to FCA-regulated SMEs
- which controls have healthcare-adjacent relevance through DSPT/NDG standards

## Future Direction

As CRIS-SME matures, the mapping layer can be extended to support:
- richer framework catalogs
- control-to-control crosswalks
- sector-specific UK mapping depth, such as FCA and DSPT control-family views
- provider-specific mapping nuances
- evidence traceability for stronger audit support
