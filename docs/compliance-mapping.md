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

## Current Positioning

The current mapping layer should be understood as:

- a governance interpretation aid
- a traceability mechanism between findings and references
- a research-friendly way to discuss alignment with external standards

It should not be described as:

- a compliance certification engine
- a substitute for formal audit evidence
- a complete implementation of any named framework

## Future Direction

As CRIS-SME matures, the mapping layer can be extended to support:
- richer framework catalogs
- control-to-control crosswalks
- provider-specific mapping nuances
- evidence traceability for stronger audit support
