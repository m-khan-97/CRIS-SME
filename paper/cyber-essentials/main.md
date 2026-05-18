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
| CMP-003 | 1 | 38.49 |
| GOV-003 | 1 | 33.88 |

### 8.4 Review Metrics

The AI-assisted pilot review ledger reviewed the 28 cloud-supported entries. It accepted 23 conservative answer-impact decisions, marked 5 as `needs_evidence`, and left 78 non-cloud entries pending. AI-assisted draft acceptance is reported separately from human agreement throughout and is not counted in `agreement_count` or `agreement_rate`.

The 28 cloud-supported entries were subsequently reviewed by the first author, who also developed the system and has read the NCSC Cyber Essentials Requirements for IT Infrastructure v3.3 document in full. This constitutes author self-assessment, not independent review by a certified CE assessor or a reviewer without prior knowledge of the system. Findings should be interpreted as internal consistency validation rather than external validity evidence. Independent assessor review by a CE-knowledgeable third party is a planned future evaluation step and is identified as a threat to validity in Section 10.

Validation against the current controlled-lab answer pack found that 8 rows required revalidation because their recorded evidence class, proposed status, or proposed answer no longer matched the current generated evidence. A reviewer-facing evidence pack was prepared for those 8 rows, including linked controls, finding IDs, finding titles, scores, and evidence statements. A final cross-check workbook marked all 8 stale rows as `accepted` with final answer `No`, matching the current CRIS-SME proposed answers.

The merged final ledger contains 23 accepted rows and 5 `needs_evidence` rows. All 23 accepted rows match the current CRIS-SME proposed answer, yielding 23 of 23 agreement over agreement-evaluable rows. The 5 `needs_evidence` rows are excluded from the agreement denominator. This result is not a Cyber Essentials certification claim; it is internal consistency validation between the author's interpretation of the CE requirements and CRIS-SME's automated answer derivation, as discussed in Section 10.

The 23/23 agreement figure is a structural property of the evaluation design as well as an empirical result. All 23 agreement-evaluable rows had proposed answer `No`, derived from direct or inferred cloud evidence with a linked CRIS-SME finding; the reviewer confirmed each `No` as conservative and evidence-grounded. The 5 `needs_evidence` rows had proposed answer `Yes`, where no mapped cloud-control-plane finding was present; the reviewer correctly flagged these as insufficiently supported by cloud evidence alone and excluded them from the agreement denominator. The design separates these two populations by construction: `No` answers backed by findings form the evaluable set, and `Yes` answers without corroborating findings are explicitly flagged for additional evidence. A reviewer who disagreed with a proposed `No` could have overridden it; zero overrides were recorded.

## 9. Discussion

The main result is not that Cyber Essentials can be automated from cloud telemetry. It cannot. The main result is that a meaningful minority of entries — 28 of 106, and 22 of 62 technical-control entries — can be pre-populated or evidence-supported from cloud control-plane telemetry, and that the remaining majority can be routed to explicit, typed evidence gaps rather than left as undifferentiated manual work. The six-class taxonomy makes this boundary machine-readable and human-auditable.

This matters for SMEs because evidence retrieval is the practical obstacle to CE self-assessment, not the questions themselves. A system that says "you need MDM evidence for this entry, NSG evidence for that one, and a policy document for the third" reduces the scope of manual work without hiding the remaining scope. It matters academically because it provides a more precise vocabulary for discussing compliance automation: not as binary automation or as compliance generation, but as evidence sufficiency, observability boundaries, and human-verification scope.

The controlled lab shows that CRIS-SME can translate real Azure misconfiguration evidence into both deterministic risk findings and Cyber Essentials answer impact. The same NSG exposure that drives a NET-001 finding with score 72.12 also drives proposed `No` answers across 5 Cyber Essentials preparation entries covering firewall configuration, inbound access control, and remote administration protection. This linkage between risk score and CE answer impact is a novel property of the deterministic approach: the two outputs are traceable to the same evidence without requiring a separate CE-specific scan.

The review ledger design is as important as the answer derivation. Proposed `Yes` answers are structurally weaker than proposed `No` answers. A detected misconfiguration can safely drive a `No` because the evidence is affirmative. The absence of a detected misconfiguration cannot safely drive an unqualified `Yes` because the collector operates at the cloud control-plane only; endpoint state, SaaS configuration, business process, and inheritance paths are outside the observable scope. The five `needs_evidence` rows in the final ledger correctly identify entries where this boundary applies.

## 10. Threats to Validity

**Reviewer identity.** The 28 cloud-supported entries were reviewed by the first author, who is also the system developer and the primary author of the CE question mapping. This constitutes author self-assessment, not independent review. The agreement rate of 23/23 should be interpreted as internal consistency validation: it shows that the system's proposed answers are coherent with the author's interpretation of the CE requirements, not that they would be accepted by an independent certified assessor. A systematic replication by a CE-knowledgeable third party with no prior exposure to CRIS-SME is identified as a priority future evaluation step.

**Construct validity of proposed answers.** Proposed `Yes` answers carry false-negative risk. A `Yes` means no mapped CRIS-SME cloud-control-plane finding was present for the linked controls in the assessed subscription. It does not prove that all firewall inheritance paths, application-layer controls, endpoint configurations, SaaS settings, BYOD devices, or out-of-scope assets satisfy the Cyber Essentials requirement. The review interface and caveat text make this explicit for each entry, but the risk cannot be eliminated from the underlying construct.

**Paraphrased question mapping.** The mapping uses paraphrased preparation entries rather than official IASME question text, to avoid reproducing proprietary wording. This introduces a risk that the paraphrase misrepresents the scope or intent of an official question. The mapping was derived from the IASME preparation question preview page and the NCSC Requirements for IT Infrastructure v3.3 document. Any divergence between the paraphrase and the official question would affect the evidence-class classification and, consequently, the proposed answer derivation.

**Controlled lab scope.** The controlled lab is intentionally minimal: one NSG with public rules and one empty storage account. It validates the cloud-control-plane evidence path without exposing a reachable VM workload, but it is not a complete SME production environment. A real SME tenant would include more storage accounts, SQL servers, VMs, SaaS integrations, and user accounts, which would surface additional findings and affect proposed answers across more CE entries. Generalizability from the controlled lab to real SME postures is limited.

**Azure-only implementation.** CRIS-SME is Azure-first. The evidence taxonomy and answer derivation are designed to be provider-neutral, but the current mapping explicitly notes `endpoint_required` for entries where Intune, Defender for Endpoint, or MDM evidence would be needed. A hybrid organisation using AWS or GCP for some services would see more `Cannot determine` entries than a pure Azure environment. Multi-provider coverage is an open implementation gap.

**AI-assisted draft review.** The AI-assisted pilot review ledger is reported separately from human agreement and is not counted in `agreement_count` or `agreement_rate`. However, the 23 entries accepted by the AI draft and subsequently confirmed by the author create a partial circularity: the author designed the AI draft policy (accept direct cloud, accept conservative inferred No, flag inferred Yes), then validated it. Independent validation of the draft policy itself is a separate evaluation need.

## 11. Limitations

CRIS-SME pre-populates cloud-observable Cyber Essentials evidence. It does not:

**Assess endpoint posture.** The 24 entries classified as `endpoint_required` cover anti-malware configuration, local firewall state, device patching, screen-lock policy, and application auto-run settings. These require Intune, Jamf, Defender for Endpoint, or equivalent MDM/EDR integration. The current implementation cannot produce a proposed answer for these entries because it does not have access to endpoint management APIs. Any claim that CRIS-SME addresses endpoint-related CE requirements would be false.

**Assess organisational or policy evidence.** The 19 entries classified as `policy_required` and 35 entries classified as `manual_required` depend on process documentation, business justification, scoping decisions, approval records, or applicant attestation. Cloud telemetry cannot substitute for these. CRIS-SME routes these entries explicitly to the human review queue rather than suppressing them.

**Assess multi-cloud or hybrid environments.** AWS, GCP, Intune, and hybrid on-premises infrastructure are outside the current collector scope. An organisation that splits workloads across providers would have lower cloud-support rates than the Azure-only evaluation suggests.

**Certify or assess compliance.** CRIS-SME is not a CE certification body, assessor, or IASME-accredited tool. It produces a pre-assessment evidence preparation artifact. The official CE self-assessment must be completed through the IASME portal by a responsible person. Proposed answers are candidate review states, not submitted answers, and the system makes this explicit at every output layer.

**Assess at tenant scope.** The Azure collector operates at subscription scope. Conditional Access policies, Privileged Identity Management configurations, and tenant-wide Entra Identity Governance signals require elevated Microsoft Graph permissions that may not be available in all assessment contexts. Where these signals are unavailable, the IAM-005 finding surfaces the observability boundary and the relevant CE entries are classified as `inferred_cloud` or `Cannot determine`.

## 12. Future Work

**Multi-provider coverage.** The six-class evidence taxonomy and CloudProfile schema are designed to be provider-neutral. AWS Security Hub, GuardDuty, IAM Access Analyzer, and Config Rules would provide analogous evidence to the Azure collector signals. An AWSCollector following the same interface as AzureCollector would enable multi-cloud CE pre-population and cross-provider comparisons.

**Endpoint integration.** Integrating Microsoft Intune, Defender for Endpoint, or Jamf would substantially increase cloud-support coverage. The 24 `endpoint_required` entries cover fundamental CE controls including anti-malware, patch management, and screen-lock policy. Even partial MDM coverage would reduce the manual evidence burden for SMEs with managed device fleets.

**Full tenant Entra assessment.** Adding Microsoft Graph `Policy.Read.All` and `UserAuthenticationMethod.Read.All` permissions to the collector would enable direct Conditional Access policy enumeration and per-user MFA registration assessment. This would convert several `inferred_cloud` IAM entries to `direct_cloud` and improve the accuracy of proposed answers for user access control questions.

**Independent expert review.** The highest-priority evaluation gap is independent review of the 28 cloud-supported entries by a CE-knowledgeable assessor or auditor who has not seen the CRIS-SME system. This would produce a genuine inter-rater agreement metric and identify entries where the paraphrased mapping or proposed answer derivation diverges from assessor interpretation.

**Real SME deployment study.** A controlled study with three or more real UK SME tenants would provide empirical coverage rates, validate the evidence taxonomy against production environments, and measure evidence retrieval time reduction. A consent model similar to the controlled lab's authorization confirmation mechanism could enable this while preserving tenant confidentiality.

**NCSC CAF outcome mapping.** The NCSC Cyber Assessment Framework for Critical National Infrastructure organisations uses a different outcome structure from Cyber Essentials. Extending CRIS-SME's evidence mapping to CAF outcomes would address CNI-sector cloud security assessment and open a path toward regulatory evidence preparation for organisations assessed against CAF.

**Longitudinal assessment and drift detection.** CRIS-SME now includes a longitudinal drift analysis engine that computes risk velocity and control stability index across historical assessment runs. Applying this to CE answer stability — tracking which entries change class or proposed answer across repeated assessments of the same tenant — would provide a dynamic view of CE posture trajectory.

## 13. Related Work

CRIS-SME sits between three bodies of work: cloud security posture management, GRC/evidence automation, and Cyber Essentials assessment preparation.

Cloud posture tools such as Microsoft Defender for Cloud, Prowler, and ScoutSuite assess cloud resources and expose security findings or compliance mappings. Defender for Cloud represents standards as compliance controls and automatically assesses resources where possible; Microsoft documentation also notes that controls that cannot be automatically assessed cannot be decided automatically, and that Defender's CE mapping operates at the control level rather than at the self-assessment preparation-entry level. Prowler supports compliance-framework execution and maps security checks to frameworks, though its checked Cyber Essentials mapping targets CISA Cyber Essentials rather than the UK NCSC Cyber Essentials self-assessment. ScoutSuite provides multi-cloud security auditing without a CE-specific preparation workflow. These tools are valuable posture assessors, but the checked public material does not expose a UK Cyber Essentials question-level answer pack with `Yes`/`No`/`Cannot determine` candidates, evidence sufficiency classes, linked finding lineage, and a human-review ledger.

GRC and evidence-automation platforms such as Vanta automate evidence collection, integrations, tests, and compliance workflow management. MSP tooling such as ConnectWise supports monitoring, automation, reporting, remediation workflow, and audit support. Identity-and-device platforms such as JumpCloud publish CE readiness material with strong coverage of endpoint and identity management. These platforms address operational compliance management more broadly than CRIS-SME. The distinction is not that they lack automation; it is that CRIS-SME exposes a deterministic, reproducible, and openly inspectable cloud-control-plane method for classifying which UK Cyber Essentials entries can be supported by cloud evidence, which require non-cloud evidence, and which cannot be determined — and it records that boundary in a machine-readable artifact rather than a dashboard summary.

Cyber Essentials-specific preparation tools include CE FastTrack, which describes itself as producing a working document for the user to complete the official IASME portal and covers the Danzell v3.3 question set. CE FastTrack is the closest tool in workflow framing: it assists with CE preparation rather than posture assessment. CRIS-SME's distinct contribution relative to CE FastTrack is that it derives candidate answers from live cloud control-plane API evidence, attaches deterministic CRIS-SME finding lineage (control ID, score, evidence text) to each proposed answer, and explicitly classifies entries that require evidence the cloud API cannot provide. A user completing CE FastTrack must gather cloud evidence manually; CRIS-SME automates the cloud-evidence retrieval step and structures the remaining manual work.

The resulting claim is deliberately bounded: to our knowledge, the checked public tools do not provide the same combination of UK Cyber Essentials question-level answer pre-population from live cloud control-plane telemetry, explicit six-class evidence taxonomy, linked deterministic finding lineage, and a review-ledger that formally separates deterministic evidence from human attestation.

## 14. Conclusion

CRIS-SME demonstrates that cloud control-plane telemetry can support a bounded, evidence-sufficiency-aware Cyber Essentials pre-population workflow. The contribution is deliberately partial: of 106 preparation entries, 28 are cloud-supported and 78 require endpoint, policy, organisational, or manual evidence that cloud APIs cannot provide. Making this boundary explicit and machine-readable is the central result.

The controlled Azure vulnerable lab validates the evidence pathway. Intentionally weak cloud-control-plane signals — public RDP/SSH exposure and public storage access — were detected by the CRIS-SME collector, converted into deterministic risk findings, and reflected in proposed `No` answers across 23 Cyber Essentials preparation entries. The same evidence drives both the risk score and the CE answer impact, demonstrating that the two outputs are traceable to a single evidence source rather than produced by independent mechanisms.

The human cross-check result — 23 of 23 accepted reviewer decisions matching CRIS-SME's proposed answers, with 5 rows classified as needing additional evidence — should be interpreted as internal consistency validation. The reviewer is also the system developer, and the result does not constitute independent assessor validation. Independent expert review is the priority next evaluation step.

The six-class evidence taxonomy (direct cloud, inferred cloud, endpoint required, policy required, manual required, not observable), the human-review ledger design, the AI-assisted draft review policy, and the reproducible evaluation pipeline are contributions that generalise beyond the current Azure implementation. The taxonomy provides a vocabulary for describing evidence sufficiency in compliance automation that is applicable to other frameworks and other providers. The ledger design ensures that reviewer decisions are downstream of and never mutate the deterministic evidence record. Together, these constitute a principled approach to what compliance pre-population should be: honest about what it cannot see, explicit about what it can, and auditable end to end.
