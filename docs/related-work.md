# Related Work

## Scope

This document positions CRIS-SME against the main categories of existing cloud posture and governance tooling that are relevant to a research paper:

- enterprise cloud security platforms
- open-source cloud auditing tools
- cloud-provider-native posture tooling
- compliance-focused governance references

The goal is not to produce an exhaustive literature review yet. The goal is to define a defensible positioning section for the first CRIS-SME paper.

## 1. Enterprise CNAPP and CSPM Platforms

The dominant commercial cloud posture market is led by cloud-native application protection platform (CNAPP) and cloud security posture management (CSPM) vendors such as Microsoft Defender for Cloud, Wiz, and Orca Security.

Microsoft Defender for Cloud positions itself as a CNAPP that combines CSPM and workload protection across multicloud and hybrid estates. Its current overview materials emphasize a unified posture view, tenant-scale scoping, recommendations, secure score, and integrated workflows across cloud and code environments.[1][2]

Wiz positions its platform as agentless, graph-based, and focused on identifying the most critical attack paths and toxic combinations of risk from code to runtime.[3] Its messaging strongly emphasizes complete coverage, security graph context, and prioritized remediation in a single console.

Orca Security similarly emphasizes agentless onboarding, full-stack visibility, context-aware prioritization, and a unified cloud data model.[4] The platform framing is centered on surfacing the small subset of issues that matter most to the business.

### Relevance to CRIS-SME

These platforms are important baselines because they define the state of practice in commercial cloud posture management:

- broad visibility
- contextual prioritization
- multicloud coverage
- integrated workflows

However, they are not optimized for the narrow operating point that CRIS-SME targets. Their product assumptions typically include larger estates, specialist security teams, and enterprise procurement models. CRIS-SME instead focuses on:

- explainable deterministic scoring
- lightweight SME-oriented outputs
- UK-specific compliance framing
- budget-aware remediation
- research-facing transparency and provenance

The contribution of CRIS-SME is therefore not breadth parity with enterprise CNAPP platforms. Its contribution is a narrower and more interpretable framework tailored to SME governance use.

## 2. Open-Source Cloud Auditing Tools

Open-source tools such as Prowler and Scout Suite provide an important alternative comparison point.

Prowler describes itself as an open cloud security platform that automates security and compliance across cloud environments, with hundreds of checks, remediation guidance, and compliance frameworks across providers including Azure.[5]

Scout Suite describes itself as an open-source multi-cloud security auditing tool that gathers cloud configuration data via provider APIs, highlights risk areas, and produces offline HTML reports for point-in-time security review.[6]

### Relevance to CRIS-SME

These tools are much closer to CRIS-SME in spirit than enterprise CNAPP platforms because they are lightweight, transparent, and oriented around assessment rather than fully managed platforms.

However, their main output model is still largely scanner-centric:

- large sets of findings
- generic compliance/control references
- less emphasis on explainable aggregate scoring
- limited SME-specific governance framing

CRIS-SME differs by combining the lightweight assessment philosophy of open-source auditing tools with:

- deterministic risk aggregation
- UK-specific regulatory mapping
- confidence calibration and native-validation reporting
- budget-aware remediation planning
- board and insurance evidence outputs

This makes CRIS-SME more than a scanner wrapper, while still keeping it far lighter than enterprise CNAPP tooling.

## 3. Provider-Native Posture Tooling

Provider-native tooling matters because it establishes the default in-product baseline many SMEs already encounter.

Microsoft Defender for Cloud provides built-in posture recommendations, security standards, and secure-score style aggregation within Azure and broader Microsoft security workflows.[1][2] This is especially relevant because CRIS-SME already uses Defender-grounded comparison as part of its confidence and validation story.

### Relevance to CRIS-SME

Provider-native tooling offers a strong operational baseline, but it is not equivalent to the CRIS-SME research contribution.

CRIS-SME adds several layers on top of provider-native recommendations:

- a provider-neutral internal model
- an explicit observability story
- deterministic risk scoring
- UK compliance overlays
- budget-aware prioritization
- paper-ready and stakeholder-ready artifacts

Accordingly, the paper should frame provider-native tooling not as a competitor to defeat, but as an external reference point for agreement and divergence analysis.

## 4. Compliance and Governance References

Most cloud posture tools emphasize global or enterprise-oriented reference frameworks such as CIS, ISO 27001, NIST, and provider security benchmarks. These are highly valuable, but they do not fully address the practical framing needs of UK SMEs.

CRIS-SME extends the reporting layer with:

- Cyber Essentials / Cyber Essentials Plus orientation
- UK GDPR references
- FCA SYSC references where relevant
- DSPT references for healthcare-adjacent contexts

### Relevance to CRIS-SME

This is one of the clearest differentiation points in the paper. The novelty is not that UK frameworks exist; the novelty is that a lightweight, explainable, cloud-posture framework explicitly maps findings into a UK SME compliance and assurance context rather than treating that context as an afterthought.

## 5. Explainability Gap

Across both enterprise and open-source tooling, a recurring tension is the gap between:

- rich technical visibility, and
- outputs that are understandable and decision-useful for smaller organizations

Enterprise platforms often solve prioritization using context graphs, attack paths, or proprietary scoring layers.[3][4] Open-source tools often solve transparency by staying closer to raw findings.[5][6]

CRIS-SME occupies a different design point:

- deterministic score construction
- explicit confidence and provenance
- actionability under budget constraints
- insurer- and board-facing output layers

This is a useful academic position because it treats explainability not as a UI convenience, but as part of the methodological design of the system.

## 6. Positioning Statement for the Paper

The strongest related-work positioning for the first CRIS-SME paper is:

1. Enterprise CNAPP platforms provide broad, context-rich posture management but are not optimized for SME-specific explainability and governance usability.
2. Open-source auditing tools provide lightweight assessment and transparency, but typically stop at finding generation and generic control mapping.
3. Provider-native cloud tooling offers an operational baseline, but not an SME-specific, UK-oriented, research-ready risk intelligence framework.
4. CRIS-SME contributes by combining:
   - lightweight assessment
   - deterministic explainable scoring
   - UK compliance framing
   - budget-aware remediation
   - provenance-aware outputs suitable for both practice and research

This is the lane in which CRIS-SME is strongest and most defensible.

## References

[1] Microsoft Learn, “Cloud overview dashboard in Microsoft Defender for Cloud,” https://learn.microsoft.com/en-us/azure/defender-for-cloud/overview-page

[2] Microsoft Learn, “What is Microsoft Defender for Cloud?,” https://learn.microsoft.com/en-us/azure/defender-for-cloud/defender-for-cloud-introduction

[3] Wiz, “Wiz cloud security platform,” https://www.wiz.io/platform/

[4] Orca Security, “Trusted Cloud Security Platform,” https://orca.security/platform/

[5] Prowler Documentation, “Introduction,” https://docs.prowler.com/introduction

[6] NCC Group GitHub, “ScoutSuite: Multi-Cloud Security Auditing Tool,” https://github.com/nccgroup/ScoutSuite
