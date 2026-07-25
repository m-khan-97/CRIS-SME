# CRIS-SME Cyber Insurance Evidence Pack

- Generated at: `2026-07-04T18:15:03.071496Z`
- Jurisdiction: `United Kingdom`
- Collector mode: `aws`
- Organizations: SIGI Technologies
- Overall risk score: `38.79`
- Readiness score: `25.00`

## Readiness Summary

- Questions assessed: `6`
- Met: `0`
- Partial: `3`
- Not met: `3`
- Unknown: `0`

## Question-Level Evidence

### INS-001 - Access security

- Question: Do you enforce multi-factor authentication for privileged and administrative accounts?
- Status: `not_met`
- Evidence statement: CRIS-SME identified material evidence that this control area is not fully met. The strongest linked gap is IAM-001 at 67.97 risk (high priority).
- Insurer relevance: UK cyber insurers routinely ask whether administrator access is protected by MFA because privileged credential compromise drives high-impact claims.
- Recommended next step: Require MFA and admin-focused conditional access for privileged identities.
- Related controls: IAM-001

| Control | Priority | Score | Evidence |
| --- | --- | ---: | --- |
| IAM-001 | High | 67.97 | 1 privileged account(s) do not have MFA enabled; Conditional access for privileged administrators was not observable and is treated as unmet for deterministic scoring |

### INS-002 - Least privilege

- Question: Do you limit privileged access and review high-risk permissions regularly?
- Status: `partial`
- Evidence statement: CRIS-SME identified partial evidence of control weakness or incomplete observability. The strongest linked gap is IAM-005 at 4.57 risk (monitor priority).
- Insurer relevance: Insurers assess whether privileged access is narrowly scoped and reviewed because excessive privilege expands ransomware and fraud blast radius.
- Recommended next step: Broaden tenant-level identity evidence collection before treating IAM coverage as complete.
- Related controls: IAM-002, IAM-004, IAM-005

| Control | Priority | Score | Evidence |
| --- | --- | ---: | --- |
| IAM-005 | Monitor | 4.57 | Subscription-scoped evidence was collected for privileged role assignments; Tenant-wide Entra controls such as conditional access were not directly observable in this run |

### INS-003 - Perimeter exposure

- Question: Are administrative services and internet-facing rules restricted to least-privilege network access?
- Status: `not_met`
- Evidence statement: CRIS-SME identified material evidence that this control area is not fully met. The strongest linked gap is NET-001 at 72.12 risk (high priority).
- Insurer relevance: Publicly reachable administrative services and permissive firewall rules are common signals in cyber insurance questionnaires and underwriting reviews.
- Recommended next step: Restrict SSH and RDP exposure with private access paths, VPN, or just-in-time controls.
- Related controls: NET-001, NET-002

| Control | Priority | Score | Evidence |
| --- | --- | ---: | --- |
| NET-001 | High | 72.12 | 1 asset(s) expose RDP to the public internet; 1 asset(s) expose SSH to the public internet |
| NET-002 | Planned | 44.71 | 2 permissive NSG rule(s) were identified |

### INS-004 - Patch and malware protection

- Question: Are critical workloads patched promptly and protected with endpoint or anti-malware controls?
- Status: `partial`
- Evidence statement: CRIS-SME identified partial evidence of control weakness or incomplete observability. The strongest linked gap is CMP-001 at 42.69 risk (planned priority).
- Insurer relevance: Patch latency and missing endpoint protection are frequent prerequisites for claims involving ransomware and exploitation of known vulnerabilities.
- Recommended next step: Patch critical workloads and enforce a stronger recurring patch policy.
- Related controls: CMP-001, CMP-002, CMP-003, CMP-005

| Control | Priority | Score | Evidence |
| --- | --- | ---: | --- |
| CMP-001 | Planned | 42.69 | 1 critical VM(s) require urgent patching |
| CMP-002 | Planned | 39.53 | Endpoint protection coverage is approximately 0% |
| CMP-003 | Planned | 38.49 | Hardened baseline coverage is approximately 0% |

### INS-005 - Backup and recovery

- Question: Do you maintain resilient backups for critical workloads and business data?
- Status: `not_met`
- Evidence statement: CRIS-SME identified material evidence that this control area is not fully met. The strongest linked gap is DATA-003 at 37.58 risk (planned priority).
- Insurer relevance: Backup recoverability is a core underwriting concern because it directly affects business interruption exposure and ransom resilience.
- Recommended next step: Increase backup and retention coverage for business-critical data stores.
- Related controls: DATA-003, CMP-004

| Control | Priority | Score | Evidence |
| --- | --- | ---: | --- |
| DATA-003 | Planned | 37.58 | Backup coverage is only 60%; Retention policy coverage is only 60% |
| CMP-004 | Planned | 36.85 | Workload backup agent coverage is approximately 0% |

### INS-006 - Monitoring and response

- Question: Do you retain logs, generate security alerts, and maintain incident response procedures?
- Status: `partial`
- Evidence statement: CRIS-SME identified partial evidence of control weakness or incomplete observability. The strongest linked gap is MON-001 at 35.79 risk (planned priority).
- Insurer relevance: Cyber insurance applications often ask for logging, alerting, and response evidence to gauge the organisation's ability to detect and contain incidents.
- Recommended next step: Increase log retention to support investigation, governance review, and evidence preservation.
- Related controls: MON-001, MON-002, MON-003, MON-004

| Control | Priority | Score | Evidence |
| --- | --- | ---: | --- |
| MON-001 | Planned | 35.79 | Activity logs are retained for only 0 day(s) |
| MON-003 | Planned | 36.94 | Security monitoring coverage is approximately 0% |

## Disclaimer

This evidence pack is an insurer-facing technical summary derived from the deterministic CRIS-SME assessment. It is not legal, regulatory, or insurance advice and should be reviewed alongside the organisation's formal insurance application.
