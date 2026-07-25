# CRIS-SME 30-Day SME Action Plan

- Planning basis: Actions are phased by deterministic risk score, remediation cost tier, and SME-operational practicality so free and low-friction improvements land first.

## Fix this week

- Time window: `Days 1-7`
- Goal: Prioritize zero-cost or low-friction fixes that reduce immediate exposure.
- Total actions: `5`
- Cumulative risk score: `236.51`

| Control | Priority | Score | Cost Tier | Action |
| --- | --- | ---: | --- | --- |
| IAM-001 | High | 67.97 | free | Require MFA and admin-focused conditional access for privileged identities. |
| DATA-001 | Planned | 48.35 | free | Disable anonymous or public storage access and review data exposure paths. |
| NET-002 | Planned | 44.71 | free | Tighten overly permissive network rules to least-privilege source and port scopes. |
| IOT-002 | Planned | 41.60 | free | Reduce IoT shared access policies, remove overbroad permissions, and rotate keys through governed operations. |
| GOV-003 | Planned | 33.88 | free | Increase baseline policy assignment coverage for governance and compliance controls. |

## Complete this month

- Time window: `Days 8-30`
- Goal: Deliver the best remaining low-cost improvements within a lean SME operating window.
- Total actions: `7`
- Cumulative risk score: `187.72`

| Control | Priority | Score | Cost Tier | Action |
| --- | --- | ---: | --- | --- |
| IAM-003 | Monitor | 23.34 | free | Rotate or remove stale service principal credentials and disable unused identities. |
| GOV-004 | Monitor | 17.87 | free | Review and remove unused or orphaned resources to reduce cost and governance noise. |
| GOV-002 | Monitor | 16.39 | free | Configure budget thresholds and spend alerts for cost oversight. |
| IOT-010 | Monitor | 4.72 | free | Document clinical, operational, and supplier ownership boundaries for IoMT assets and validate device-level evidence manually. |
| IOT-005 | Planned | 47.25 | low | Restrict IoT Hub public access using IP filters, private endpoints, or documented clinical network boundaries. |
| DATA-002 | Planned | 42.36 | low | Enable encryption at rest for affected storage and database services. |
| MON-001 | Planned | 35.79 | low | Increase log retention to support investigation, governance review, and evidence preservation. |

## Plan next

- Time window: `After day 30`
- Goal: Schedule higher-effort items that likely need architecture, tooling, or procurement support.
- Total actions: `5`
- Cumulative risk score: `89.55`

| Control | Priority | Score | Cost Tier | Action |
| --- | --- | ---: | --- | --- |
| IOT-008 | Monitor | 21.98 | low | Store and rotate IoT credentials through governed key-management services with owner accountability. |
| IOT-003 | Monitor | 21.77 | low | Enable IoT Hub diagnostic settings and route core diagnostic categories to a monitored destination. |
| IOT-007 | Monitor | 20.93 | low | Route IoMT telemetry to governed storage and retain sufficient logs for investigation and clinical safety review. |
| IOT-009 | Monitor | 20.30 | low | Create IoT-specific alert rules and route them to accountable clinical or operational responders. |
| IAM-005 | Monitor | 4.57 | low | Broaden tenant-level identity evidence collection before treating IAM coverage as complete. |
