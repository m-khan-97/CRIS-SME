# Cyber Essentials Question Annotation Matrix

> Status: private-method working skeleton.  
> Do not paste IASME question text into this file until reuse terms are confirmed. Use stable local IDs and paraphrased scope notes.

## Purpose

This matrix is the working annotation surface for the Cyber Essentials paper. It should be completed before implementing `data/ce_question_mapping.json`.

Research question:

> Which Cyber Essentials self-assessment questions can be pre-populated from cloud control-plane telemetry, and which require endpoint, MDM, EDR, policy, or human evidence?

## Annotation Rules

- Use paraphrased descriptions, not verbatim IASME question text.
- Record a single primary evidence class, even when secondary evidence exists.
- Prefer `manual_required` when an answer depends on organisational scope, ownership, or business justification.
- Prefer `endpoint_required` when the answer depends on laptops, desktops, tablets, mobile devices, local firewall state, device unlock settings, local AV, or local patch state.
- Use `direct_cloud` only when a current or planned cloud API can support the answer without human inference.
- Use `inferred_cloud` when CRIS-SME can produce a useful signal but not a complete self-assessment answer.

Evidence classes:

- `direct_cloud`
- `inferred_cloud`
- `endpoint_required`
- `policy_required`
- `manual_required`
- `not_observable`

## Coverage Summary

Fill these counts after the question-by-question pass.

| Evidence class | Count | Notes |
| --- | ---: | --- |
| `direct_cloud` | TBD | Questions answerable from Azure control-plane evidence. |
| `inferred_cloud` | TBD | Questions with useful cloud evidence but incomplete answer support. |
| `endpoint_required` | TBD | Requires Intune, Defender for Endpoint, Jamf, MDM, EDR, or local device inventory. |
| `policy_required` | TBD | Requires policy, process, contract, approval, or business-need evidence. |
| `manual_required` | TBD | Requires human scoping or final assertion. |
| `not_observable` | TBD | Not supported by current CRIS-SME evidence paths. |

## Firewall Questions

| Local ID | Short paraphrase | Asset scope | Evidence class | Azure evidence path | Current CRIS-SME signal | Missing signal | Human review | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CE-FW-001 | Scope identifies internet boundary and firewall-controlled assets. | Boundary, cloud networks, remote users | `manual_required` | Subscription/resource inventory can assist. | Provider inventory, network inventory | Agreed CE scope boundary | Yes | Scope is not derivable from telemetry alone. |
| CE-FW-002 | Inbound internet services are restricted to required services. | IaaS, PaaS, cloud network rules | `direct_cloud` | NSG rules, public IPs, load balancers, app ingress. | `NET-001`, `NET-002` | PaaS app ingress breadth | Yes | Strong cloud-control-plane candidate. |
| CE-FW-003 | Public administrative access is blocked or strongly protected. | Admin ports, management interfaces | `direct_cloud` | NSG rules, public IPs, source allow lists, CA signal. | `NET-001`, `IAM-001` | Full management-plane access policy | Yes | Current fix makes CA unknown explicit. |
| CE-FW-004 | Firewall rules are approved and documented. | Firewall/NSG/change records | `policy_required` | Tags, policy assignments, rule descriptions can assist. | `NET-002`, governance metadata | Approval/change ticket evidence | Yes | Telemetry can identify rules, not prove approval. |
| CE-FW-005 | Unneeded firewall rules are removed promptly. | Firewall/NSG lifecycle | `inferred_cloud` | Rule age if available, unused rule analytics if available. | `NET-002` | Rule age and business justification | Yes | Needs drift/history support for stronger answer. |
| CE-FW-006 | Software firewalls protect devices on untrusted networks. | Laptops, desktops, mobile devices | `endpoint_required` | Intune/MDM/Defender for Endpoint. | None | Endpoint firewall state | Yes | Out of cloud-control-plane scope. |

## Secure Configuration Questions

| Local ID | Short paraphrase | Asset scope | Evidence class | Azure evidence path | Current CRIS-SME signal | Missing signal | Human review | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CE-SC-001 | Unsupported default or guessable credentials are removed or changed. | Cloud identities, VMs, devices | `inferred_cloud` | Entra, VM auth settings, policy recommendations. | `IAM-001`, `IAM-002`, `CMP-005` | Local/default password proof | Yes | Stronger with Entra password policy and VM login evidence. |
| CE-SC-002 | Unnecessary accounts are removed or disabled. | Cloud identities, local device accounts | `inferred_cloud` | Entra users/service principals, role assignments. | `IAM-003` | Local accounts and HR joiner/mover/leaver context | Yes | Good for cloud identities, incomplete for endpoints. |
| CE-SC-003 | Unnecessary software and services are removed or disabled. | VMs, endpoints, PaaS apps | `endpoint_required` | Defender inventory could assist for VMs. | `CMP-003` | Full installed software/service inventory | Yes | Cloud-only evidence is weak. |
| CE-SC-004 | Auto-run or automatic execution is disabled where required. | Endpoints | `endpoint_required` | Intune/Jamf/MDM configuration. | None | Device configuration policy | Yes | Not cloud-control-plane observable. |
| CE-SC-005 | Device unlock settings meet expected protections. | Endpoints and mobile devices | `endpoint_required` | Intune/Jamf/MDM compliance policy. | None | Device lock/password configuration | Yes | Requires endpoint/MDM integration. |
| CE-SC-006 | Cloud services are configured securely under shared responsibility. | SaaS, PaaS, IaaS | `inferred_cloud` | Azure Policy, Defender recommendations, secure score. | Provider contracts, policy assignments, findings | Contractual provider responsibility evidence | Yes | Useful paper discussion item. |

## Security Update Management Questions

| Local ID | Short paraphrase | Asset scope | Evidence class | Azure evidence path | Current CRIS-SME signal | Missing signal | Human review | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CE-SUM-001 | Software is licensed, supported, and receives security updates. | VMs, endpoints, applications | `inferred_cloud` | VM image metadata, Defender recommendations. | `CMP-001` | Endpoint and application inventory | Yes | Cloud workloads only without MDM/EDR. |
| CE-SUM-002 | High/critical updates are applied within required timelines. | VMs, endpoints, applications | `inferred_cloud` | Azure Update Manager, Defender assessments. | `CMP-001`, native recommendations | Patch age and endpoint patch state | Yes | Needs richer VM patch collector. |
| CE-SUM-003 | Unsupported software is removed, segregated, or isolated. | VMs, endpoints, applications | `inferred_cloud` | Defender recommendations, VM OS metadata. | `CMP-001`, `CMP-003` | Installed software inventory | Yes | Good future drift metric candidate. |
| CE-SUM-004 | Automatic update mechanisms are enabled where appropriate. | Endpoints, VMs, applications | `endpoint_required` | Intune/MDM, Azure Update Manager. | Partial compute posture | Device update policy | Yes | Split cloud workload vs endpoint answer later. |

## User Access Control Questions

| Local ID | Short paraphrase | Asset scope | Evidence class | Azure evidence path | Current CRIS-SME signal | Missing signal | Human review | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CE-UAC-001 | User accounts are assigned to authorised individuals. | Entra users, service accounts, SaaS accounts | `inferred_cloud` | Entra users, role assignments, service principals. | IAM inventory, `IAM-003` | HR/authorisation evidence | Yes | Telemetry cannot prove business authorisation. |
| CE-UAC-002 | Access is limited to what users need for their role. | RBAC, SaaS permissions | `direct_cloud` | Azure role assignments and directory roles. | `IAM-002` | Business role justification | Yes | Strong CRIS-SME fit for cloud RBAC. |
| CE-UAC-003 | Privileged access is separated and tightly managed. | Admin accounts, privileged roles | `inferred_cloud` | Role assignments, directory roles, PIM/access reviews if available. | `IAM-002`, `IAM-004`, `IAM-005` | PIM/access review telemetry | Yes | Add Graph/PIM path later. |
| CE-UAC-004 | MFA protects cloud services and privileged access. | Entra, SaaS, privileged users | `direct_cloud` if Graph permissions allow; otherwise `not_observable` | Conditional Access, credential registration details. | `IAM-001`, `IAM-005` | Tenant permissions for CA/MFA reports | Yes | Highest-value live evidence path. |
| CE-UAC-005 | Password-based authentication controls meet expected protections. | Entra, local accounts, SaaS | `inferred_cloud` | Entra authentication methods and password policy. | Partial IAM posture | Local passwords and SaaS policies | Yes | Needs Graph expansion. |
| CE-UAC-006 | Third-party or MSP accounts are in scope and controlled. | Supplier/MSP accounts | `manual_required` | Role assignments may identify external identities. | Role assignment inventory | Contract and ownership context | Yes | Human scoping is central. |

## Malware Protection Questions

| Local ID | Short paraphrase | Asset scope | Evidence class | Azure evidence path | Current CRIS-SME signal | Missing signal | Human review | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CE-MP-001 | Malware protection is active on in-scope devices. | Servers, laptops, desktops, mobile devices | `endpoint_required` | Defender for Endpoint, Intune, VM extensions. | `CMP-002` | Endpoint AV/EDR inventory | Yes | Current CRIS-SME can only infer workload coverage. |
| CE-MP-002 | Anti-malware is kept updated. | Endpoints and servers | `endpoint_required` | Defender for Endpoint health, MDM. | `CMP-002` | AV signature/version state | Yes | Needs endpoint integration. |
| CE-MP-003 | Malware execution is blocked or prevented. | Endpoints and workloads | `endpoint_required` | Defender policy, application control policy. | Partial workload hardening | Device policy state | Yes | Not answerable from subscription inventory. |
| CE-MP-004 | Application allow-listing is configured where used. | Endpoints, servers | `endpoint_required` | Intune/Jamf/Defender Application Control. | `CMP-003` | App control policy evidence | Yes | Future Intune connector candidate. |
| CE-MP-005 | Sandboxing or app-store restrictions are configured where used. | Mobile/end-user devices | `endpoint_required` | MDM platform evidence. | None | Device management evidence | Yes | Outside current CRIS-SME. |

## Cross-Cutting Scope / Asset Questions

| Local ID | Short paraphrase | Asset scope | Evidence class | Azure evidence path | Current CRIS-SME signal | Missing signal | Human review | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CE-SCOPE-001 | The organisation has defined the assessment scope. | Whole organisation or subset | `manual_required` | Subscription/resource inventory can assist. | Evaluation dataset metadata | Agreed certification scope | Yes | Required before answer generation. |
| CE-SCOPE-002 | Cloud services that host organisational data/services are included. | IaaS, PaaS, SaaS | `inferred_cloud` | Resource inventory, SaaS inventory if available. | Azure resource inventory | SaaS inventory outside Azure | Yes | CRIS-SME can help identify Azure estate. |
| CE-SCOPE-003 | BYOD and third-party device scope is understood. | BYOD, third-party devices | `manual_required` | MDM if available. | None | Device ownership and use context | Yes | Important limitation for paper. |
| CE-SCOPE-004 | Provider/shared-responsibility evidence is available where provider implements controls. | Cloud services | `policy_required` | Provider trust docs and contracts. | Provider evidence contracts | Contract clauses/provider assurance docs | Yes | Strong link to CRIS-SME assurance artifacts. |

## Next Annotation Pass

1. Download the official IASME question set through the NCSC route.
2. Align each official question to one local ID or add missing local IDs.
3. Record counts by evidence class.
4. Identify which questions can be backed by current CRIS-SME controls.
5. Identify which questions require new Azure Graph, Defender, Intune, or policy evidence.
6. Convert the final paraphrased mapping into `data/ce_question_mapping.json`.

