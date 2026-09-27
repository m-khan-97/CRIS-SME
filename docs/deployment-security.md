# Deployment Security Restrictions

## Current Supported Boundary

CRIS's local runner is unauthenticated. Use it only as a single trusted operator
on an isolated workstation or private host. Do not publish it as a shared service,
expose it through a public tunnel, or treat a VPN/reverse proxy as tenant isolation.
The [threat model](threat-model.md) records the remaining browser, file, egress
and authorization risks. These are operating requirements, not enforced policies.

## Before Running

1. Use a dedicated OS account or disposable VM, current dependencies and a trusted
   browser profile. Avoid untrusted websites/extensions while the runner is active.
   Loopback is not protection from hostile local software or browser-origin attacks.
2. Keep the API on `127.0.0.1` (default port 8787). Keep Compose's published port
   `127.0.0.1:8080:8080`; do not replace it with `8080:8080` or host networking.
   For manual Docker runs, explicitly bind `-p 127.0.0.1:8080:8080`.
3. Use a dedicated read-only cloud identity with documented account/subscription
   authorization. Review [Azure permissions](azure-least-privilege-setup.md) and
   [AWS permissions](aws-least-privilege-setup.md). Do not provide root/admin keys.
4. Keep one organization's credentials and outputs in each isolated working
   environment. Run one assessment at a time; UI organization labels and run
   selectors are not security boundaries. Restrict output permissions (for
   example, start the process with `umask 077`).
5. Leave `CRIS_SME_ENABLE_NARRATOR=false` unless the organization approves the
   transmitted report context and third-party processing. Keep MCP local and
   connect only clients trusted to read the entire configured dataset.
6. Do not use public-exposure probes for untrusted targets. Until T04 is fixed,
   use a dedicated probe environment with network-enforced denial of internal,
   loopback, link-local and cloud-metadata destinations, including IPv6. Do not
   run that environment with cloud credentials or sensitive internal reachability.
   The initial application DNS check is not sufficient SSRF protection.

## Imports And Exports

Local API POST routes require one decimal `Content-Length`, a single
`Content-Type: application/json` header (parameters allowed), and at most 65,536
body bytes. Missing length returns 411, oversized bodies 413, and unsupported
media types 415. Transfer encoding, duplicate lengths, malformed UTF-8/JSON and
non-object payloads are rejected with 400. This narrows request parsing, but
does not add authentication, request-read deadlines or global concurrency quotas.

Accept snapshots, reports, review CSV/JSON and RBOM manifests only from trusted
sources. Inspect file size and referenced paths first; use an isolated environment
for unfamiliar input. Do not wrap these local parsers in a public upload endpoint.
Do not open unreviewed spreadsheet exports with macros/active content enabled.

Treat all generated reports, raw snapshots, history, run databases and logs as
confidential. Review HTML/JSON/CSV content and embedded identifiers before sharing.
Static hosting makes deployed files downloadable: publish only explicitly approved,
sanitized demo artifacts, never a whole customer output directory. Do not upload
credential caches, signing keys or environment files. A static demo is distinct
from exposing the live runner.

## Shutdown And Incident Handling

Stop the runner and revoke network access when not in use. `docker compose stop`
stops the service but retains its data volume; this is not a data-deletion command.
Apply the agreed retention policy to outputs, backups, CI artifacts and deployed
copies. Do not delete customer evidence without the owner's approval.

If unintended access is suspected: stop exposure, preserve necessary logs securely,
identify affected artifacts/accounts, revoke or rotate potentially exposed
credentials, notify the owner and investigate before restarting. Removing a report
URL does not revoke downloaded copies.

## Exit Criteria For Shared Hosting

P1 must establish authenticated users, per-account authorization, tenant-scoped
storage/jobs/artifacts, bounded requests and egress, audit/redaction controls and
negative tests. A successful Docker smoke test or OWASP project listing would not
replace those requirements. See [roadmap](roadmap.md) and
[container instructions](packaging-and-container.md).
