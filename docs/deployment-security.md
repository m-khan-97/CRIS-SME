# Deployment Security Restrictions

## Local API State Ownership

The local API takes nonblocking POSIX advisory locks for its report directory,
figure directory and database before loading or recovering persisted runs. A
second cooperating API sharing any of these exact paths fails startup instead
of marking the first API's runs interrupted. Resolved symlink aliases share the
same locks. Lock files remain on disk after shutdown; do not delete them to
resolve contention. Port range, request deadlines, connection limits and browser
policy are checked before state directories are created.

This is a single-host, trusted-filesystem safeguard, not distributed job leasing
or tenant isolation. Direct library users and CLI scans do not take these locks;
do not run them against a live API's output paths. Nested output roots, hard-link
database aliases and network filesystems are not supported ownership boundaries.
An API process exiting releases its locks but does not prove its scan child has
stopped. Stop the entire service process group (the container supervisor does
this) and verify no old scan is running before restarting after a crash. A bind
failure can still occur after persisted-run recovery; it releases all locks.

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
6. Do not use public-exposure probes for untrusted targets. As defense in depth,
   use a dedicated probe environment with network-enforced denial of internal,
   loopback, link-local and cloud-metadata destinations, including IPv6. Do not
   run that environment with cloud credentials or sensitive internal reachability.
   Address validation/pinning does not establish target ownership or control
   network routing; it is not a substitute for these deployment restrictions.

Public-exposure HTTP probes now record only the first response: redirect locations
remain report evidence, but are not contacted. A redirected security.txt therefore
does not establish file availability. HTTP probes deliberately ignore inherited
proxy configuration; proxy-only networks may report connection failures. These
behaviors use a pinned connection with the standard library's HTTP protocol
implementation (see [Python HTTP client documentation](https://docs.python.org/3/library/http.client.html)).
Initial DNS failure skips all target probes; public mode excludes invalid and
non-global addresses, including shared address space. Native HTTP, HTTPS, TLS
metadata, legacy TLS and optional port probes reuse the initial address snapshot.
Connections use numeric IPv4/IPv6 sockets without a second hostname lookup;
fallback is limited to addresses in that snapshot. HTTP Host and TLS SNI retain
the original hostname, and normal HTTPS certificate verification remains enabled.
Legacy protocol-support probes retain their separate non-validating handshake
behavior; they do not establish certificate trust. Redirects are never followed.

Direct probe-function calls also validate a single DNS snapshot by default.
Explicit private-target mode permits non-public addresses for trusted labs, but
still rejects malformed addresses and IPv6 zone identifiers. Injected Python
probe callbacks are trusted extension/test code and are outside the native
transport guarantee. Private-target mode is not a hosted-user permission.

## Browser Request Policy

The local API now checks Host and Origin before dispatching any route. Default
Host names are `127.0.0.1`, `localhost` and `[::1]` (valid request ports are
accepted). Default browser origins are HTTP on those hosts at ports 5173, 8080
and 8787, covering the standard Vite, Docker and direct-API workflows. Only an
approved Origin is echoed in CORS responses; wildcard CORS is not used.

Unapproved or opaque (`null`) origins return 403. Duplicate Origin/Host headers
and malformed Host values return 400. Requests marked `Sec-Fetch-Site: cross-site`
without Origin are rejected. CLI requests without browser headers still work.
Origin includes scheme, host and port; see the
[browser header reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Origin).

For a deliberately configured private host or a different frontend port, specify
the exact startup allowlists. Each repeated option **replaces**, rather than
extends, its corresponding defaults:

```bash
python -m cris_sme.api.local_runner --allowed-host 127.0.0.1 --allowed-host localhost --allowed-origin http://127.0.0.1:5174
```

Host options contain hostnames only, without scheme or port. Origin options must
be explicit HTTP(S) origins without paths, queries, fragments or wildcards.
Changing the bind address does not implicitly trust a new Host or browser origin.
Downloaded `file://` dashboards are not trusted; serve them from an approved
local origin instead. Proxies must preserve Origin and enforce their own Host
policy; forwarded headers are not used to grant access.

These checks restrict browser access and Host-based attacks, but are **not
authentication, tenant isolation or complete CSRF protection**. Non-browser
clients can supply headers, and code running at an approved local origin is
trusted. Keep the existing isolated single-operator deployment restrictions.

## Request And Import Limits

Local API POST routes require one decimal `Content-Length`, a single
`Content-Type: application/json` header (parameters allowed), and at most 65,536
body bytes. Missing length returns 411, oversized bodies 413, and unsupported
media types 415. Transfer encoding, duplicate lengths, malformed UTF-8/JSON and
non-object payloads are rejected with 400. This narrows request parsing, but
does not add authentication or global concurrency quotas.

The socket idle timeout, total request-line/header deadline and separate total
JSON body-read deadline each default to 10 seconds. The header deadline covers
the request line and all header lines together, including continuously trickled
bytes. Once body reading begins, trickled bytes do not reset its deadline;
an expired body read returns 408 and closes the connection before cloud work.
Stalled request lines/headers are closed by the idle timeout without promising a
JSON response. The timeout is configurable using `--request-read-timeout` with a
finite positive number of seconds. It does not shorten the cloud scan itself.
The runner admits at most 16 simultaneous connection workers by default; use
`--max-connections` with a positive integer to change that limit. Excess accepted
connections are closed without creating a worker or promising an HTTP response.
Slots are returned after connection handling, including worker/startup failures.
This bounds API worker count, not per-user request rates, response
sizes or execution time. Network-level denial of service remains possible. Keep
the single-operator boundary until the remaining controls exist.

Each local runner instance now admits only one assessment at a time across AWS,
Azure and public-exposure scans. A competing request returns HTTP 409 before
creating a scan worker or persisting another run. There is no pending scan queue;
the operator must retry after the active assessment finishes. The slot covers
public-exposure artifact publication and is released on completion and failure,
including worker-start and persistence failures. Cloud subprocesses retain their
existing 900-second timeout; synchronous public probes have no new whole-scan
deadline from this change.

This admission gate is in-process; API lifecycle locks provide the separate local
process safeguard described above. Neither is a distributed worker lease. Do not
run direct CLI scans or other writers against live API output folders. Durable
queuing, tenant quotas and rate limits are not implemented.

## Cloud Run Namespaces

New AWS/Azure API assessments reserve fresh server-generated directories under
`<output-dir>/assessments/<API-run-id>/reports` and sibling `figures`. Organization
names and request-supplied paths never choose these directories. Existing run IDs
or directories are not reused. The configured `figure-dir` remains available for
legacy figure downloads; new cloud-run figures are stored alongside their reports.
CLI execution and existing report files are unchanged.

History and artifact downloads discover these namespaces only after the cloud
worker is recorded as completed. Queued, running, failed and untracked namespaces
are not published through those routes. `/outputs/<export>` and
`/api/artifacts/latest` resolve the newest completed API run with a readable report;
they do not copy it over legacy files. Old root/history and evidence-lab reports
remain selectable. Explicit artifact paths keep referring to their original run.
Missing exports in the selected latest run do not fall back to a different run.
Public-exposure exports resolve a separate latest public run, as described below.

This is local run separation, not immutable storage, tenant authorization or a
transactional blob publication protocol. API-run IDs and report provenance IDs
remain distinct; the stored run artifact path links them without rewriting report
evidence. The single-scan gate remains. Index enumeration has no new total-size or
retention bound. Raw filesystem/static-server access bypasses API publication.

New namespaces start with empty comparison history. They intentionally do not
inherit the previous organization's report. Historical report selection remains
available, but automatic cross-run drift/lifecycle comparison needs explicit
account, connection and scope matching before being enabled for these runs.

## Public Exposure Run Storage

New public-exposure API scans reserve the same run directory layout and save
their lifecycle in SQLite with collector `public_exposure`. The synchronous scan
response includes the server-generated `run_id`; JSON/Markdown artifact paths
identify that exact run. `/api/assessment-runs` includes these records, and
`/api/assessments/<run-id>` returns their persisted status and artifact listing.
The cloud report history retains its cloud report schema and excludes public runs.

Public exports become downloadable after completion and when the JSON report's
run ID matches its directory. Failed or interrupted scans cannot replace the
latest completed public result. The JSON and Markdown `/outputs/` aliases and the
public-exposure entry in `/api/artifacts/latest` resolve independently of cloud
latest results. Explicit artifact paths retrieve earlier completed public runs.
Existing root public results remain readable as legacy exports. Missing exports
in a selected run return 404 rather than an export from a different run.

Publication still depends on local SQLite state and trusted filesystem access.
The scan remains synchronous with one assessment admitted at a time; cancellation,
durable worker leases and a dedicated public-history browser selector are pending.

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

## Request And Worker Scope

Assessment authorization requires the JSON boolean `true`, not a nonempty string,
number, list or object. The optional common-port scan flag must also be a JSON
boolean. Public-exposure requests contain 1-10 nonempty string targets, each at
most 2048 characters; oversized lists are rejected instead of silently truncated.
This validates intent syntax, not ownership or user identity.

Cloud inputs are validated before run admission or role verification. Nonempty
AWS account IDs contain 12 ASCII digits; Azure subscription and tenant IDs use
hyphenated UUIDs. IAM role ARNs must identify a role, and an explicit account ID
must match the role's account. An external ID requires a role and supported
non-space characters; role verification shares this validation. See the official
[STS parameters](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html)
and [IAM role constraints](https://docs.aws.amazon.com/IAM/latest/APIReference/API_CreateRole.html).
Organization names are trimmed strings of at most 256 characters, without control
characters. Invalid types are rejected, not coerced into strings. Optional cloud
IDs remain blank for credential-based discovery; successful syntax validation
does not establish IAM trust, RBAC permission or target authorization.

Scan subprocesses and CLI credential helpers use explicit, provider-specific
environment allowlists in [worker_environment.py](../src/cris_sme/api/worker_environment.py).
Supported runtime paths, proxy/CA settings, provider credential/profile settings
and selected CRIS configuration are retained. AWS children do not inherit Azure
credential variables, or vice versa; arbitrary application secrets are dropped.
The narrator key is retained only when narrator enablement is explicit.

Browser-request account/subscription scope, organization names/IDs, target-role
settings and output/event paths do not inherit stale parent values. The runner
sets its own output/event paths and applies validated request fields. Workload
identity settings such as `AWS_ROLE_ARN` identify source credentials and remain
distinct from the requested target role (`CRIS_SME_AWS_ROLE_ARN`). Operator region,
sector, provenance and Azure resource-group filters remain supported. Unsupported
custom environment variables are no longer inherited; review the allowlist before
using a custom credential process or network setup. Direct CLI scans are unchanged.

This is environment minimization, not process isolation. The child still runs as
the same OS user and can access that user's files, credential caches and trusted
runtime configuration, including HOME, PATH and PYTHONPATH. In-process SDK checks
still use the runner's credentials. Separate users/workers and scoped secret
delivery remain requirements for hosted tenants.

## Error Responses

Credential checks and AWS role verification return fixed, application-authored
failure messages rather than raw SDK exceptions or Azure CLI stderr. Azure CLI
responses that cannot provide an account object with an ID do not claim a
successful sign-in; exported user metadata is limited to name and type.

GET/POST dispatch errors use generic HTTP 500 messages. Only explicitly marked
public validation errors are returned verbatim; an arbitrary `ValueError` is not
assumed safe to display. Public-exposure target-validation errors do not reflect
the raw submitted target. Busy-scan and request-framing messages retain their
documented 409/4xx status codes.

Run creation, status and run-list responses now set `diagnostics_withheld: true`.
The compatibility fields `stdout_tail` and `stderr_tail` are empty; a failed run
has a fixed message directing the operator to private local diagnostics using
the run ID. This projection also applies to existing records restored from SQLite.
Stored diagnostics are not rewritten or deleted.

The status timeline is reconstructed from known phase/status values, bounded
integer sequence numbers and valid timezone-aware timestamps. Free-form worker
messages, detail dictionaries and unknown fields are not sent to the browser;
phase messages are authored by the API. Event files are limited to 1 MiB, read
without following symlinks, and return at most the first 200 valid events. Invalid,
partial, oversized or unsupported events may be omitted. The run's status remains
the completion signal; an empty or truncated timeline is not proof of no activity.

This is not comprehensive secret redaction. Private SQLite records and JSONL
files still retain raw diagnostics, and scanner evidence and downloadable reports
may contain diagnostics. Organization/account metadata and artifacts remain
confidential. No centralized redacted diagnostic store or correlation-ID workflow
is provided by this change. The API status projection is not a publication check
for full reports, backups or static exports.

## Artifact Downloads

The local API serves an explicit export allowlist, not arbitrary files beneath
the output folder. `/outputs/` is restricted to recognized report files, dated
history snapshots, named figures and remediation reference exports. The
`/api/report-artifact` route applies the same policy to the current directory
and other directories represented in the existing report index; it also supports
the configured figures directory and indexed reports' adjacent figures.
Run databases, event logs, hidden files, review ledgers and unregistered files
are not downloadable through these routes. New export types require an explicit
policy update in `api/artifact_access.py`.

Artifact downloads have a 32 MiB per-file read cap; an otherwise allowed file
over that cap returns HTTP 413. Report indexing and selected-report JSON use a
stricter 16 MiB cap. The reader checks the opened file's size before allocating
its contents and reads at most the cap plus one byte to detect growth after the
check. These are local API constants, not new CLI settings. Oversized, malformed
or excessively nested report JSON is omitted from history; existing files remain
unchanged and can be inspected locally. An empty history therefore does not prove
that no reports exist. A report changed after indexing is checked again on read.
Malformed metadata containers cannot crash indexing.

These byte caps do not bound decoded JSON object memory, the number of indexed
reports, aggregate concurrent memory or other CLI/import parsers. They are not a
complete report-schema validation or an immutable-file guarantee.

Reads use POSIX descriptor-relative opens with no-follow flags, reject symbolic
links and non-regular files, and return 404 on rejection. Report indexing and
selected-report reads also reject symlink traversal. Downloads fail closed on
platforms without the required POSIX support. These checks assume trusted local
writers and configured directory ancestors; hard links and malicious local
filesystem administrators are not an isolation boundary.

This is export filtering, not per-user or per-tenant authorization. Recognized
historical reports remain available to the same trusted local operator; shared
hosting still requires authenticated artifact IDs and tenant ownership. Static
servers serving files directly do not inherit this API policy.

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
