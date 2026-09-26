# Security Policy

## Supported Boundary

The current pre-1.0 development line is maintained on a best-effort basis.
There is no LTS/security-backport commitment or guaranteed response SLA.
Read the [support policy](SUPPORT.md) and
[deployment restrictions](docs/deployment-security.md) before use. The local
runner is unauthenticated and is not approved for public/shared hosting.

## Reporting A Suspected Vulnerability

Do not publish exploit details, credentials, customer data or raw cloud reports
in an issue or pull request. GitHub private vulnerability reporting was **disabled
when checked on 26 September 2026**; a confidential intake channel still needs
activation and an end-to-end maintainer check.

When enabled, use the repository's
[private advisory form](https://github.com/m-khan-97/CRIS-SME/security/advisories/new).
Until a private route is confirmed, a public issue may request a confidential
contact using only the subject "Private security contact requested" and no
technical details. Wait for an agreed private channel before sending the report.
This fallback is a contact request, not a confidential reporting mechanism.

Once a private channel is agreed, include affected commit/version, the supported
deployment involved, impact, minimal synthetic reproduction and suggested
mitigations. Do not test other people's deployments or access data beyond your
authorization. There is no bounty or legal safe-harbor promise in this policy.

## Handling And Disclosure

The maintainer triages scope and impact, seeks a reproduction, agrees disclosure
timing with the reporter, and records a fix or mitigation with regression tests.
Aim to acknowledge reports within 14 days; this is a target, not measured response
history. Urgent credential exposure needs immediate containment and owner
notification. Keep sensitive investigation records outside public issues.

Publish an advisory and upgrade/mitigation instructions when appropriate, with
reporter credit only by consent. Release notes should reference assigned public
vulnerability identifiers. Do not close a report solely because the project is
pre-release; distinguish documented deployment limits from a defect in those limits.

Private reporting, branch protection, secret scanning, security analysis and
incident response are separate controls. This document does not establish their
operation. See the [threat model](docs/threat-model.md) and
[OpenSSF evidence gaps](docs/openssf-evidence.md).
