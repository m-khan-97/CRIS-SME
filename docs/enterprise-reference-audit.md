# Enterprise Reference Repository Audit

Inspection dates: 20-21 September 2026. Purpose: inform the [canonical CRIS roadmap](roadmap.md), not rank products by a self-selected feature matrix.

## Scope And Method

This review inspected local source, configuration, tests, documentation, rule metadata, deployment files and CI/release workflows in CRIS, Prowler and OpenShield. It followed representative paths through collection, evaluation, persistence, authorization, job execution and artifact publication. It is a source-based architectural assessment, not an exhaustive vulnerability assessment or proof that every workflow currently passes.

No cloud resources were provisioned or scanned, no customer credentials were read, no external repositories were changed, and no commercial service behavior was tested. Third-party test suites and deployment environments were not executed. Repository controls such as GitHub branch protection cannot be established from YAML alone.

| Input | Inspection identity | Important qualification |
| --- | --- | --- |
| CRIS-SME | Baseline Git revision `ffa4ead`; existing local edits preserved | Research/output changes already in the worktree were not rewritten for this audit |
| Prowler | `03cb59c20ddbd7de490b6916ecc04377d1c91b5e` | Findings concern this local checkout, not every hosted product or release |
| OpenShield | Supplied `openshield-main` directory; Git revision unavailable | Snapshot, not a verified upstream release; README SHA-256 `09ff9cd740995907421ba053ca7011bc044b52a60ee6429b497a14e9e9f10d75` identifies the inspected README only |

Source counts provide scale, not effectiveness:

| Measure | CRIS | Prowler | OpenShield |
| --- | --- | --- | --- |
| Rule/content inventory | 36 catalog entries; 5 newer metadata entries | 1,616 provider `*.metadata.json` files | 127 `scanner/rules/az_*.py` files and 127 matching CLI playbook files |
| Provider structure | Azure/AWS and mock paths | 23 `*_provider.py` files in provider directories | Azure-focused collector/rule structure |
| CI workflows | 7 | 55 `.yml` workflows | 11 workflows |
| Rule outcome migration | Existing evidence-sufficiency model, incomplete metadata migration | Structured check metadata and scan results | Only one rule file contains a top-level `evaluate` definition; legacy adapter still matters |

Counts exclude semantic equivalence and do not prove native/live coverage. A provider wrapper is not the same as a mature cloud integration. The OpenShield AST count does not detect imported aliases or dynamically supplied evaluators. Its README's lower advertised rule count also illustrates documentation drift.

Verification in CRIS on 21 September: `PYTHONPATH=src pytest -q` completed with **327 passed**; `npm test` in `frontend/console` completed with **36 passed** in one test file. All 81 local Markdown links checked across the ten edited/added documents resolved, and `git diff --check` passed. These checks do not validate third-party suites, hosted isolation, live provider completeness, real browser workflows or container runtime. The known Mermaid-only CI assertion remains a P0 task; this is not a claim that the entire CI pipeline passes.

## Executive Findings

1. **CRIS should not compete principally on check count.** Prowler's breadth, metadata and integrations are valuable sources of input. CRIS can normalize scanner evidence and concentrate on sufficiency, decisions, constraints and accountable follow-up.
2. **Enterprise readiness is mostly a platform/security problem now.** The local API, file artifacts and process model are the first constraints, not lack of another dashboard page.
3. **OpenShield has useful release and governance mechanisms**, particularly explicit unknown/error handling, OIDC tests, job recovery, supply-chain evidence and an honest badge-evidence register.
4. **Useful architecture does not make every rule sound.** OpenShield's PQC inference shortcuts should become negative test cases, not copied logic.
5. **CRIS already has many proposed features in partial form.** The roadmap should finish and validate registry, exports, runner, decision and evidence features instead of marking them unbuilt or claiming complete maturity.

## 1. Prowler: Patterns Worth Adopting

Paths below are relative to the inspected Prowler root. The [pinned tree](https://github.com/prowler-cloud/prowler/tree/03cb59c20ddbd7de490b6916ecc04377d1c91b5e) provides reviewable upstream references.

| Area | Inspected evidence | Strength | CRIS adaptation |
| --- | --- | --- | --- |
| Rule schema | `prowler/lib/check/models.py`; sample S3 public-access metadata | Typed metadata, resource categorization, references and remediation | Complete CRIS metadata across active controls; preserve sufficiency and decision fields |
| Registry and filtering | `prowler/lib/check/checks_loader.py` | Provider/service/check/severity/compliance selection and aliases | Validate filters/dependencies and publish exact evaluated scope |
| Provider abstraction | `prowler/providers/common/provider.py`; AWS `lib/service/service.py` | Provider/service ownership and shared collection | Cache expensive inventory, bound concurrency and track permission gaps |
| External tools | `prowler/lib/check/tool_wrapper.py`, `external_tool_providers.py` | Adapters extend coverage without rewriting every scanner | Versioned imports first; retain source identity and rule semantics |
| Scan orchestration | `prowler/lib/scan/scan.py`, scan filters, mutelist/timeline code | Reusable scan concepts, selection and lifecycle | Finish CRIS runner boundaries without losing deterministic report generation |
| Outputs | Output modules for OCSF/ASFF/CSV/HTML/compliance | Interoperability with operational security tooling | Harden existing CRIS OCSF/SARIF/CSV rather than rebuilding exports |
| Tenant isolation | `api/src/backend/api/rls.py` | Enabled/forced RLS, missing tenant context denied | Database defense in depth with runtime role tests, plus blob/cache/job isolation |
| Authorization | `api/src/backend/api/models.py`, `rbac/permissions.py`, authentication/middleware | Tenant memberships, scoped keys and provider groups | Explicit cloud-connection grants, auditor/operator roles and negative tests |
| Isolation tests | `api/tests/integration/test_rls_transaction.py`, `test_tenants.py`, `test_authentication.py` under backend | Tests cover security boundaries beyond UI navigation | Reproduce attack cases, not framework-specific code blindly |
| Durable tasks | `api/src/backend/tasks/jobs/scan.py`, `orphan_recovery.py` | Scheduling/recovery separated from request handling | Leases, heartbeat, cancellation, idempotent publication and crash tests |
| Recovery caution | `orphan_recovery.py` | Avoids treating uncertain task state during broker failure as proof the task is dead | Prevent duplicate scans/publish after transient infrastructure faults |
| Graph context | `tasks/jobs/attack_paths/` under backend | Provider-specific graph processing and cleanup | Start with evidence-backed edges; graph storage only when scale demands it |
| UI and MCP | UI role/onboarding/provider workflows; separate MCP server/tests | Operational journeys and structured integration surfaces | Test whole onboarding-to-report workflows; authorize MCP like the API |

### DevOps and release lessons

- `.github/workflows/ci-zizmor.yml`: pinned actions, constrained job permissions and runner egress hardening are concrete safeguards to adapt.
- `sdk-security.yml`: lock-aware vulnerability checks and static analysis should complement, not replace, unit/integration tests.
- `ui-tests.yml`: changed-path selection saves CI time; always retain global authentication/isolation regression gates and periodic full runs.
- SDK/API/UI/MCP container workflows enable SBOM and maximum build-provenance output. CRIS should verify provenance consumers and release lineage, not only attach files.
- Action linting, secrets scanning, component CodeQL, container checks and Helm validation cover different failure classes.
- Component lockfiles make releases reviewable. Updating locks needs explicit upgrade/testing policy.

Do not copy the entire Django/Celery/Next.js stack or all workflows into CRIS. Framework migration, graph databases and service proliferation need local justification. Prowler source is not evidence that commercial edition features, performance or every provider will match CRIS requirements.

## 2. OpenShield: Patterns Worth Adopting

Paths below are relative to the supplied OpenShield snapshot. They are not links to an assumed remote revision.

| Area | Inspected evidence | Strength | CRIS adaptation |
| --- | --- | --- | --- |
| Explicit outcomes | `scanner/evaluation.py` | PASS/FAIL/UNKNOWN/ERROR/NOT_APPLICABLE with reasons | Keep failed collection and unavailable evidence visible separately from compliance |
| Legacy migration | `scanner/engine.py` | Unmigrated rules can report `LEGACY_RULE_NOT_MIGRATED` rather than treating silence as pass | Define compatibility behavior when introducing CRIS registry/evaluation contracts |
| OIDC | `api/auth.py`; `tests/test_oidc_auth.py`, `test_auth.py` | Issuer/audience/JWKS validation, role mapping, fail-closed configuration | Adopt standard validation patterns with tenant-specific negative tests |
| Scope authorization | `tests/test_subscription_authorization.py` | Subscription permission boundary treated as testable behavior | Test cloud-account scope separately from login and display labels |
| Job claims/recovery | `api/models/finding.py`; `scanner/worker.py` | PostgreSQL `FOR UPDATE SKIP LOCKED`, stale recovery and bounded attempts | Consider a small durable queue before a larger task stack |
| Persistence | Alembic migrations | Explicit schema evolution | Test historical report import and supported upgrade/rollback |
| API operations | `api/observability.py`, `rate_limit.py`, `validation.py` | Limits, input validation and observability are product concerns | Set quotas, redaction and readiness from P1, not after launch |
| Azure inventory | `scanner/arg_inventory.py`, `scanner/azure_client.py` | Shared resource inventory and wider Azure evidence sources | Reuse collection results, publish query scope and permission errors |
| Remediation references | `playbooks/cli/fix_az_*.sh` | One discoverable playbook per rule | Validate commands and scope; keep default CRIS export non-executing |
| SIEM delivery | `sentinel/ingest.py` and KQL assets | Payload validation, bounded upload and operational queries | Build versioned outbound adapters; recheck provider API lifecycle before copying |
| AI grounding | AI/RAG code and grounding tests | Tests distinguish sources and generated content | Optional narrative only; protect against hostile evidence/prompt injection |
| Governance | Maintainer/support/security docs and `docs/openssf-silver-evidence.md` | Criterion-level evidence and candid remaining work | Maintain a real evidence register; do not inherit another project's badge claims |

### Release engineering worth adapting

The inspected `.github/workflows/ci.yml` includes pinned actions, hash-locked Python dependencies, rule/framework/playbook validation, lint/format, secrets/static/dependency scanning, SBOM generation, container scanning and runtime smoke checks. It also covers frontend checks and a bundle token-leak canary. Final required-job aggregation checks outcomes rather than assuming success.

The release workflow and `scripts/release_integrity.py` check release lineage, prepare deterministic source archives, create checksum/SBOM artifacts and publish/verify attestations. These are stronger patterns than a release tag followed by an unverified upload.

Limits to retain in CRIS's adaptation:

- An 80% coverage threshold scoped to API/scanner is not 80% of the entire product.
- Tests that skip without external AI credentials do not establish live AI performance.
- A deterministic source archive is not the same as a bit-for-bit reproducible container, especially with floating base tags or changing OS packages.
- A branch policy requiring a particular development branch is not inherently better than protected-main PR workflow.
- Badge documentation and README badges were inspected as repository claims, not independently certified current badge status.

## 3. PQC Findings: Do Not Copy These Inferences

### Minimum TLS policy is not negotiated key exchange

`scanner/rules/az_pqc_001.py` checks App Service `min_tls_version` against 1.3 while naming the finding classical key exchange. Its risk object sets public exposure and harvest-now-decrypt-later exposure true and assigns score 10 without observing those properties.

The inspected input can support a finding about minimum protocol policy. It cannot by itself establish negotiated group, internet reachability, sensitivity or whole-service PQ status. In CRIS, configured policy, supported capability and observed connection must be distinct records. TLS 1.3 can still use classical key exchange.

### Algorithm inventory is not validated migration priority

`scanner/rules/az_pqc_002.py` usefully inventories RSA/EC key metadata, but its fixed risk/exposure assumptions do not establish how the key is used or the confidentiality lifetime of protected information. Keep inventory; require usage and owner context before asserting impact or ordering migration.

### Certificate subject key is not certificate signature

`scanner/rules/az_pqc_003.py` labels non-PQ certificate signatures but reads `policy.key_properties.key_type`. That describes a key policy, not the actual issuer signature algorithm of the certificate. CRIS should parse certificate material using a maintained library and distinguish the subject key, issuer signature and negotiated exchange.

These findings concern the inspected implementations, not the merit of PQC discovery. They motivate the negative fixtures and evidence model in roadmap P3. [AWS's scoped KMS PQ TLS documentation](https://docs.aws.amazon.com/kms/latest/developerguide/pqtls.html) and [NIST migration work](https://www.nccoe.nist.gov/applied-cryptography/migration-to-pqc) are better foundations than a TLS-version shortcut.

## 4. CRIS Gaps And Immediate Risks

| Priority | Observation and evidence | Consequence | Roadmap |
| --- | --- | --- | --- |
| Blocker for hosting | [Local runner](../src/cris_sme/api/local_runner.py) uses local trust, not demonstrated tenant authentication/isolation | Do not expose as multi-tenant SaaS | P0-05; P1-01/02 |
| Blocker for concurrency | Shared output/report discovery and subprocess execution in local runner | Cross-run overwrite/discovery and unreliable lifecycle under concurrency | P1-03/04/05 |
| Incomplete persistence | [Run repository](../src/cris_sme/api/run_repository.py) persists process state, while artifacts remain file-backed | Restart persistence is not transactional tenant-aware report storage | P1-03 |
| CI regression | [Quality workflow](../.github/workflows/reusable-python-quality.yml) still requires a Mermaid block in README after SVG replacement | Documentation check can reject otherwise valid changes | P0-01 |
| CI reporting | Same workflow's always-running summary includes unconditional success wording | A failed run can produce misleading summary text | P0-01 |
| Packaging | [Dockerfile](../Dockerfile) copies source but not root policy `data/`; [catalog](../src/cris_sme/controls/catalog.py) defaults to a relative data path | Clean-image policy loading needs full execution validation, not build-only confidence | P0-02 |
| Process/runtime | [Entrypoint](../docker/entrypoint.sh) uses `/bin/sh` and `wait -n`; image is Debian-derived | Shell compatibility and process shutdown need runtime proof | P0-03 |
| Content migration | [Catalog](../data/control_catalog.json) has 36 entries; [metadata v2](../data/control_metadata_v2.json) has five | Registry existence does not mean all rules use the richer contract | P0-04 |
| Narrow quality gates | Limited lint/type scope; no demonstrated complete frontend PR gate in inspected workflow | Whole-product regression coverage is incomplete | P0-06 |
| Integrity terminology | [RBOM implementation](../src/cris_sme/engine/rbom.py) uses HMAC-SHA256 | Shared-secret authenticity is not public verification | P4-04 |
| Incomplete runner boundary | [Assessment runner](../src/cris_sme/engine/assessment_runner.py) covers core phases; additional report generation remains outside | Recovery/progress cannot assume every artifact stage is durable | P1-04 |
| PQC evidence gap | [Public exposure](../src/cris_sme/engine/public_exposure.py) captures TLS/certificate evidence, not a full PQ discovery model | Do not reuse existing TLS display as PQ readiness | P3 |

Container observations here are source-derived risks, not claims that a container was built and tested during this review. They are explicitly acceptance-test tasks. Existing local worktree edits are not evidence of their deployment.

## 5. Capabilities To Finish Rather Than Rebuild

CRIS already contains registry/filtering, asset/evidence models, provider contracts, summaries, lifecycle/muting, OCSF/SARIF/CSV, remediation reference export, graph context, MCP queries and persona views. Existing source presence does not establish enterprise maturity, but ignoring it would duplicate work.

| Existing area | Maturity work needed |
| --- | --- |
| Evidence sufficiency and provenance | Complete rule adoption; freshness, partial-scope handling and independent adjudication |
| Decision ledger and exceptions | Durable append-oriented events, authorization, approval, expiry and historical consistency |
| Muting and adjusted scores | Visible raw versus adjusted posture; test whether operational suppression is being mistaken for risk reduction |
| Budget simulation | Explicit effort assumptions, dependencies, constraints and comparative evaluation |
| Compliance/CE outputs | Versioned questionnaires, manual-evidence boundaries and assessor review |
| Graph context | Evidence-backed relations, inference labels and reproducible validation |
| Export/MCP surfaces | Tenant-aware authorization, schema compatibility and privacy tests |
| Organization/run selectors | Authoritative server-side scoping across every query and export |
| IoMT research | Device/cloud evidence separation and qualified healthcare review |

## 6. Adopt, Adapt, Defer

| Decision | Items |
| --- | --- |
| Adopt as engineering practices | Typed rule metadata; explicit unknown/error; least privilege; negative auth tests; dependency locks; signed release verification; evidence-based governance |
| Adapt to CRIS | Provider clients, durable job patterns, resource inventory, scanner imports, operational UI, SIEM/ticketing, component-aware CI |
| Preserve and strengthen | Sufficiency, provenance, budget decisions, replay, claim boundaries, local/private assessment and research reproducibility |
| Do not copy without validation | PQC inference shortcuts, fixed risk scores, framework mappings, remediation scripts and claims of live coverage |
| Defer until demand | Large service split, dedicated graph database, every cloud provider, native image/AI scanning and write-capable auto-remediation |

## 7. Validation And Market Implications

Use independent evaluation dimensions: deployment/authentication, tenant safety, recovery, evidence completeness, rule precision, permission handling, interoperability, maintainability, user decision outcomes and operating cost. These are meaningful buyer concerns, not simply the features CRIS happens to implement.

For experimental comparisons, align cloud scope, permissions, source snapshots, rule intent and tool versions. Adjudicate disagreements; additional findings are not automatically true positives. Compare native scanner output and normalized/imported CRIS views without conflating different collection coverage with better reasoning.

Commercial differentiation remains a hypothesis until tested. Promising directions are investigation-versus-remediation choice, constraint-aware planning, stale-claim detection and evidence-aware PQC migration. Their roadmap entries specify baselines and measurements.

OWASP participation, OpenSSF badges and grants are separate pathways. None replaces independent product/security validation. The [roadmap](roadmap.md) contains current-source links, eligibility caveats, owners and application prerequisites.

## 8. Audit Limitations And Follow-Up

- Broad representative inspection is not line-by-line review of every check, frontend screen or workflow.
- No live AWS/Azure effectiveness benchmark or reproduction of Prowler/OpenShield deployments was attempted.
- No promise is made about commercial product parity or uninspected upstream changes.
- No complete legal license opinion or regulatory assessment is supplied; imported components require their own review.
- Organization identity, environment source, authorization and evaluation independence must remain separate in future evidence packs.
- Next technical work should begin with roadmap P0 rather than adding more unvalidated feature claims.
