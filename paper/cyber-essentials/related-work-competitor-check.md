# Related-Work and Competitor Check

This note supports the novelty claim for the Cyber Essentials paper. It records what was checked and how CRIS-SME should position itself.

## Defensible Claim

To our knowledge, existing tools provide readiness guidance, control-level compliance mapping, automated evidence collection, or resource-level posture checks, but do not generate a question-level Cyber Essentials answer pack from live cloud control-plane telemetry with explicit evidence-sufficiency labels, proposed `Yes`/`No`/`Cannot determine` answers, linked finding lineage, and a human-review ledger.

This claim should remain bounded to the sources checked below. It should not claim that no commercial GRC platform automates any Cyber Essentials evidence.

## Checked Tools and Sources

| Tool or source | Observed capability | CRIS-SME distinction |
| --- | --- | --- |
| Microsoft Defender for Cloud regulatory compliance | Defender represents standards as compliance controls and automatically assesses resources where possible. Microsoft documentation states that controls that cannot be automatically assessed cannot be decided by Defender. Defender lists NCSC Cyber Essentials v3.1 as a supported regulatory standard. | CRIS-SME produces a Cyber Essentials answer pack at question/preparation-entry level, separates direct/inferred/unavailable evidence, and records human review decisions. Defender is resource/control-oriented rather than CE answer-pack oriented. |
| Prowler | Prowler supports compliance-framework execution with `--compliance` and has a broad compliance hub. The checked public result for "Cyber Essentials" was CISA Cyber Essentials, not UK NCSC Cyber Essentials self-assessment pre-population. | CRIS-SME targets UK Cyber Essentials preparation entries and proposed answers, not only mapped security checks. |
| ScoutSuite | ScoutSuite is an open-source multi-cloud security-auditing tool for cloud posture assessment. | ScoutSuite reports cloud security findings; the checked public project material does not show UK Cyber Essentials question-level pre-population with evidence sufficiency and human review. |
| Vanta | Vanta markets Cyber Essentials automation with integrations, tests, evidence collection, and compliance guidance. Vanta help material describes integrations that continuously collect evidence and map it to frameworks. | Vanta is a commercial GRC/evidence platform. The public material checked does not expose a deterministic UK CE question-level cloud-telemetry mapping, evidence-class taxonomy, or reproducible answer-pack artifact comparable to CRIS-SME. Do not overclaim against undisclosed commercial features. |
| JumpCloud | JumpCloud publishes Cyber Essentials/Cyber Essentials Plus readiness material, especially around identity, device, and endpoint management. | JumpCloud is strong for identity/device management. The checked material is readiness guidance rather than cloud-control-plane CE answer-pack generation. |
| ConnectWise/MSP tooling | ConnectWise material emphasizes RMM, automation, reporting, exceptions, remediation workflows, and compliance-audit support. | MSP tooling supports operational management and reporting, but the checked public material does not show UK CE question-level answer derivation from cloud telemetry with explicit evidence insufficiency states. |
| IASME/NCSC workflow | NCSC publishes Cyber Essentials requirements. IASME operates the certification/self-assessment process. | CRIS-SME does not replace IASME/NCSC. It prepares a paraphrased, human-reviewable evidence pack and avoids reproducing official question text. |
| CE FastTrack | CE FastTrack states it produces a working document for the user to complete the official IASME portal and covers the Danzell v3.3 question set. | CE FastTrack appears closest in workflow framing. CRIS-SME's distinct contribution is deterministic linking from live cloud-control-plane evidence to answer candidates, evidence classes, findings, and review ledger artifacts. |

## Sources

- Microsoft Defender for Cloud regulatory compliance standards: https://learn.microsoft.com/en-us/azure/defender-for-cloud/concept-regulatory-compliance-standards
- Microsoft Defender for Cloud regulatory compliance FAQ: https://learn.microsoft.com/en-us/azure/defender-for-cloud/faq-regulatory-compliance
- Prowler compliance documentation: https://docs.prowler.com/projects/prowler-open-source/en/latest/tutorials/compliance
- Prowler Hub CISA Cyber Essentials entry: https://hub.prowler.com/compliance/cisa_aws
- ScoutSuite GitHub repository: https://github.com/nccgroup/ScoutSuite
- Vanta Cyber Essentials product page: https://www.vanta.com/products/cyber-essentials
- Vanta integrations help material: https://help.vanta.com/en/articles/11346110-maximizing-your-vanta-roi-with-integrations
- JumpCloud Cyber Essentials Plus readiness article: https://jumpcloud.com/blog/cybersecurity-plus-compliance-get-ready
- ConnectWise Automate product page: https://www.connectwise.com/platform/automate
- ConnectWise cyber remediation page: https://www.connectwise.com/solutions/cyber-remediation
- NCSC Cyber Essentials resources: https://www.ncsc.gov.uk/cyberessentials/resources
- NCSC Cyber Essentials requirements v3.3 PDF: https://www.ncsc.gov.uk/files/cyber-essentials-requirements-for-it-infrastructure-v3-3.pdf
- CE FastTrack: https://cefasttrack.com/

## Related-Work Framing for the Paper

Use three categories:

1. **Cloud posture and CSPM tools**: Defender for Cloud, Prowler, ScoutSuite. These assess resources and controls, sometimes with framework mappings, but do not expose the CE preparation workflow as a question-level, human-reviewed answer pack.
2. **GRC/evidence automation platforms**: Vanta and similar platforms automate evidence collection, tests, and compliance workflows. CRIS-SME differs by being deterministic, inspectable, cloud-control-plane-specific, and explicit about answerability boundaries.
3. **Cyber Essentials preparation and certification workflow**: IASME/NCSC and CE FastTrack address the assessment process directly. CRIS-SME should position itself as a pre-assessment evidence engine that feeds human completion, not as a certification portal or assessor.

## Claim Discipline

Avoid:

- "No tool automates Cyber Essentials."
- "CRIS-SME completes Cyber Essentials."
- "CRIS-SME certifies compliance."

Use:

- "No checked public tool exposes the same combination of UK CE question-level answer pre-population, live cloud-control-plane evidence lineage, explicit evidence sufficiency, and human-review ledger."
- "CRIS-SME supports assessment preparation and evidence retrieval; final answers remain human-attested."
