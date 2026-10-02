# CRIS Threat Model

Review date: 24 September 2026. Scope: current local runner, collectors, reports,
imports, MCP and optional narrator. This is a source-based threat assessment,
not a penetration test, certification or claim that the listed gaps are fixed.
Maintainer responsibility: security/engineering lead (roadmap SE/BE); a named
security contact and disclosure process remain P0-08 work.

## Deployment Boundary

The supported baseline is one trusted operator on an isolated workstation or
private single-operator host. The runner has no application authentication or
tenant authorization. A private network alone does not establish user trust.
Follow [deployment restrictions](deployment-security.md). Internet-facing and
shared-customer API deployments are outside the current security boundary.

## Assets And Actors

Protect cloud credentials, assumed-role sessions, account/subscription identifiers,
resource topology, finding/evidence records, reviewer identities, reports,
exceptions, run history, integrity keys and CI publication credentials.

Trusted actors are the authorized operator and maintainers controlling installed
code/policy. Potential attackers include hostile browser pages, other local or
network users, contributors supplying malicious dependencies or artifacts, and
owners of probed endpoints or attacker-controlled cloud names/tags. Cloud API
authentication does not make returned free text safe to render or send to an LLM.

## Data Flows And Trust Boundaries

| Boundary | Flow | Current trust assumption |
| --- | --- | --- |
| Browser to runner | Console requests scan, role verification, probes, history and artifacts | Network reachability grants access; UI confirmation is not authentication |
| Runner to cloud | Subprocess uses inherited environment, Azure CLI or AWS credentials/STS | Operator supplies scoped read-only identity; account name is not an authorization boundary |
| Cloud to evaluation | Provider data becomes normalized evidence and findings | Evidence content is untrusted; missing evidence must remain explicit |
| Runner to storage | SQLite run state, event files, JSON/HTML/CSV reports and snapshots | Local filesystem permissions protect data; no tenant isolation |
| Storage to browser/MCP | Report routes and MCP query tools expose local assessment records | Every connected client must be trusted for the entire configured dataset |
| Import to evaluation | Snapshot/report JSON, CE review CSV/JSON, policy/exception files and RBOM paths | Operator controls source and paths; not an untrusted upload service |
| Probe to network | DNS, HTTP(S), TLS and optional port connections to requested targets | Target owner authorizes probes; hostile DNS/redirects remain a risk |
| Report to narrator | Optional compact report sent to Anthropic | Explicit data-sharing approval required; generated text is not authoritative |
| Build to runtime | Dependencies, policy assets, image and static published artifacts | Locks constrain dependencies; provenance and publication need separate review |

## Threat Register

Priorities describe deployment impact, not CVSS scores. All unresolved entries
below remain open; operating restrictions are mitigations, not code fixes.

| ID / priority | Threat and source evidence | Existing control / residual gap | Required work and acceptance |
| --- | --- | --- | --- |
| T01 / hosting blocker | Unauthenticated calls read reports or spend cloud/probe resources: [runner handler](../src/cris_sme/api/local_runner.py) | Loopback default and Compose host binding; no identity, RBAC or tenant checks | P1-01/02, BE/SE: deny unauthenticated calls and test cross-user/account access |
| T02 / high | Hostile browser calls local API | Host allowlist, exact Origin allowlist, no wildcard CORS, and rejection before route dispatch now have regression coverage. Non-browser clients can forge headers; approved origins remain trusted | P1-01/09, BE/SE: authenticated sessions and appropriate CSRF controls, adversarial browser/proxy testing; these guards do not authorize users or tenants |
| T03 / high | Artifact disclosure, including siblings and internal state | Explicit export allowlist; sibling exports require an indexed report. Descriptor-relative no-follow reads reject symlinks/special files; internal databases, logs and ledgers are excluded. Local history remains shared with the trusted operator | P1-03/05, BE: authenticated artifact IDs and tenant ownership, immutable run storage and cross-tenant tests; static file servers and hostile local writers are outside this API boundary |
| T04 / high | Probe SSRF into internal/metadata services: [public exposure](../src/cris_sme/engine/public_exposure.py) | Native probes validate and pin one address snapshot across HTTP/TLS/ports, without hostname re-resolution; redirects and inherited proxies disabled. Regression tests cover rebinding, mixed addresses, metadata exclusions, IPv4/IPv6 numeric connections and HTTPS identity | P1-09, SE/BE: retain network egress restrictions, independently review transport and enforce hosted target authorization; private-target mode and trusted callback injection remain outside the public-only guarantee |
| T05 / high | Wrong-customer report or overwritten evidence during concurrent scans | Single-scan admission and local API lifecycle locks remain. New cloud and public API scans reserve individual directories and persist status; completed results enter download discovery. Cloud/public latest aliases resolve separately. Legacy paths, CLI/library writers and orphan children remain outside coordination | P1-03/04/05, BE: tenant ownership, transactional publication, durable leases, scope-matched comparisons and concurrent/crash tests |
| T06 / high | Credential or confidential context leakage through environment, logs, API errors or publication | Fixed public exceptions and projected run progress with raw diagnostics withheld. Child/CLI-helper environments now use provider-specific allowlists, excluding unrelated secrets and stale request scope. Same-user files, SDK credential caches and private stored/report diagnostics remain confidential | P1-09/P0-08, SE/RE: isolated credential delivery, private log/evidence redaction, secret scanning and publication review; environment filtering is not a sandbox |
| T07 / high | Request/import exhaustion and expensive repeated scans | POST JSON bodies capped at 64 KiB; framing checks, separate 10-second total header/body deadlines and socket idle timeout precede work. API workers capped at 16 connections by default; saturation closes excess sockets. API artifact reads capped at 32 MiB and indexed/selected report JSON at 16 MiB, with growth detection. Scan subprocess timeout exists | P1-09/P2, BE: global scan quotas, endpoint rate limits, index-count/decoded-memory budgets and limits on other import parsers; these per-file/connection caps are not complete denial-of-service protection |
| T08 / high | Malicious evidence rendered as HTML, spreadsheet formula or model instructions | Rendering/parse helpers and narrator separation exist; no comprehensive hostile-input assurance | P0-06/P2, BE/SE: context-specific escaping, CSV formula handling and hostile report fixtures across export surfaces |
| T09 / medium | Tampered review ledger, exceptions or RBOM changes apparent assurance | Parsers and RBOM checks exist; local writers are trusted, HMAC key holders can forge records; RBOM paths can be absolute | P4-04/P1, SE: constrain imported paths, independent signatures, authorized/audited review changes; tampering tests |
| T10 / high | MCP client or LLM service receives another customer's evidence | [MCP](../src/cris_sme/mcp/server.py) uses local report tools; [narrator](../src/cris_sme/reporting/narrator.py) disabled by default | P1/P4, BE/SE: scope every query, minimize transmitted data, test egress and prompt-injection boundaries |
| T11 / high | Compromised release or accidental customer-data deployment | Hash-locked Python dependencies, pinned base images and package smoke checks; hosted gates still need confirmation | P0-06/08, RE: review publication inputs, verify CI/release lineage, secret/dependency checks and recovery procedure |

## Secret And Storage Inventory

- Azure CLI cache and configured SDK credentials; AWS profile/config, exported
  access keys/session tokens and STS credentials: keep outside source/image/report
  directories. Mount only the required credential material, never the whole home.
- AWS external IDs are trust-policy context, not replacement credentials or user
  authentication. Treat them as sensitive configuration, not public report labels.
- `ANTHROPIC_API_KEY` and RBOM HMAC signing keys: separate from artifacts and
  logging. A shared HMAC does not establish third-party authorship.
- CI/deployment credentials: use the hosting platform's secret storage; do not
  include values in examples, build arguments or browser bundles.
- SQLite state, stdout/stderr tails, events, histories and generated artifacts
  contain confidential context even when no raw secret is intentionally exported.
  Filesystem permissions and backups are operator-managed; automatic retention,
  encryption at rest and verified deletion are not established product guarantees.

## Evidence And Review

Existing regression suites include local API, public exposure, CE review import,
MCP, narrator and packaging tests. Passing them is not proof that the open threats
are mitigated. P0-05 adds the deployment inventory and source-default regression
checks, not an authentication or SSRF redesign.

Revisit this model when adding a route, parser, collector, output format, external
service, tenant boundary or deployment mode. Changes must update the threat ID,
owner, test evidence and [roadmap](roadmap.md). P1 hosting gates require adversarial
authorization/isolation tests and an independent security review before widening
the current deployment boundary.
