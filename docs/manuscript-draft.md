# Manuscript Draft

> Status: working draft for publication.  
> Includes historical/frozen values for narrative consistency; refresh metrics before submission.

## CRIS-SME: An Explainable Cloud Risk Intelligence Framework for SME Cloud Governance Assessment

### Abstract

Small and medium enterprises (SMEs) increasingly depend on cloud infrastructure, yet many lack governance capability, compliance automation, and risk tooling suited to their scale. Enterprise cloud security platforms offer broad coverage, but they are often too costly, operationally heavy, or opaque for smaller organizations. This paper presents CRIS-SME, a Cloud Risk Intelligence System designed for SME-oriented cloud governance assessment through deterministic control evaluation, explainable scoring, UK-oriented compliance framing, and provenance-aware reporting. CRIS-SME uses a provider-neutral core architecture with an Azure-first implementation. The framework evaluates posture across identity and access management, network exposure, data protection, monitoring and logging, compute and workload hardening, and governance hygiene. Findings are normalized into a common risk model, scored using deterministic factors, aggregated into category and overall risk views, and exported into report, figure, and appendix-ready artifacts. The current implementation was evaluated across three evidence modes: synthetic SME profiles, a frozen live Azure case-study snapshot, and an intentionally vulnerable AzureGoat-derived lab track. In the frozen live Azure case study, CRIS-SME identified 18 non-compliant findings and produced an overall risk score of 33.23/100. In the vulnerable-lab track, CRIS-SME also identified 18 non-compliant findings with an overall risk score of 32.79/100. Across the current evidence base, dominant risks relate to public administrative exposure, permissive network rules, Linux password-based SSH access, incomplete key-management protections, and weak endpoint and workload protection coverage. The contribution of CRIS-SME is not a claim of fully autonomous security intelligence, but an explainable and research-defensible framework that bridges practical cloud governance engineering and publishable SME-focused cloud risk research.

### 1. Introduction

Cloud adoption has become an operational necessity for many SMEs, but governance capability has not matured at the same rate. Smaller organizations often move critical workloads into public cloud platforms without structured control baselines, continuous compliance validation, or accessible decision-support tooling. As a result, governance and resilience gaps can accumulate even in relatively small cloud estates.

This problem is intensified by the current market shape of cloud security tooling. Enterprise cloud security posture management platforms offer broad visibility, but they are often designed for organizations with specialist security teams, larger budgets, and mature governance functions. SMEs, by contrast, need simpler and more transparent systems that provide actionable risk insight without imposing excessive operational overhead.

CRIS-SME addresses this gap by proposing an explainable cloud risk intelligence framework tailored to SME cloud governance assessment. The framework prioritizes deterministic control evaluation, explicit evidence provenance, modular architecture, and repeatable outputs suitable for engineering use and research dissemination. Rather than beginning with opaque AI-based prioritization, CRIS-SME starts with interpretable governance logic and treats AI-assisted prioritization as a later-stage extension rather than a foundational dependency.

The current reference implementation is Azure-first, but the architecture is intentionally provider-neutral at the core. This creates a realistic delivery path: credible live Azure evidence first, then structured expansion toward additional providers such as AWS and GCP.

The main contributions of this work are:

1. an SME-oriented cloud governance assessment framework with a provider-neutral core and Azure-first implementation
2. a deterministic and explainable scoring engine that converts governance findings into interpretable risk outputs
3. a provenance-aware reporting pipeline with archived run history, comparison figures, and appendix-ready exports
4. a live Azure validation path that explicitly records observability boundaries instead of overstating coverage

### 2. Problem Statement and Motivation

UK SMEs migrating to cloud environments frequently lack structured governance frameworks, automated compliance validation mechanisms, and risk intelligence systems tailored to their scale. Existing enterprise-grade solutions are often cost-prohibitive or operationally complex, creating a measurable governance and compliance gap. This gap matters not only for security but also for resilience, accountability, and the practical ability to make cloud risk visible to decision-makers.

The motivation behind CRIS-SME is therefore twofold. First, there is an engineering need for a lightweight framework that can turn cloud posture observations into prioritized, explainable findings. Second, there is a research need for a defensible technical artifact that supports empirical case studies, repeatable experimentation, and comparative analysis across environments.

### 3. Related Work and Positioning

The dominant commercial cloud posture market is led by enterprise CNAPP and CSPM platforms such as Microsoft Defender for Cloud, Wiz, and Orca Security. These platforms emphasize broad visibility, context-rich prioritization, graph or attack-path reasoning, and integrated multicloud workflows. They establish the state of practice in commercial posture management, but they are generally oriented toward larger estates, specialist teams, and enterprise procurement models rather than SME-specific governance usability.

Open-source auditing tools such as Prowler and Scout Suite provide a more lightweight comparison point. They are much closer in spirit to CRIS-SME because they favor transparent assessment and portable outputs over fully managed platforms. However, their output model remains largely scanner-centric: they surface broad sets of findings and generic control references, but typically stop short of explainable aggregate scoring, UK-specific governance framing, budget-aware action planning, or stakeholder-ready evidence packaging.

Provider-native posture tooling is also relevant because it defines the default baseline many SMEs already encounter. Microsoft Defender for Cloud provides built-in recommendations, standards mappings, and secure-score style aggregation inside Azure and the wider Microsoft ecosystem. In CRIS-SME, this makes Defender especially useful as an external validation reference rather than as a system CRIS-SME is trying to replace.

CRIS-SME therefore occupies a distinct design point. It is not attempting breadth parity with enterprise CNAPP platforms, nor is it simply a wrapper around raw cloud findings. Its contribution is a lighter and more interpretable operating point that combines deterministic score construction, provenance-aware reporting, UK-oriented compliance framing, budget-aware remediation, and outputs suitable for boards, insurers, and research communication. This positioning matters academically because it treats explainability not as a user-interface convenience, but as part of the methodological design of the framework itself.

### 4. Framework Architecture

CRIS-SME is organized into six main layers:

1. collectors
2. provider adapters
3. control modules
4. risk engine
5. compliance mapping
6. reporting and artifact generation

Collectors acquire posture information from either synthetic datasets or live provider APIs and CLIs. Provider adapters normalize raw provider-specific records into a shared internal `CloudProfile` model. Control modules evaluate governance conditions across IAM, Network, Data, Monitoring, Compute, and Governance domains. The risk engine transforms findings into scored, ranked, and aggregated outputs. The compliance layer maps findings into governance references. The reporting layer then converts results into JSON, HTML, text, SVG, PNG, Markdown, and CSV artifacts.

This architecture supports inspection and iteration because each layer can evolve independently. Provider-specific collection can deepen without forcing changes to the scoring model, new reporting artifacts can be added without rewriting controls, and additional providers can be introduced through adapters without rebuilding the core logic.

### 5. Methodology

The methodology follows five principles:

- realism over hype
- explainability over opacity
- modularity over monolithic tooling
- iterative validation over premature platform complexity
- SME suitability over enterprise-only assumptions

The implementation began with synthetic SME posture profiles to validate scoring and control behavior in a repeatable way. Live Azure-backed collection was then added to move the framework beyond mock-only evaluation while preserving explicit provenance. Finally, an intentionally vulnerable AzureGoat-derived lab track was introduced to increase evaluation variance without relying on unauthorized public infrastructure. This staged approach is methodologically defensible because it allows the risk model and control logic to stabilize before live-provider variability is introduced.

The current pipeline is:

1. collect synthetic or live posture evidence
2. normalize evidence into a common cloud profile
3. evaluate governance and compliance controls
4. generate normalized findings
5. score findings using deterministic logic
6. aggregate category and overall risk views
7. map findings to governance references
8. archive report snapshots for repeated-run comparison
9. export reports, figures, and appendix tables

### 6. Scoring Model

CRIS-SME uses a deterministic scoring model designed for interpretability rather than vendor-style opacity. Each finding includes severity, exposure, data sensitivity, confidence, and remediation effort. Severity is mapped using fixed weights:

- Critical = 10
- High = 7
- Medium = 4
- Low = 1

The score modifiers are:

- likelihood factor = `0.8 + 0.8 * exposure`
- data factor = `0.8 + 0.8 * data_sensitivity`
- confidence factor = `0.7 + 0.3 * confidence`
- remediation factor = bounded uplift for operational persistence and effort

Scores are normalized to a 0-100 scale and then aggregated into category averages and a weighted overall score. The current category weighting model is:

- IAM = 25%
- Network = 20%
- Data = 20%
- Monitoring/Logging = 15%
- Compute/Workloads = 10%
- Cost/Governance Hygiene = 10%

This weighting reflects an SME-oriented assumption that identity, external exposure, and data protection should dominate the overall risk picture. The current weights are expert-judgment defaults rather than empirically fitted parameters and should therefore be interpreted as a transparent starting point for future calibration rather than a universal final model.

### 7. Implementation

The implementation is written in Python 3.10+ with typed models using Pydantic v2. The current system includes:

- six control domains
- provider-normalized collection
- live Azure-backed evidence paths
- HTML, JSON, and summary reporting
- archived report history
- SVG and PNG figure generation
- appendix-ready Markdown and CSV exports
- notebook-driven research workflows

The live collector includes Azure-backed evidence across Network, Data, Monitoring, Compute, Governance, and enriched IAM/Entra-adjacent context. It also records observability boundaries instead of silently treating inaccessible evidence as absence.

### 8. Evaluation Design

The present evaluation is structured around three complementary modes:

- synthetic SME baseline assessment
- live Azure-backed case-study assessment
- AzureGoat-derived vulnerable-lab assessment

This evaluation is not framed as a competitive benchmark against commercial CSPM tools. Instead, it addresses three questions:

1. can CRIS-SME turn posture observations into explainable governance findings?
2. does the scoring engine produce interpretable category and overall risk outputs?
3. do archived runs support comparison across different assessment contexts?

### 9. Results

The archived runs currently include a synthetic baseline, a frozen live Azure case-study snapshot, and an active vulnerable-lab track. The live Azure snapshot used as the main empirical reference in this manuscript is `cris_sme_report_20260418T004604Z.json`. Relative to the synthetic baseline, it shows an overall score delta of `-6.61`, indicating a narrower but still meaningful governance-risk profile in the real tenant.

The frozen live Azure assessment produced:

- 18 non-compliant findings
- overall risk score of 33.23
- IAM score: 14.78
- Network score: 47.59
- Data score: 39.75
- Monitoring/Logging score: 36.38
- Compute/Workloads score: 39.02
- Cost/Governance Hygiene score: 27.11

The most significant live findings were:

1. public administrative network exposure
2. permissive network security rules
3. password-based SSH exposure on Linux workloads
4. incomplete key-management protections
5. low endpoint and workload protection coverage

The current AzureGoat-derived vulnerable-lab assessment produced:

- 18 non-compliant findings
- overall risk score of 32.79
- dataset source type `vulnerable_lab`
- authorization basis `intentionally_vulnerable_lab`

This lab-derived run is important because it broadens the evidence base without relying on unauthorized public infrastructure. It also increases evaluation variance by introducing intentionally exposed storage, application, and network conditions. The current deployment was a constrained AzureGoat variant because tenant location policy, Automation Account incompatibility, Basic public-IP restrictions, and live VM-capacity shortages prevented a full stock deployment. This limitation should be disclosed, but it does not negate the value of the environment as an explicitly authorized vulnerable-lab dataset.

Control-level comparison against the previous distinct-mode baseline showed notable increases for several live risks, including `NET-002`, `CMP-005`, `DATA-004`, `CMP-002`, and `MON-002`. This demonstrates that the framework can move beyond headline scores and compare how specific governance conditions differ across synthetic and live contexts.

### 10. Identity and Observability Discussion

IAM is a particularly important area for methodological honesty. The current system can observe subscription-scoped privileged role assignments and some Entra-adjacent signals, including signed-in-user directory-role visibility and tenant directory-role catalog visibility where accessible. In the frozen live Azure case-study snapshot, the signed-in assessment identity exposed zero visible Entra directory roles, while the tenant directory-role catalog exposed 57 visible entries. The resulting observability state was recorded as `broad`.

This does not imply full tenant-wide identity governance coverage. Conditional Access and other tenant-wide controls remain only partially observable in the current implementation. That boundary is explicitly surfaced as a finding (`IAM-005`) and in collection provenance. This is an important design choice because it favors research defensibility over overstated control coverage.

### 11. Discussion

The current results suggest that CRIS-SME is already capable of supporting credible engineering and research workflows. The framework can transform posture evidence into explainable findings, preserve the distinction between observed evidence and limited visibility, and export outputs that are immediately useful for demonstrations, notebooks, figures, and paper drafting. Importantly, the framework now supports three evidence classes: synthetic baseline profiles, production-adjacent live Azure case-study evidence, and intentionally vulnerable lab evidence.

The most important design lesson so far is that transparency matters. Deterministic scoring, explicit provenance, and archived comparison provide a stronger foundation for both trust and academic communication than a premature move toward opaque “AI risk intelligence” claims.

### 12. Limitations

The present work has several limitations:

- evaluation currently centers on a single live Azure subscription
- the current vulnerable-lab track is based on one constrained AzureGoat deployment variant
- repeated live runs currently show stability more than operational drift
- some Entra-wide controls remain only partially observable
- AWS and GCP expansion remains at adapter-planning stage
- the scoring model, while explainable, still requires broader empirical calibration

These limitations do not undermine the framework. Instead, they define the current maturity boundary clearly.

### 13. Threats to Validity

The current study has several threats to validity that should be stated explicitly in any submission.

#### 13.1 Internal Validity

CRIS-SME relies on deterministic control logic and a manually engineered scoring model. Although this improves explainability, it also means that implementation choices can influence the resulting score distribution. Control confidence is only partially calibrated at present, and some findings are necessarily shaped by heuristic thresholds rather than exhaustive empirical tuning.

#### 13.2 Construct Validity

The framework measures cloud governance posture through observable control evidence, not through direct business-impact outcomes such as financial loss, breach probability, or regulatory sanctions. As a result, the overall score should be interpreted as a structured governance-risk indicator rather than a literal prediction of incident likelihood.

#### 13.3 External Validity

The empirical evidence base remains limited. The live case-study track currently reflects one authenticated Azure subscription, and the vulnerable-lab track reflects one constrained AzureGoat deployment variant. These are useful for demonstrating feasibility and stress behavior, but they do not yet constitute a broad UK SME sample.

#### 13.4 Platform Validity

The current implementation is Azure-first. While the architecture is provider-neutral at the core, the present live evidence and comparison logic are centered on Azure APIs, Azure CLI, and Microsoft Defender for Cloud. Therefore, the current results should not be generalized directly to AWS- or GCP-based SME environments.

#### 13.5 Observability Validity

Some control families remain only partially observable in the authenticated environment. This is most relevant for Entra-wide identity controls, Conditional Access, and tenant-scoped policy visibility. CRIS-SME reduces the risk of overclaiming by surfacing observability state and provenance, but partial visibility still affects how some findings should be interpreted.

#### 13.6 Environment-Constraint Validity

The AzureGoat lab was collected from a constrained deployment variant rather than a completely stock deployment. Tenant region policy, Automation Account restrictions, Basic public-IP incompatibility, and repeated VM-capacity failures required selective adaptation. This does not invalidate the lab as an intentionally vulnerable dataset, but it does mean that some AzureGoat behaviors were not fully represented.

### 14. Future Work

The next defensible extensions are:

1. deeper tenant-level identity and budget-governance evidence
2. expanded repeated-run evaluation across longer time windows
3. mock and live AWS/GCP implementations through the existing adapter strategy
4. scoring sensitivity experiments across broader SME-style environments
5. carefully scoped AI-assisted prioritization experiments layered on top of the deterministic core

### 15. Conclusion

CRIS-SME demonstrates that an SME-oriented cloud governance framework can be technically clean, explainable, and research-ready without depending on heavyweight enterprise tooling or overstated AI claims. The framework now supports synthetic and live Azure-backed assessment, archived comparison, figure generation, appendix export, and manuscript-oriented documentation. As such, it provides a credible bridge between iterative engineering work and publishable cloud governance research.
