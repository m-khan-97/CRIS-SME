# Conference Abstract Draft

## Working Title

CRIS-SME: An Explainable Cloud Risk Intelligence Framework for SME Azure Governance Assessment

## Draft Abstract

Small and medium enterprises (SMEs) adopting cloud infrastructure frequently face a governance gap: enterprise-grade cloud security tooling is often too complex, too costly, or too opaque for smaller organizations, while lightweight alternatives rarely provide structured, explainable risk intelligence. This paper presents CRIS-SME, a Cloud Risk Intelligence System designed to support SME-oriented cloud governance assessment through deterministic control evaluation, explainable scoring, compliance mapping, and progressively enriched live-cloud evidence collection.

CRIS-SME uses a provider-neutral core architecture with an Azure-first implementation. The framework evaluates cloud posture across identity and access management, network exposure, data protection, monitoring and logging, compute/workload hardening, and governance hygiene. Findings are translated into normalized risk objects, scored using a deterministic model, and aggregated into category-level and overall risk views. To support research transparency, CRIS-SME records collection provenance, explicit observability boundaries, archived run history, and appendix-ready outputs for downstream analysis.

The current implementation was validated using both synthetic SME profiles and repeated live Azure-backed assessment runs. In the latest live Azure case study, CRIS-SME observed `16` non-compliant findings and produced an overall risk score of `33.12/100`. The most significant risks related to public administrative network exposure, broadly permissive network rules, Linux password-based SSH access, incomplete key-management protections, and weak endpoint/workload protection coverage. Identity evidence was strengthened through subscription-scoped privileged role assessment and Entra-adjacent directory-role visibility, while still explicitly marking tenant-wide conditional-access observability as partial where access was constrained.

The contribution of CRIS-SME is not a claim of fully autonomous security intelligence, but a research-backed, explainable, and iteratively extensible governance assessment framework that is practical for SMEs. The framework demonstrates how deterministic risk analytics, provenance-aware reporting, archived-run comparison, and lightweight research artifacts can form a credible bridge between engineering implementation and publishable cloud governance research.

## Evaluation and Results Notes

Current empirical points available for a paper or poster draft:

- mock archived run overall risk: `39.90`
- latest live Azure archived run overall risk: `33.12`
- live versus mock delta: `-6.78`
- latest live run history count: `4`
- latest live IAM observability state: `broad`
- latest live visible directory-role catalog entries: `57`

## Candidate Contribution Framing

Possible contributions section wording:

1. a provider-neutral cloud risk intelligence core tailored to SME governance needs
2. an explainable deterministic scoring model aligned with auditability and research defensibility
3. a provenance-aware reporting pipeline with archived run comparison and appendix-ready outputs
4. an Azure-first live collection path that explicitly reports identity observability boundaries rather than overclaiming tenant-wide visibility

## Suggested Next Draft Step

The next refinement should convert this abstract into a structured conference submission package with:

- problem statement
- research motivation
- method
- evaluation snapshot
- contributions
- limitations and future work
