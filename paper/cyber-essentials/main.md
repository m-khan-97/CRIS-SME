# Evidence-Sufficiency-Aware Cyber Essentials Pre-Population From Cloud Control-Plane Telemetry

## Abstract

Cyber Essentials is a widely used UK baseline cyber security scheme, but small and medium enterprises often complete its self-assessment manually despite already operating cloud environments that contain relevant control evidence. Existing cloud security and GRC tools report technical misconfigurations, collect audit evidence, or expose framework-level compliance mappings, but they do not generally expose which Cyber Essentials entries are answerable from cloud control-plane telemetry and which require non-cloud evidence. This paper presents CRIS-SME, a deterministic cloud risk decision engine extended with a Cyber Essentials pre-assessment workflow. CRIS-SME maps paraphrased Cyber Essentials preparation entries to cloud control-plane evidence, classifies each entry as direct cloud, inferred cloud, endpoint required, policy required, manual required, or not observable, and emits a human-reviewable answer pack with proposed answers of `Yes`, `No`, or `Cannot determine`.

In the current Azure-first implementation, CRIS-SME maps 106 Cyber Essentials preparation entries, including 62 technical-control entries. From cloud control-plane evidence alone, 28 entries are cloud-supported overall and 22 technical entries are cloud-supported. A controlled Azure vulnerable-lab run produced 23 proposed `No` answers, 5 proposed `Yes` answers, and 78 `Cannot determine` answers, demonstrating that cloud telemetry can materially reduce Cyber Essentials evidence retrieval work while preserving human accountability. A final human cross-check accepted 23 agreement-evaluable proposed answers, with 23 of 23 matching CRIS-SME's proposed answers; 5 rows were marked `needs_evidence` and excluded from the agreement denominator. The system explicitly avoids certification automation: proposed answers remain reviewable, AI-assisted draft review is reported separately from human agreement, and non-cloud evidence gaps are preserved rather than silently inferred.

## 1. Introduction

Small and medium enterprises increasingly rely on cloud infrastructure, but many lack the security staff, time, and tooling required to translate cloud posture into governance decisions. The Cyber Essentials scheme gives UK organisations a practical baseline, yet the self-assessment process still depends on manual interpretation of infrastructure, identity, endpoint, and policy evidence. For cloud-first SMEs, this creates a gap: useful evidence exists in the control plane, but it is not organized in a form that maps directly to the questions applicants need to answer.

CRIS-SME addresses this gap by treating Cyber Essentials preparation as an evidence-sufficiency problem rather than a certification automation problem. The system does not claim to certify an organisation, replace IASME or NCSC guidance, or remove the need for human attestation. Instead, it asks a narrower research question: which Cyber Essentials preparation entries can be supported from cloud control-plane telemetry, which cannot, and how should those boundaries be represented so that a reviewer can make a safer decision?

The answer is useful precisely because it is partial. In the current mapping, 28 of 106 entries are cloud-supported, including 22 of 62 technical-control entries. The remaining entries require endpoint, policy, manual, or external evidence. This is not a weakness of the method; it is the method's central claim. A transparent system that says "cannot determine" for out-of-scope evidence is more defensible than a scanner that maps cloud findings to a compliance label without explaining what it cannot see.

## 2. Contributions

This paper makes six contributions:

1. A question-level Cyber Essentials mapping model that avoids reproducing proprietary IASME wording by storing paraphrased descriptions and stable local question identifiers.
2. A deterministic answer-pack generator that links Cyber Essentials entries to CRIS-SME controls, findings, evidence snippets, and caveats.
3. A six-class evidence taxonomy for Cyber Essentials pre-population: direct cloud, inferred cloud, endpoint required, policy required, manual required, and not observable.
4. A human-review ledger that records accepted answers, overrides, evidence requests, reviewer notes, and final reviewed status without altering deterministic CRIS-SME scores.
5. A reproducible evaluation pipeline that exports observability metrics, proposed answers, review outcomes, control-contribution tables, and chart-ready data for paper use.
6. An empirical Azure controlled-lab evaluation showing 26.42% overall cloud support, 35.48% technical-entry cloud support, and 23 of 23 accepted human-review agreements over agreement-evaluable rows.

## 3. Background and Problem

Cyber Essentials is structured around baseline security controls such as firewalls, secure configuration, user access control, malware protection, and security update management. In practice, assessment preparation spans more than purely technical cloud settings. Some evidence is visible in cloud APIs, such as network security rules or privileged role assignments. Other evidence is endpoint-specific, such as anti-malware status on laptops. Some evidence is organisational, such as scoping decisions, business justification, or policy records.

This mixed evidence model makes the self-assessment difficult to automate safely. A cloud API can reveal whether an Azure Network Security Group allows inbound RDP from the internet, but it cannot prove that every endpoint firewall, SaaS configuration, inherited rule path, or business process satisfies a Cyber Essentials requirement. CRIS-SME therefore frames pre-population as candidate answer support, not final compliance determination.

## 4. System Design

CRIS-SME begins with cloud evidence collection. The current implementation has an Azure-first collector and a mock collector for repeatable testing. Evidence is normalized into provider-neutral posture profiles and evaluated across deterministic control domains: identity and access management, network exposure, data protection, monitoring and logging, compute/workload hardening, and governance hygiene.

The Cyber Essentials workflow is downstream of the deterministic risk engine:

1. `data/ce_question_mapping.json` stores paraphrased Cyber Essentials preparation entries, evidence classes, supporting control IDs, and planned evidence paths.
2. `build_ce_self_assessment_pack()` links mapped entries to CRIS-SME findings and evidence.
3. `proposed_answer` is derived as `Yes`, `No`, or `Cannot determine`.
4. `build_ce_review_console()` creates a human-verification ledger.
5. `build_ce_evaluation_metrics()` calculates observability, proposed-answer, review, and control-contribution metrics.
6. `write_ce_paper_exports()` emits Markdown, CSV, and chart-ready JSON artifacts.

Reviewer decisions are deliberately downstream. They may change the Cyber Essentials review ledger, but they never alter CRIS-SME findings, risk scores, or control outcomes.

## 5. Evidence Taxonomy

Each mapped entry is assigned one evidence class.

**Direct cloud** means a cloud control-plane API can directly support a candidate answer. For example, Azure NSG rules can reveal public inbound administrative exposure.

**Inferred cloud** means cloud posture can partially support a candidate answer, but final interpretation still requires a reviewer. For example, cloud role assignments can support least-privilege review, but they cannot prove business authorisation for every user.

**Endpoint required** means the entry requires evidence from endpoint, MDM, EDR, local firewall, anti-malware, or patch systems.

**Policy required** means the entry requires documented process, approval, contractual, or business-context evidence.

**Manual required** means the entry depends on applicant context, scoping judgement, organisation metadata, or final attestation.

**Not observable** means the required signal is outside current CRIS-SME evidence paths.

The `Yes` answer has an explicit false-negative boundary. It means no mapped CRIS-SME cloud-control-plane finding was observed for the relevant controls. It does not prove that all firewall inheritance paths, application-layer controls, endpoint controls, business processes, SaaS settings, or out-of-scope assets satisfy the Cyber Essentials requirement.

## 6. Proposed Answer Derivation

For direct and inferred cloud entries, CRIS-SME derives candidate answers from mapped controls and linked findings:

- mapped risk finding present: proposed answer `No`
- mapped controls present with no linked risk finding: proposed answer `Yes`
- insufficient evidence or non-cloud class: proposed answer `Cannot determine`

This approach is intentionally conservative for failure evidence. A detected mapped risk can safely drive a proposed `No`, because it indicates that a human reviewer should not treat the entry as satisfied without further evidence. Proposed `Yes` answers are weaker and require explicit caveats.

AI-assisted draft review follows the same conservative stance:

- direct cloud answers are accepted as pilot decisions
- inferred cloud `No` answers with linked findings are accepted as conservative answer-impact decisions
- inferred cloud `Yes` answers are marked `needs_evidence`
- non-cloud entries remain pending

The metrics distinguish AI-assisted draft acceptance from human agreement. `agreement_count` and `agreement_rate` are reserved for non-AI human reviewer decisions.

## 7. Evaluation Design

The current evaluation has three evidence modes:

1. A synthetic CRIS-SME baseline using mock SME profiles for repeatability.
2. A live Azure CE evidence run using an authenticated Azure subscription.
3. A controlled Azure vulnerable lab using intentionally weak cloud-control-plane signals.

The controlled lab was created in an authorised Azure for Students subscription. It used an NSG with public SSH and RDP rules, plus an empty storage account with public network/blob access enabled. No VM was attached to the public administrative rules. The lab was deleted after assessment.

The evaluation reports:

- mapped entry count
- technical entry count
- evidence-class distribution
- cloud-supported rate
- proposed answer distribution
- review ledger states
- human agreement and AI draft acceptance separately
- controls contributing to proposed `No` answers

## 8. Results

### 8.1 Coverage

CRIS-SME maps 106 Cyber Essentials preparation entries. Of these, 62 are technical-control entries. The evidence-class distribution is:

| Evidence class | Count | Rate |
| --- | ---: | ---: |
| direct cloud | 5 | 4.72% |
| inferred cloud | 23 | 21.70% |
| endpoint required | 24 | 22.64% |
| policy required | 19 | 17.92% |
| manual required | 35 | 33.02% |

Cloud-supported entries account for 28 of 106 entries, or 26.42%. Among technical-control entries, 22 of 62 are cloud-supported, or 35.48%.

### 8.2 Controlled Azure Vulnerable Lab

The controlled lab produced an overall CRIS-SME risk score of 40.16/100 across 18 non-compliant findings. Category scores were:

| Category | Score |
| --- | ---: |
| IAM | 32.51 |
| Network | 58.42 |
| Data | 41.74 |
| Monitoring/Logging | 36.38 |
| Compute/Workloads | 38.29 |
| Cost/Governance Hygiene | 27.11 |

The top lab-sensitive findings were:

| Control | Finding | Score |
| --- | --- | ---: |
| NET-001 | Administrative services are exposed to the public internet | 72.12 |
| IAM-001 | Privileged role assignments without MFA enforcement | 67.97 |
| DATA-001 | Public storage access increases data exposure risk | 48.35 |
| NET-002 | Network security group rules are broader than expected | 44.71 |

### 8.3 Cyber Essentials Answer Impact

The controlled lab produced:

| Proposed answer | Count |
| --- | ---: |
| No | 23 |
| Yes | 5 |
| Cannot determine | 78 |

The top controls contributing to proposed `No` answers were:

| Control | Affected entries | Max linked score |
| --- | ---: | ---: |
| IAM-001 | 9 | 67.97 |
| NET-002 | 6 | 44.71 |
| NET-001 | 5 | 72.12 |
| IAM-002 | 5 | 24.98 |
| IAM-005 | 3 | 4.57 |
| DATA-001 | 2 | 48.35 |

### 8.4 Review Metrics

The AI-assisted pilot review ledger reviewed the 28 cloud-supported entries. It accepted 23 conservative answer-impact decisions, marked 5 as `needs_evidence`, and left 78 non-cloud entries pending.

This is not independent human agreement. A CE-knowledgeable reviewer ledger was received for the 28 cloud-supported entries. Validation against the current controlled-lab answer pack found that 8 rows required revalidation because their recorded evidence class, proposed status, or proposed answer no longer matched the current generated evidence. A reviewer-facing evidence pack was prepared for those 8 rows, including linked controls, finding IDs, finding titles, scores, and evidence statements.

A final human cross-check workbook has since marked all 8 stale rows as `accepted` with final answer `No`, matching the current CRIS-SME proposed answers. The merged final ledger contains 23 accepted rows and 5 `needs_evidence` rows. All 23 accepted rows match the current CRIS-SME proposed answer, yielding 23 of 23 agreement over agreement-evaluable rows. The 5 `needs_evidence` rows are excluded from the agreement denominator.

## 9. Discussion

The main result is not that Cyber Essentials can be automated from cloud telemetry. It cannot. The main result is that a meaningful minority of entries can be pre-populated or evidence-supported from cloud control-plane telemetry, and that the remaining majority can be routed to explicit evidence gaps.

This matters for SMEs because it can reduce evidence retrieval work without hiding uncertainty. It also matters academically because it provides a more precise way to discuss compliance automation: not as binary automation, but as evidence sufficiency, observability, and human-verification boundaries.

The controlled lab shows that CRIS-SME can convert real Azure misconfiguration evidence into both deterministic risk findings and Cyber Essentials answer impact. The lab also shows why the review ledger is necessary. Public RDP/SSH and public storage can support proposed `No` answers, but proposed `Yes` answers remain weaker and require human confirmation.

## 10. Threats to Validity

The Cyber Essentials mapping uses paraphrased preparation entries rather than official question text. This protects licensing boundaries but requires careful documentation and may need review against IASME terms before publication.

The implementation is Azure-first. AWS, GCP, Intune, Defender for Endpoint, and MDM integrations would increase observability, especially for endpoint and device questions.

The controlled lab is small by design. It validates cloud-control-plane evidence paths without exposing a reachable VM workload, but it is not a complete SME production environment or a full AzureGoat deployment.

AI-assisted draft review is not independent human review. Human agreement claims require a CE-knowledgeable reviewer to validate or override the 28 cloud-supported entries. The current merged ledger includes the final human cross-check for the controlled-lab answer pack, but the agreement claim remains bounded to the reviewed cloud-evidence rows and is not a Cyber Essentials certification claim.

Proposed `Yes` answers carry false-negative risk outside mapped cloud-control-plane evidence.

## 11. Related Work

CRIS-SME sits between three bodies of work: cloud security posture management, GRC/evidence automation, and Cyber Essentials assessment preparation.

Cloud posture tools such as Microsoft Defender for Cloud, Prowler, and ScoutSuite assess cloud resources and expose security findings or compliance mappings. Defender for Cloud represents standards as compliance controls and automatically assesses resources where possible; Microsoft documentation also notes that controls that cannot be automatically assessed cannot be decided automatically. Prowler supports compliance-framework execution and maps security checks to frameworks, while ScoutSuite provides multi-cloud security auditing. These tools are valuable posture assessors, but the checked public material does not expose a UK Cyber Essentials question-level answer pack with `Yes`/`No`/`Cannot determine` candidates, evidence sufficiency classes, linked finding lineage, and a human-review ledger.

GRC and evidence-automation platforms such as Vanta automate evidence collection, integrations, tests, and compliance workflow management. MSP tooling such as ConnectWise supports monitoring, automation, reporting, remediation workflow, and audit support. These platforms address operational compliance management more broadly than CRIS-SME. The distinction is not that they lack automation; rather, CRIS-SME exposes a deterministic and reproducible cloud-control-plane method for deciding which UK Cyber Essentials entries can be supported by cloud evidence and which must remain outside the automated answer boundary.

Cyber Essentials-specific workflows include IASME/NCSC assessment guidance and preparation tools such as CE FastTrack. These are closer to the assessment process itself. CRIS-SME does not replace the official assessment portal or reproduce official question wording. Instead, it uses paraphrased local entries and treats the task as evidence preparation: each generated answer remains bounded by its evidence class and human review state.

The resulting claim is deliberately narrow: to our knowledge, the checked public tools do not provide the same combination of UK Cyber Essentials question-level answer pre-population, live cloud-control-plane evidence lineage, explicit evidence-sufficiency labels, and review-ledger separation between deterministic evidence and human attestation.

## 12. Conclusion

CRIS-SME demonstrates that cloud control-plane telemetry can support a bounded, evidence-sufficiency-aware Cyber Essentials pre-population workflow. The current Azure-first implementation maps 106 preparation entries, identifies that 28 are cloud-supported, and produces reviewable proposed answers with explicit evidence gaps. The controlled Azure vulnerable lab shows that intentionally weak cloud-control-plane signals can be reflected in both deterministic risk findings and Cyber Essentials answer impact. The final human cross-check provides an empirical review result for the agreement-evaluable rows: 23 of 23 accepted reviewer decisions matched CRIS-SME's proposed answers, while 5 rows remained classified as needing additional evidence.
