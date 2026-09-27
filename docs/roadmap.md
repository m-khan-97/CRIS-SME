# CRIS Enterprise And Product-Family Roadmap

Updated: 21 September 2026. Status: proposed execution baseline, not implemented capability.

This is the **single authoritative product and engineering roadmap**. It replaces the former 0/30/60/90-day roadmap, the 2026 H2 roadmap, the rebranding plan and implementation sequences in older strategy documents. Research manuscripts and historical evaluation plans remain records, not current product commitments.

Read the [reference repository audit](enterprise-reference-audit.md) for inspected code, limitations, licensing considerations and the reasons behind these priorities. The [architecture](architecture.md) describes the current system; this document describes the target and the work separating them.

## 1. Product And Organization Decision

Build **CRIS as an evidence-driven security decision platform**, with a shared engine and three focused modules:

| Module | Buyer and purpose | Starting position | Release boundary |
| --- | --- | --- | --- |
| CRIS-SME | SME owners/security leads and MSPs: cloud remediation and Cyber Essentials evidence preparation | Existing Azure/AWS assessment and assurance implementation | Preserve affordable local/private use; pre-assessment is not certification |
| CRIS-IoMT | Healthcare security and clinical engineering: cloud-connected medical-system assurance | Existing healthcare/IoMT research track | Cloud evidence cannot establish device safety or whole-estate compliance |
| CRIS-PQC | Enterprise security architects and migration owners: cryptographic discovery and migration planning | Proposed product module | Discovery and planning first; no blanket quantum-safe certification |

Use **Aureon Systems as the proposed commercial umbrella**, subject to confirming the legal entity, ownership and naming rights. CRIS is the product family, not a statement that a company or GitHub organization has already been created. Larger organizations are a valid PQC market; this does not require abandoning SMEs or maintaining three independent platforms.

The product thesis: **connect security conclusions to evidence, reveal what remains unknown, and help an accountable owner choose the next affordable action**. Scanner count alone is not the differentiator. Comparing two repositories does not establish global novelty or patentability.

### Repository and governance boundaries

Keep the existing repository and `cris_sme` package initially. Build clear module boundaries inside a modular monolith; extract repositories only for components with independent maintainers and release needs.

| Boundary | Responsibility |
| --- | --- |
| Commercial organization | Contracts, support, hosted operations and approved branding |
| CRIS community project | Public core, schemas, collectors, rules and reproducible evaluation |
| Shared platform | Identity, workspaces, connections, runs, evidence, policies, decisions and audit records |
| Domain modules | SME/CE, IoMT and PQC models, rules, views and validated workflows |
| Research archive | Frozen paper artifacts with consent, redaction and manifests |
| Private customer storage | Assessment data, credentials and contracts; never a public artifact repository |

Before an organization transfer: identify at least two actual maintainers, enforce MFA/least-privilege teams, establish recovery, inventory Actions/OIDC/deployment integrations, test redirects and protect releases. Redirects do not repair cloud trust policies or deployment hooks automatically.

Preserve CLI commands, imports, report filenames and `CRIS_SME_*` variables. Any future rename needs a versioned migration and compatibility tests. Preserve paper reproduction commands against their original releases.

Prowler's inspected root license is Apache-2.0; OpenShield's is MIT. Review each imported component's actual license, notices, dependencies and standards-text rights. Branding changes do not remove attribution obligations. Disclose overlapping maintainer roles where relevant.

## 2. Current Baseline

The September source audit found:

- A substantial deterministic core, Azure/AWS adapters, evidence sufficiency, provenance, replay, lifecycle decisions, budget simulation, Cyber Essentials and IoMT work.
- A React console and local API with SQLite run-state persistence; full artifacts remain file-backed.
- No demonstrated authenticated multi-tenant boundary. Organization labels and report selectors are not authorization.
- Local threads/subprocesses and shared report paths that need replacement before concurrent hosted use.
- AWS AssumeRole support, but provider-specific validation is still needed before removing research-preview boundaries.
- At the reference audit, a 36-entry control catalog and five-entry newer metadata registry; P0-04 has since completed metadata parity (see progress below).
- Seven GitHub workflows, with existing security checks but incomplete whole-product CI and release assurance.
- HMAC-SHA256 report integrity support, not publicly verifiable asymmetric signing, release attestation or PQC signing.

These are implementation observations, not exhaustive security-audit results. Existing SIGI engagements and expert feedback can support scoped case studies; provenance, reviewer independence and measured outcomes must remain explicit.

## 3. Target Architecture And Contracts

Start with a **modular monolith and isolated workers**. Security boundaries matter more than service count.

```text
Browser / CLI / approved integrations
                 |
       Authenticated, versioned API
                 |
       Tenant and authorization policy
                 |
       Scheduler and durable job ledger
                 |
       Isolated least-privilege workers
                 |
 AWS / Azure / scanner imports / authorized probes
                 |
 Typed evidence -> versioned rules -> sufficiency -> decisions
                 |
 SME and CE views | IoMT views | PQC discovery and migration
                 |
 PostgreSQL metadata + tenant-scoped artifact storage
                 |
 Reports / tickets / audit exports / expiring sharing
```

Required contracts:

1. Separate tenant/workspace ID, organization display name, cloud account identity and scan ID. A typed organization name never authorizes access.
2. Every run records authorized scope, connection, initiator, timestamps, collector/rule versions, evidence mode and terminal status. Artifacts belong to one immutable run namespace.
3. Model evaluation outcome separately from evidence sufficiency. Distinguish pass, fail, unknown, error and not-applicable. An empty finding list is not proof of a pass.
4. Credentials belong in a secret-management boundary, not browser storage, reports or logs. Workers receive only the connection access needed for their job.
5. PostgreSQL tenant scoping and row-level security provide defense in depth. Runtime roles cannot bypass RLS; migrations use a different identity. Apply authorization to artifacts, caches, search, jobs and exports too.
6. Preserve local/offline assessment and controlled bundle import. Treat uploads as untrusted: limit size, validate schemas, prevent path traversal and check provenance.
7. Select durable execution through an architecture decision. A PostgreSQL leased-job queue is an initial candidate; Celery/broker adoption requires justified scheduling and throughput needs. Do not improvise a distributed queue without recovery tests.

## 4. Delivery Model

Planning envelope: **12-18 months or more with 3-5 dedicated engineers**, plus part-time security, cryptography and domain reviewers. This is a capacity assumption, not a staffed delivery commitment. A solo-maintainer plan requires re-estimation; enterprise gates cannot be compressed to meet pitch dates.

Owners: PL product/technical lead; BE backend/platform; SE security engineering; DE detection/content; FE frontend; RE release/operations; VR validation/research; GT commercial/community. One person may hold several roles initially, but independent review requires another reviewer.

| Phase | Indicative window | Dependencies | Exit decision |
| --- | --- | --- | --- |
| P0 Correctness and baseline | Weeks 0-4 | None | Reproducible, accurately described local release |
| P1 Secure platform | Weeks 4-12+ | P0 | Isolated, recoverable private pilot |
| P2 Scanner/content maturity | Months 3-5+ | P0; P1 for hosted use | Validated AWS/Azure scope and interoperable evidence |
| P3 PQC discovery | Months 4-7+ | P2 contracts; P1 for hosting | Reviewable crypto inventory |
| P4 Decision validation | Months 6-9+ | P2; P3 for PQC experiments | Comparative evidence for selected benefits |
| P5 Enterprise/IoMT pilots | Months 8-12+ | Applicable P1-P4 gates | Procurement-ready supported pilots |
| P6 GA and ecosystem | Months 12-18+ | P5 and independent review | Scoped GA and sustainable operations |

Governance, threat modeling, documentation and user research continue throughout. Recruit participants early; comparative evaluations require an appropriate stable build. Parallel development is possible; release gates remain mandatory.

## 5. P0: Correctness And Baseline

Progress, 24 September 2026: **P0-01 implemented; hosted CI confirmation pending.**
The Mermaid-only assertion is replaced by Markdown-aware local-link/SVG checks,
and the summary reports actual step outcomes. Nineteen focused regression tests
pass locally. See [quality check reporting](ci-cd-and-vercel.md#quality-check-reporting).
This does not mark the remaining P0 work or the phase exit gate complete.

P0-02/03 are implemented and locally verified: installed policy assets, clean-wheel smoke
testing, a non-root private container and coordinated process shutdown are now
implemented. See [packaging and container verification](packaging-and-container.md).
Local verification passed: 353 tests, lint, and an sdist-to-wheel installation
that generated mock reports from an empty working directory without its source.
Hash-locked Python runtime/cloud/MCP/build/dev profiles and digest-pinned base
images are now implemented. CI verifies lock fingerprints and uses hash checking.
The locked environment passes 362 tests, lint, workflow-entrypoint type checks
and the installed-wheel smoke test; the fresh-environment check also exposed and
fixed missing AWS test SDK dependencies in the previous requirements.
On 24 September 2026, the operator reported a successful Docker acceptance run
covering non-root execution, report retrieval, persistence, shutdown and service
failure propagation. See the verification record linked above. The assistant
could not independently rerun Docker because its session lacks daemon access.
Hosted CI confirmation remains pending; the overall P0 gate is not complete.

P0-04 is implemented and locally verified: metadata revision 2.1.0 covers all
36 catalog controls, with schema, catalog/spec and evaluator-ID checks in CI.
Relationship validation rejects dangling links and dependency cycles. Provider
preview labels and unvalidated mapping provenance remain explicit; no detection
or scoring changes are claimed. The locked environment passes 380 tests and the
installed sdist/wheel smoke test. See [control metadata](control-metadata.md).
Hosted CI confirmation remains pending.

P0-05 documentation is implemented: the [threat model](threat-model.md) inventories
credentials, storage, imports, probes, MCP/narrator and publication boundaries.
[Deployment restrictions](deployment-security.md) limit the unauthenticated runner
to isolated single-operator use. Open authentication, browser-origin, artifact,
SSRF and concurrency risks have explicit follow-up owners and gates. This phase
does not fix those risks or approve shared hosting. Regression tests protect
documented runtime defaults; both documents are included in CI link validation.
Local verification: 384 tests passed, critical-rule lint passed, and all seven
documentation entrypoints passed link/SVG checks. Hosted CI remains pending.

P0-06 implementation is locally verified as of 26 September. Full-console
ESLint passes with zero warnings; 52 component tests and four fixture-backed
Chromium workflows pass on Node 22. Production, demo and self-host builds pass,
including type checks for test configuration. Frontend coverage floors are now
required in PR CI. Python 3.11/3.12 each pass 406 tests after the P0-07 additions,
with 79.38% package-wide combined coverage; the installed-package smoke also
passes. Mypy covers eight selected entry/runtime modules. Compatible frontend
dependency updates leave zero npm advisories at this measurement date.
See [quality baseline](quality-baseline.md) for exact denominators and exclusions.

P0-07 now has a schema-backed [capability evidence register](capability-evidence.md):
13 scoped entries distinguish implemented/planned delivery, fixture tests,
live observations and independent reviews. CI checks local references, evidence
digests, dates and independence declarations; 22 new regression tests cover the
register. Live and independent evidence admission remains pending review, not
a claim that historical customer scans or practitioner feedback never happened.
Original customer and research artifacts have not been changed by this work.

Remaining P0 gates: run this revision in hosted PR CI, independently reverify
container execution, configure required merge checks, and admit reviewed
historical evidence into P0-07. GitHub currently reports no classic main-branch
protection and no repository rulesets; those settings were not changed.
Runtime JSON validation and richer frontend interaction coverage remain follow-up
work, not guarantees supplied by compile-time interfaces.

Commit `8eb0595` is published. Its hosted static-site workflow, including the
reusable Python 3.11 quality job, passed; this is not the full PR/browser/container
matrix. See the [dated quality record](quality-baseline.md).

P0-08 is in progress: contribution, governance, support and security-reporting
policies now define the current single-maintainer, pre-1.0 boundary. The
[OpenSSF register](openssf-evidence.md) maps all 67 Passing identifiers without
claiming a badge or substituting policies for operational evidence. Offline
[dependency-license inventories](dependency-licenses.md) are generated for the
installed Python environment and npm lock, with CI artifact retention. Local
verification now passes 456 tests on both Python 3.11 and 3.12, plus Ruff and
16 documentation entrypoint checks; package coverage remains 79.38% combined.

Release preparation now has a fail-closed preflight: existing tag and checkout
identity, package version, clean source and authored tracked notes must agree.
Twenty-two regression cases exercise this gate. Manual tag input is passed as
environment data; Node setup and console dependency installation are explicit.
The workflow creates drafts, not automatically published latest releases. See
[release preparation](releases/README.md). This workflow change is locally
validated; no tag or release was created and no hosted release run is claimed.

The full PR quality suite is now reusable and manually dispatchable. Release
validation calls the same Python matrix, console/browser and container gates
before building a draft. Release assets now include both license inventories,
authored notes and a checked exact-set SHA-256 list, with 12 checksum regression
cases. These hashes are not signatures. Hosted execution of this revision and
independent release approval remain pending.

Next implementation priority: finish P0-08 operational gates (working private
security intake, repository protections, backup maintainer and release/license
review) alongside full hosted validation and historical evidence admission.
Private reporting and secret-scanning protections were disabled when checked;
no setting has been changed by these documentation/tooling additions. No badge
application or external project affiliation has been submitted.

27 September: `5fb89ce` is published. The first full hosted run passed the console
and container jobs, but both Python jobs failed the production-snapshot replay
check after their test/package stages passed. Local reproduction found that
replay omitted deterministic resource links attached by the assessment runner.
Replay now regenerates those links for linked snapshots and checks the captured
finding contents against their stored hash as well. Historical artifacts remain
unchanged. Commit `8c99b8a` fixes this; the
[full hosted rerun](https://github.com/m-khan-97/CRIS-SME/actions/runs/36281224558)
passed all four jobs, including Python 3.11/3.12 replay, console/browser and
container verification. The current local suites pass 517 tests on each Python
version, with 79.58% combined package coverage. This closes the hosted-execution
gap for that commit, not the independent validation or repository-protection gates.

P1-09 preparatory hardening adds a 64 KiB POST body cap, unambiguous length/media
type checks and strict UTF-8/object JSON parsing across all four local API POST
routes. This does not complete P1-01 or make the runner safe for shared hosting;
read deadlines, authorization, quotas and tenant isolation remain open.

| ID | Owner | Work and acceptance evidence |
| --- | --- | --- |
| P0-01 | RE | Repair stale Mermaid-only README assertion after SVG migration. Check linked diagrams and documents. CI summaries must reflect failed/cancelled jobs instead of always printing success. |
| P0-02 | BE/RE | Package required control/configuration assets. Test installed wheel and container from a clean directory without checkout `data/`. Run a complete mock assessment and retrieve its report. |
| P0-03 | RE | Verify entrypoint shell compatibility, signal forwarding and child cleanup. Test graceful stop/restart and writable volumes; remove runtime root where possible. Lock dependencies with an upgrade process. |
| P0-04 | DE | Inventory controls, evaluators, metadata, mappings and fixtures. Migrate all 36 baseline catalog entries to validated metadata or explicitly retire them. CI rejects active unregistered controls. |
| P0-05 | SE/PL | Publish threat model and deployment restrictions. Keep unauthenticated runner localhost/private. Inventory secrets, report exposure, import parsers, outbound probes and trust boundaries. |
| P0-06 | RE | Establish backend/frontend baseline tests, supported runtimes, package-build tests, browser workflows, lint/type scope and measured coverage. Do not reuse old test counts as current assurance. |
| P0-07 | PL/VR | Capability manifest distinguishes implemented, fixture-tested, live-observed, independently reviewed and planned. Preserve original evaluation provenance. |
| P0-08 | GT/SE | Maintainers, contribution/disclosure policies, support policy, license inventory and criterion-by-criterion OpenSSF evidence register. No unearned badges. |

**Gate:** clean installation produces a complete versioned assessment; required CI fails on deliberately introduced faults; public support claims match evidence. Not yet hosted-enterprise ready.

## 6. P1: Identity, Isolation And Reliable Runs

| ID | Owner | Work and acceptance evidence |
| --- | --- | --- |
| P1-01 | BE/SE | Maintained API framework, versioned OpenAPI and OIDC. Validate issuer, audience, signatures, expiry and algorithms; fail closed. Add session/CSRF protections appropriate to the flow. |
| P1-02 | BE/SE | Tenants, memberships and connection scopes. Owner/admin/operator/analyst/auditor roles with endpoint and object-level authorization tests. Roles cannot imply arbitrary cloud-account access. |
| P1-03 | BE | PostgreSQL migrations and run/finding/evidence metadata; blob storage for artifacts. Idempotent historical import preserves IDs and origin, never assigning tenants from display names alone. |
| P1-04 | BE/RE | Leases, heartbeat, cancellation, retry/backoff, timeout, quotas and idempotent publication. Recover worker death and database/broker interruption without duplicate terminal reports. |
| P1-05 | BE/SE | Run-specific directories and tenant object keys. Test concurrent tenants with identical labels, resource names and filenames; no overwrite or cross-tenant discovery. |
| P1-06 | SE/BE | AWS onboarding: backend workload identity, least-privilege target role and per-connection external ID where appropriate. Validate target account/trust/scope/revocation. Account ID alone grants nothing. |
| P1-07 | SE/BE | Azure onboarding: explicit Entra application/workload identity design plus customer Azure RBAC. Graph permissions are separate. Browser sign-in alone does not enable unattended collection. Test expiry, tenant mismatch and disconnect. |
| P1-08 | FE | Global tenant/run context on every view/export, including time, provider, account, evidence mode and completeness. No mixing historical and latest results across tabs. |
| P1-09 | RE/SE | Redacted logs, metrics, health/readiness, audit events and correlation IDs. Rate-limit costly endpoints; scope egress/probes and block SSRF/DNS-rebinding access to metadata/private services. |

**Gate:** adversarial tenant-boundary tests pass across API/files/jobs/logs/exports; worker-kill recovery works; revocation stops new access; backups restore in isolation. A shared static API key is insufficient for hosted multi-organization use.

## 7. P2: Scanners, Rules And Integrations

Each rule requires stable ID/version, service scope, permissions, inventory prerequisites, applicability, evidence schema, outcome logic, severity rationale, remediation, references, owner and tests. Framework mappings are reviewed interpretations, not compliance certificates.

| ID | Owner | Work and acceptance evidence |
| --- | --- | --- |
| P2-01 | DE/BE | Registry filters by provider/service/severity/framework/region/tags/rule. Deterministic order, dependency validation, cycle and invalid-filter tests. |
| P2-02 | BE | Shared provider clients: cache, pagination, regional discovery, concurrency bounds and retry budgets. Publish requested/observed/failed scope; test denied access, throttling and credential expiration. |
| P2-03 | DE/VR | Validate AWS/Azure separately with positive, negative, unknown, error and not-applicable fixtures plus authorized live cases. Report evaluated/skipped resources, not only finding count. |
| P2-04 | DE | Prioritize IAM/external trust, public exposure, storage/data protection, keys/secrets, logging, workload configuration, backups and governance against customer need and observable evidence. No arbitrary rule-count race. |
| P2-05 | BE/DE | Pinned Prowler OCSF/JSON and approved scanner import adapters. Preserve source IDs, severity, version and scope; imported findings must not masquerade as native CRIS evaluation. |
| P2-06 | BE | Versioned JSON evidence/export contracts; choose OCSF/ASFF/SARIF by use case. Round-trip fixtures preserve unknowns and provenance. |
| P2-07 | DE/SE | Muting is distinct from risk acceptance. Exceptions need owner, rationale, expiry and review. Hiding an alert cannot silently erase evidence or improve scores. |
| P2-08 | FE/BE | Resource inventory, searchable findings, evidence drill-down, permission gaps and run comparison. Ticket/webhook integrations have signatures, tenant scope and reliable delivery. |
| P2-09 | DE/VR | Provider capability matrix by service/evidence type. Promote AWS only for validated scope; similarly named AWS/Azure controls do not imply semantic parity. |
| P2-10 | PL/BE | Demand-gated GCP, Kubernetes and IaC prototypes via adapters. Container/SBOM imports can precede native image scanning. New providers inherit all security/evidence gates. |

**Gate:** complete metadata and negative-path tests for released rules; reproducible coverage and adjudicated false-positive results. Unavailable evidence never becomes a pass.

## 8. P3: CRIS-PQC Discovery

Start with cryptographic inventory and evidence quality, not a universal quantum-risk score. Use maintained cryptographic/discovery libraries rather than implementing algorithms.

| Source | Can establish | Cannot establish alone |
| --- | --- | --- |
| KMS/ACM/Key Vault and service configuration | Key/certificate metadata, lifecycle, associations and configured policy | Actual client negotiation or all application cryptography |
| Authorized handshake probe | Observed protocol/group where available, certificate chain and probe conditions | All clients, future sessions or backend traffic |
| Approved connection logs | Fields recorded for those sessions | Protection of unlogged traffic or whole-account readiness |
| Code/SBOM/CBOM import | Declared or statically observed dependencies/crypto references | Runtime reachability and production use |
| Owner/vendor evidence | Sensitivity, confidentiality lifetime, upgrade paths and commitments | Independent technical verification without corroboration |

AWS describes PQ TLS for KMS; apply that evidence narrowly, not to all AWS encryption. [AWS KMS documentation](https://docs.aws.amazon.com/kms/latest/developerguide/pqtls.html).

| ID | Owner | Work and acceptance evidence |
| --- | --- | --- |
| P3-01 | DE/SE | Crypto-asset/evidence model separates key exchange/KEM, certificate subject key, certificate signature, symmetric cipher and wrapping. Record scope, source and timestamp. |
| P3-02 | BE | Read-only AWS/Azure crypto metadata collectors with permission gaps and resource links. Never export private keys, secrets or decrypted customer data. |
| P3-03 | SE/DE | Probe allowlist, SNI, implementation version and client capabilities. Record classical/hybrid/PQ-supported/not-observed/unknown per dimension, not one secure badge. |
| P3-04 | BE/DE | Import approved handshake/software evidence; preserve trust, conflicting observations and temporal changes when deduplicating assets. |
| P3-05 | BE | Schema-validated CycloneDX CBOM with stable IDs/evidence links and pinned specification; independent parser interoperability test. |
| P3-06 | PL/VR | Owner-confirmed sensitivity, confidentiality lifetime, criticality, vendor readiness and effort. Unknown business context creates evidence requests, not fabricated high scores. |
| P3-07 | DE/FE | Migration backlog: dependencies, owners, vendor blockers, verification and rollout/rollback constraints. Distinguish claimed support from observed deployment. |
| P3-08 | VR/SE | Golden cases: TLS 1.3 classical; hybrid where supported; RSA certificate with hybrid exchange; unknown group; subject/signature mismatch; inaccessible inventory; misleading policy-only input. Independent crypto review. |

**Gate:** reproducible bounded AWS/Azure inventory and CBOM. TLS 1.3, AES-256 or a certificate algorithm alone must never imply application-wide PQ safety.

Discovery itself is established practice. The proposed research angle is **evidence-sufficiency-aware migration decisions across incomplete sources**. Align terminology with [NIST migration work](https://www.nccoe.nist.gov/applied-cryptography/migration-to-pqc), [CycloneDX CBOM](https://cyclonedx.org/capabilities/cbom/) and [NCSC migration guidance](https://www.ncsc.gov.uk/guidance/pqc-migration-timelines); recheck evolving guidance at release time.

## 9. P4: Testable Decision Benefits

| ID | Owner | Work and acceptance evidence |
| --- | --- | --- |
| P4-01 | VR/BE | Compare remediation now with gathering missing evidence first. Model investigation cost/uncertainty; retain an explainable baseline before probabilistic extensions. |
| P4-02 | BE/VR | Constraint-aware budget planning using a maintained solver: money, hours, dependencies, maintenance windows and mandatory controls. Report infeasibility and estimate sensitivity. |
| P4-03 | DE/BE | Graph edges link to evidence and distinguish observed/inferred/untested relationships. Heuristic paths are not proven exploits. |
| P4-04 | SE/BE | Versioned evidence receipts and verifier; select asymmetric signing, key custody and rotation deliberately. Preserve documented HMAC compatibility. Test tamper, wrong/revoked key and missing artifacts. |
| P4-05 | DE/FE | Claim expiry and revalidation: identify decisions relying on stale/changed evidence and create owner review tasks. |
| P4-06 | VR | Independent CE sufficiency review and clear manual-evidence marking; measure inappropriate auto-answering and corrections. IoMT/PQC need their own qualified reviewers. |
| P4-07 | VR/GT | Practitioner study with equal input scope, counterbalanced presentation, predefined tasks and appropriate baseline. Measure accuracy, time, priority quality and unsupported conclusions. |

| Hypothesis, not established result | Comparator | Measurement |
| --- | --- | --- |
| Evidence-gap-aware planning reduces unjustified actions | Same rules without sufficiency gating | Adjudicated errors, investigation effort and missed urgent issues |
| Constraint-aware planning is more feasible | Severity order and existing heuristic | Constraint violations, completed approved actions and effort error |
| Claim expiry exposes stale assurance sooner | Periodic static-report review | Detection time and unnecessary review burden |
| PQC evidence fusion improves reliable coverage | Policy-only and endpoint-only discovery | Verified assets, unsupported classifications and unknown rate |

Use a small formative study to refine the protocol, not establish population-wide effectiveness. CISO, cloud/security architect and SME CEO feedback is relevant but not equivalent to independent CE assessor or cryptography review. Recruit missing expertise; record criticisms and resulting changes as well as positive feedback.

For SIGI, recover original run IDs, dates, scope, approvals, source snapshots and remediation follow-ups. Organization authorization and environment provenance are separate: an authorized organization can supply production, staging or constructed-lab evidence. Do not relabel original artifacts or invent improvements. Publish details only with approval.

**Gate:** protocols, adjudication and uncertainty are reported; claims track measured outcomes. Sensitivity stability does not establish risk validity or reduced breach probability.

## 10. P5: Enterprise Operations And IoMT Pilots

| ID | Owner | Work and acceptance evidence |
| --- | --- | --- |
| P5-01 | SE/BE | Enterprise SSO/lifecycle, scoped service tokens and rotation; SCIM when buyers require it. Test deprovisioning, privilege change and break-glass audit. |
| P5-02 | RE | Supported local/private and hosted deployment profiles; demo is separate. Helm/IaC requires upgrade/rollback/secrets/backup tests. |
| P5-03 | RE/SE | Encryption, regional storage, retention/deletion and redaction. Test object/index/export deletion and backup lifecycle; document legal-hold exceptions. |
| P5-04 | RE | Load/soak/failure tests, quotas, backpressure and noisy-neighbor protection. Publish measured limits by worker size/provider scope. |
| P5-05 | FE/BE | Explicit MSP client grants, portfolio, schedules, expiry alerts, tickets and executive reports. All views/exports preserve tenant/run boundaries. |
| P5-06 | VR/DE | Expert-reviewed IoMT relationships, device/vendor imports and healthcare mappings. Default passive/cloud evidence; active device probing requires separate clinical authorization and safety review. |
| P5-07 | SE/GT | Procurement pack: architecture/data flows, subprocessors, privacy/DPA review, penetration-test summary, support and incident process. Obtain legal review for contractual/regulatory claims. |
| P5-08 | GT/VR | Paid or formally scoped partner pilots with baseline, success criteria, time-to-value and support cost. Separate willingness to pay from researcher goodwill. |

Proposed targets to ratify before testing, **not current SLAs**:

- 99.9% monthly hosted API availability, separate from scan completion.
- Metadata API p95 under one second on a declared workload; scans/large exports asynchronous.
- At least 10 isolated workspaces and 20 queued scans in the initial benchmark, with explicit worker concurrency and no lost terminal states/leakage. Expand against pilot demand.
- Initial restore-drill RPO <=24 hours and RTO <=4 hours; stricter contracts require cost/architecture changes.
- No unresolved critical/high authentication or tenant-isolation findings at launch; other high risks require explicit owner disposition, never silent bypass.

**Gate:** independent security assessment, recovery exercise, supported upgrade and scoped pilot criteria met. Platform security tests do not validate healthcare-specific claims.

## 11. P6: GA And Sustainable Growth

- Publish GA scope, support matrix, measured limits, migration guides, vulnerability policy and escalation. Keep experimental modules visibly labelled.
- Release signed digest-addressable artifacts, SBOMs and provenance. Document verification, trust roots and revocation.
- Publish module validation summaries and limitations; maintain schema/rule-pack/provider compatibility policies.
- Add commercial subscriptions with entitlement isolation, accounting and billing-failure handling only when needed. Price against buyer research and actual operating costs.
- Fund maintenance and review strategy quarterly. Retire unsupported rules explicitly.
- Gate broader providers, compliance packs, air-gapped deployment and advanced integrations on customers, maintainers and validation capacity.

## 12. DevSecOps Standard

Borrow OpenShield release discipline and Prowler component-aware CI, not their workflow count.

| Layer | Required outputs | Phase |
| --- | --- | --- |
| PR | Backend/frontend tests, lint/types, schema/metadata checks, migrations, docs/assets, secrets, dependencies and licenses | P0-P2 |
| Security-sensitive PR | Independent review for auth, isolation, credentials, probes, rule semantics and release workflows | P1+ |
| Workflow security | Least privilege, pinned action revisions, actionlint/zizmor, protected environments and no secrets for untrusted fork code | P0-P1 |
| Build | Locks, clean wheel install, nonroot container smoke test, vulnerability scan, SBOM and digests | P0-P2 |
| Integration | PostgreSQL/RLS, recovery, provider denial/throttling and browser tests; full regression alongside changed-path selection | P1-P2 |
| Release | Protected lineage, signing/provenance/verification, upgrade/rollback and staged approval | P2-P5 |
| Runtime | SLOs, redacted telemetry, cost/queue alerts, restore/incident drills, retention and revocation | P1-P5 |

Publish coverage numerator/denominator. Start from measured baseline; target >=80% statement coverage for critical maintained modules, plus branch/scenario tests for security decisions. A percentage cannot replace isolation or rule-correctness tests. Flaky-test quarantine needs owner and expiry; required checks cannot silently become optional.

## 13. OWASP And OpenSSF

### OWASP pathway

Propose a vendor-neutral **CRIS evidence-assurance core**, not commercial-suite endorsement. Assess overlap/community need, including OpenShield. Prepare maintained release, reproducible example, governance, licenses, public issues and scope.

The current policy requires foundation approval, 2-5 recognized leaders who are members, open participation and project-site obligations. Source/artifacts need an OSI-approved license; documentation has separate licensing requirements. Review contributor agreements, hosting and branding before application. Corporate sponsorship is distinct from project leadership. Do not add affiliation branding before approval. [OWASP project policy](https://owasp.org/legal/project).

Owner GT/PL; prepare from P0, apply when real maintainer capacity and P2-quality artifacts exist. A repository transfer requires an explicit decision; this roadmap does not execute one.

### OpenSSF progression

| Track | Work | Gate |
| --- | --- | --- |
| Best Practices Passing | License, governance, contribution/disclosure, documentation and secure development/testing | Honest criterion register with verifiable links |
| Silver | Stronger governance/continuity, testing/security requirements, accessibility and reproducibility | Actual maintainer access and measured practices, not templates alone |
| Gold | Higher assurance and sustained mature engineering | Reassess after GA; no promised achievement date |
| OSPS Baseline | Control-to-evidence mapping | Track separately from badge status |
| Scorecard | Automated repository-risk checks | Remediate findings; score is not product certification |

Official [Passing](https://www.bestpractices.dev/en/criteria/0), [Silver](https://www.bestpractices.dev/en/criteria/1) and [Gold](https://www.bestpractices.dev/en/criteria/2) criteria govern applications. [OSPS Baseline](https://baseline.openssf.org/) and [Scorecard](https://scorecard.dev/) are separate tools. None certifies cloud findings, PQ safety or regulatory compliance.

## 14. Market, Grants And Competitions

Suggested positioning: **CRIS turns cloud and cryptographic evidence into reviewable security decisions: what is known, what needs verification, and what can be improved within operational constraints.**

Three demonstrations, one platform:

1. SME/MSP: scoped assessment, clearly marked manual-evidence gap, affordable plan and follow-up scan.
2. Enterprise/PQC: metadata plus observed cryptography, policy-only blind spot, vendor dependency and accountable migration plan.
3. Healthcare: cloud-connected system evidence and explicit unresolved device/clinical questions, with domain review.

Maintain an application pack: reproducible release/demo, architecture/security brief, competitor analysis using independent buyer criteria, evaluation protocol/results, IP ownership, budget/work packages, consented letters and commercialization assumptions. Papers and positive feedback support credibility but do not replace outcome evidence.

### Opportunity register: checked September 2026

| Route | Status/constraint | Action |
| --- | --- | --- |
| Innovate UK/UKRI | Eligibility, co-funding and deadlines vary by call | GT reviews [official funding finder](https://www.ukri.org/opportunity/) monthly and records dated go/no-go decisions |
| Cyber scale in critical sectors | 2026 call closed 10 June | Historical example; monitor successors and recruit a real end-user partner. [Official call](https://www.ukri.org/opportunity/contracts-for-innovation-cyber-scale-in-critical-sectors/) |
| CyberASAP | Year 10 Phase 1 closed 11 February 2026; academic-led route | Eligible institution/TTO and IP review needed; recheck future terms. [Call](https://apply-for-innovation-funding.service.gov.uk/competition/2376/overview/1b9b9265-ca4b-4f8c-a0c2-577cb8713642) |
| NCSC for Startups | Official page says programme no longer running | Do not plan an application; examine current alternatives separately. [NCSC archive](https://www.ncsc.gov.uk/section/ncsc-for-startups/overview) |
| RSAC Innovation Sandbox | 2026 concluded; future cycle/terms need checking | Prepare pitch/traction/demo; investment is not a grant. [Programme](https://www.rsaconference.com/rsac-programs/innovation/innovation-sandbox) |
| Defence innovation | Historical DASA pages do not prove an active call | Verify current official route, security constraints and end-user problem first |
| Quantum funding | PQC software is not automatically eligible | Check scope; justify research rather than keyword matching |

No open award or eligibility is promised here. Recheck official terms before applying. Separate routine product engineering from experimental grant work; never double-charge work across awards.

Research packages for suitable calls: uncertainty-aware investigation/remediation planning, evidence-grounded PQC migration, and independently assessed healthcare evidence sufficiency. Each needs baseline, research question, qualified partner, data-access plan and exploitation route.

## 15. First Implementation Backlog

Create small reviewed PRs with tests, not one platform rewrite.

| Order | Issue | Done when |
| --- | --- | --- |
| 1 | P0-01: docs CI | SVG links are checked; failed jobs cannot produce success summaries |
| 2 | P0-02/03: installation/container | Complete mock run from installed assets; shell/stop/nonroot behavior tested |
| 3 | P0-04: registry parity | All baseline active controls have validated metadata/stable IDs |
| 4 | P0-06: whole-product CI | Backend/frontend tests/builds and supported runtimes checked |
| 5 | P0-05: threat model | Trust boundaries, deployment restrictions and security tests defined |
| 6 | P1-05: run namespaces | Concurrent assessments cannot overwrite reports; historical migration tested |
| 7 | P1-01/02: workspace API | Positive/negative identity and authorization tests before exposure |
| 8 | P1-03/04: persistence/workers | Migrations, leases, cancellation and crash recovery demonstrated |
| 9 | P2-03/09: provider release | Support labels backed by validation including errors/unknowns |
| 10 | P3-01/08: PQC contracts | Golden fixtures reject misleading TLS/certificate shortcuts before live collectors |

Each issue records owner, dependencies, claim/threat impact, test plan, evidence and release decision. Mark complete only when those artifacts exist. A document, mockup or fixture-only collector is not an enterprise release.

## 16. Deferrals And Review Rules

### Delivery risks

| Risk | Early warning | Response and owner |
| --- | --- | --- |
| Three modules exceed maintainer capacity | Core security work repeatedly displaced by module demos | PL reduces scope; share infrastructure and keep PQC/IoMT experimental until staffed |
| Weak data access or ground truth | More fixtures but no independently adjudicated cases | VR secures scoped partner agreements and reviewers before expanding effectiveness claims |
| Multi-tenant breach | Any cross-tenant artifact, job or query access | SE blocks hosted release until fixed and independently retested |
| Provider/API drift | Permission gaps or silent empty inventories increase | DE pins compatibility fixtures, alerts on coverage loss and publishes scope limitations |
| Cloud and CI costs outgrow pilots | Increasing per-scan cost or repeated full inventory calls | RE measures costs, caches within evidence-freshness limits and enforces budgets/quotas |
| Supply-chain/license ambiguity | Rule/code imports without origin or notices | SE/PL blocks import pending provenance and license review |
| Funding changes | Closed call or incompatible applicant/IP terms | GT maintains dated eligibility checks; core delivery must not depend on an unawarded grant |
| Premature security/compliance claims | Marketing outpaces validation or badge evidence | PL requires capability-manifest and reviewer evidence before publishing claims |

### Scope exclusions

- No attempt to match every Prowler provider or commercial CNAPP feature at once.
- No microservice/repository split solely for branding.
- No native AI/LLM scanner merely because another tool has one.
- Optional AI explanations remain source-bound/non-authoritative, with prompt-injection and tenant-leakage defenses before use.
- No default automated remediation. Future writes require separate identity, approval, preview, rollback and impact controls.
- No default active medical-device scanning or exploitation.
- No custom crypto implementation or universal quantum-risk score.
- No advance claim of badges, OWASP affiliation, funding eligibility or enterprise certification.

Review monthly for execution and quarterly for strategy. Record changed assumptions, removed work, outcomes and costs here. Supporting designs link to this file rather than introducing competing dated roadmaps.
