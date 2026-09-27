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
| T02 / high | Hostile browser calls local API; wildcard CORS, no Origin/Host validation | Loopback limits network exposure but does not authorize browser origins | P1-01/09, BE/SE: exact origin/host policy, CSRF protection appropriate to auth, negative browser tests |
| T03 / high | Artifact disclosure, including siblings and internal state | Resolved-path containment exists, but `/outputs/` serves files beneath output_dir; artifact route can cover parent `outputs/`; no per-run allowlist | P1-03/05, BE: authorized artifact IDs, deny internal files and symlink escapes, cross-run tests |
| T04 / high | Probe SSRF into internal/metadata services: [public exposure](../src/cris_sme/engine/public_exposure.py) | Initial private-address rejection; subsequent hostname connections resolve again and urllib follows redirects | P1-09, SE/BE: pin approved public addresses, revalidate every redirect, test DNS rebinding, IPv4/IPv6 and metadata destinations |
| T05 / high | Wrong-customer report or overwritten evidence during concurrent scans | Shared output paths despite persisted run state | P1-03/04/05, BE: isolated run directories, atomic publish, ownership and concurrent/crash tests |
| T06 / high | Credential or confidential context leakage through environment, logs, API errors or publication | SDK/CLI credential discovery; subprocess inherits environment and stores output tails; no demonstrated comprehensive redaction | P1-09/P0-08, SE/RE: allowlisted child environment, redaction fixtures, secret scanning and publication review |
| T07 / high | Request/import exhaustion and expensive repeated scans | POST JSON bodies capped at 64 KiB; ambiguous/unsupported framing rejected before work. Scan subprocess timeout exists; no request-read deadline or global scan quota; imported JSON files loaded whole | P1-09/P2, BE: read deadlines, file limits, bounded concurrency and slow-input tests; body-cap regressions now cover all four POST routes |
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
