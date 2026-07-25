# Prowler Comparison and CRIS-SME Ideas

This note compares the local Prowler repository at `/home/muhammad-ibrahim/Github/prowler` with CRIS-SME. The goal is not to turn CRIS-SME into another scanner. Prowler is strongest as a broad cloud security scanning platform. CRIS-SME is strongest as an evidence-to-decision governance and assurance platform for SMEs.

The useful path is to borrow Prowler's platform mechanics while preserving CRIS-SME's product identity: deterministic risk governance, evidence honesty, decision provenance, assurance outputs, and SME-specific communication.

## Executive Read

Prowler is a high-breadth open cloud security platform. It has thousands of provider-specific checks, metadata-rich check definitions, mature provider authentication, resource/finding persistence, compliance packs, CLI filtering, API models, UI views, muting, integrations, and multiple output formats.

CRIS-SME is a high-context decision system. It collects or accepts normalized cloud posture, evaluates a curated control set, scores findings with confidence and exposure, generates compliance mappings, lifecycle state, assurance artifacts, evidence snapshots, replay summaries, decision ledgers, Cyber Essentials outputs, insurance packs, and remediation simulations.

The strategic recommendation is:

- Borrow Prowler's metadata-first check architecture, registry, filtering, provider/session abstractions, resource/finding persistence ideas, output interoperability, compliance pack validation, and operational UI structure.
- Do not copy Prowler's positioning, dependency footprint, scanner breadth race, or generic CSPM user journey.
- Keep CRIS-SME as the governance layer that explains what evidence means, what decisions are defensible, what risk is accepted, and what an SME should do next.

## What Was Inspected

CRIS-SME areas inspected:

- `README.md`
- `src/cris_sme/main.py`
- `src/cris_sme/models/finding.py`
- `src/cris_sme/models/cloud_profile.py`
- `src/cris_sme/controls/catalog.py`
- `src/cris_sme/controls/network_controls.py`
- `src/cris_sme/collectors/providers/base.py`
- `src/cris_sme/engine/provider_contracts.py`
- `src/cris_sme/api/local_runner.py`
- `docs/saas-api-evolution.md`
- `docs/finding-lifecycle.md`
- `docs/product-strategy.md`

Prowler areas inspected:

- `README.md`
- `pyproject.toml`
- `prowler/__main__.py`
- `prowler/lib/check/models.py`
- `prowler/lib/check/check.py`
- `prowler/lib/check/checks_loader.py`
- `prowler/lib/scan/scan.py`
- `prowler/lib/outputs/finding.py`
- `prowler/providers/common/provider.py`
- `prowler/providers/aws/aws_provider.py`
- `prowler/providers/azure/azure_provider.py`
- Azure storage public access check metadata and implementation
- `api/src/backend/api/models.py`
- `ui/app/(protected)/*`
- `ui/lib/compliance/threatscore-calculator.ts`
- `docs/images/products/prowler-app-architecture.mmd`
- `docs/tutorials/prowler-app-lighthouse-ai-chat.mdx`

Measured local Prowler catalog size:

- AWS service check metadata files: 608
- Azure service check metadata files: 169
- All provider service check metadata files: 1416
- Compliance JSON files: 102

## Architectural Comparison

| Area | Prowler | CRIS-SME | Idea for CRIS-SME |
| --- | --- | --- | --- |
| Product shape | Broad scanner and cloud security platform | Evidence-to-decision governance platform | Keep CRIS as the assurance layer, not a scanner clone |
| Core unit | Provider-specific check | Curated control finding | Add metadata-rich controls without losing curated semantics |
| Input model | Provider sessions and live service clients | Normalized `CloudProfile` and Azure live collector | Add resource-level evidence records below the profile |
| Execution | CLI, SDK `Scan`, API worker, Celery | Monolithic deterministic `main.py` pipeline | Introduce an `AssessmentRunner` with phases and progress events |
| Check metadata | Per-check JSON with severity, resource type, risk, remediation, categories, compliance | Central control catalog plus code evaluators | Create CRIS control metadata v2 with risk, remediation code, evidence needs, provider support |
| Check loading | Dynamic registry, filtering by service, check, severity, compliance, category, resource group | Fixed evaluator sequence | Add control registry and filters by control, domain, severity, framework, provider, evidence requirement |
| Provider abstraction | Rich provider classes handle auth, identity, config, scope, output, muting | Light adapter normalizes raw profile to `CloudProfile` | Expand provider contracts for identity, scopes, permissions, resources, evidence, and test connection |
| Resource model | Persistent resources and finding-resource mappings | Findings have `resource_scope`; profile is aggregate-heavy | Add normalized `Asset` and `AssetEvidence` model |
| Finding model | Operational security finding with provider/resource fields and raw output | Risk governance finding with confidence, exposure, sensitivity, effort, mappings | Preserve CRIS fields, add resource UID, first/last seen, source evidence IDs |
| Lifecycle | Muting and API persisted finding state | CRIS lifecycle and exception semantics | Borrow operational mute UX, keep governance approvals and expiry |
| Compliance | Large external compliance pack catalog | Smaller curated mapping set | Externalize and validate CRIS compliance packs |
| Outputs | CSV, JSON, OCSF, ASFF, SARIF, HTML, compliance outputs, integrations | JSON, HTML, dashboard, appendix, insurance, action plan, simulation | Add OCSF/SARIF interoperability while keeping CRIS packs canonical |
| API/SaaS | Django models for providers, scans, resources, findings, summaries | Local runner and SaaS evolution doc | Use Prowler models as reference for CRIS SaaS persistence |
| UI | Overview, findings, resources, compliance, providers, scans, attack paths, mutelist, integrations | Demo console and static dashboard | Adapt routes around SME roles and assurance workflows |
| AI | Lighthouse chat via MCP tools | AI narrator constrained by deterministic outputs | Later add CRIS MCP over evidence, claims, and decisions |

## Prowler Strengths Worth Borrowing

### 1. Metadata-First Checks

Prowler separates check metadata from check execution. Each check has structured metadata for provider, check ID, service, resource type, severity, category, description, risk, remediation, related URLs, compliance, and aliases. The check code stays small and focused.

CRIS-SME currently has a simpler central catalog and evaluator functions. That works for a curated research prototype, but as the project grows it will become harder to filter, validate, document, and expose controls through an API.

CRIS-SME should introduce a richer `ControlDefinition` model and control metadata schema while keeping deterministic evaluator code.

### 2. Registry and Filtering

Prowler can decide what to run by check ID, service, severity, category, compliance framework, resource group, and aliases. This is useful for CLI, UI, API, scheduled scans, demos, and scoped assessments.

CRIS-SME should add control loading by:

- `control_id`
- domain or category
- severity
- compliance framework
- provider support
- evidence requirement
- resource group
- assurance claim

This would let CRIS answer questions like "run only Cyber Essentials Azure controls" or "run controls whose evidence is stale".

### 3. Programmatic Scan Runner

Prowler has an SDK-style `Scan` class that yields progress and findings. CRIS-SME's `main.py` is currently doing orchestration, artifact generation, scoring, lifecycle, dashboard, and exports in one long flow.

CRIS-SME should introduce an `AssessmentRunner` that yields structured phases:

- collect evidence
- normalize profile
- evaluate controls
- score findings
- map compliance
- assess evidence sufficiency
- update lifecycle
- build decisions
- generate artifacts

The CLI and local API can then become thin wrappers around the runner.

### 4. Provider Responsibilities

Prowler providers handle identity, sessions, auth methods, regions or subscriptions, config, scope, output shape, mutelist args, and provider-specific reporting.

CRIS-SME's current provider adapter is intentionally light. For Azure-first live collection and later AWS/GCP support, CRIS needs a middle ground:

- provider identity
- auth/session setup
- permission checks
- scopes such as subscription, tenant, region, account, project
- evidence freshness
- resource enumeration
- evidence collection capability matrix
- provider limitations
- output normalization

This aligns well with the existing CRIS provider evidence contracts.

### 5. Resource-First Persistence

Prowler persists resources separately from findings and maps findings to resources. This unlocks resource pages, repeated finding history, attack paths, blast-radius views, and summaries.

CRIS-SME currently uses aggregate profile fields and `resource_scope`. That keeps assessment deterministic but limits drilldown.

CRIS-SME should add normalized resource records:

- `asset_uid`
- `provider`
- `account_or_subscription`
- `region_or_location`
- `service`
- `resource_type`
- `name`
- `tags`
- `relationships`
- `evidence_ids`

Findings should reference asset UIDs where possible.

### 6. Operational Muting, CRIS Governance Exceptions

Prowler has mute rules. CRIS already has stronger governance semantics through lifecycle, accepted risk, suppression, expiry, and decision provenance.

The useful idea is the operational UX:

- rule name
- enabled flag
- reason
- finding IDs or patterns
- creator
- processor type

CRIS should keep richer fields:

- approval owner
- expiry
- compensating control
- evidence required
- board or insurer visibility
- decision ledger entry

### 7. Output Interoperability

Prowler exports OCSF, SARIF, ASFF, CSV, HTML, compliance outputs, and integration payloads. CRIS-SME exports more assurance-oriented artifacts.

CRIS should keep its JSON and assurance packs as canonical, then add interoperability exports:

- SARIF for developer/security tooling
- OCSF for security data lakes
- CSV for SMEs and MSPs
- optionally ASFF if AWS support becomes real

### 8. Compliance Pack Validation

Prowler has a large compliance catalog. The important lesson is not the number of frameworks. The lesson is that compliance mappings must be externalized, schema-validated, discoverable, and filterable.

CRIS-SME should validate:

- duplicate control IDs
- invalid framework IDs
- unsupported provider scopes
- missing remediation summaries
- missing evidence requirements
- stale references
- missing assurance claim links

### 9. SaaS Data Model

Prowler's Django models are a useful operational reference. It models providers, scans, resources, findings, scan summaries, daily summaries, integrations, mute rules, and attack path scans.

CRIS-SME should adapt this into an assurance-first SaaS model:

- tenant
- workspace
- cloud account
- assessment run
- evidence record
- asset
- finding
- finding lifecycle event
- exception
- decision ledger entry
- action item
- report artifact
- policy or control pack
- claim verification result
- evidence sufficiency score

### 10. UI Navigation

Prowler's UI routes are a mature map for cloud security operations: overview, findings, resources, compliance, providers, scans, services, attack paths, mutelist, integrations, roles, and users.

CRIS should adapt this around its own personas:

- SME owner: risk summary, decisions, action plan, insurance pack
- Technical lead: evidence, assets, findings, remediations, replay
- Assessor or auditor: claims, evidence sufficiency, mappings, exceptions
- MSP: workspaces, runs, drift, action queues
- Insurer or board: selective disclosure and signed artifacts

## What Not To Copy

Do not compete with Prowler on raw check count. CRIS-SME's advantage is trust, interpretation, and defensible decision support.

Do not inherit Prowler's full dependency footprint. CRIS-SME should stay lightweight and local-first until SaaS persistence genuinely requires more.

Do not let AI alter scores or conclusions. Prowler's Lighthouse/MCP pattern is useful, but CRIS should keep AI as a narrator over deterministic evidence and claim IDs.

Do not add auto-fix as a default behavior. CRIS can generate remediation commands and IaC snippets, but execution should require explicit approval and should be linked to a decision record.

Do not flatten CRIS findings into scanner findings. CRIS finding fields such as confidence, exposure, sensitivity, remediation effort, and decision provenance are central to the project.

## Prioritized Ideas For CRIS-SME

### P0: Highest Leverage

1. [DONE] Add `ControlDefinition` metadata v2.

   Include title, category, severity, provider support, resource type, resource group, description, risk, evidence requirements, freshness, confidence penalties, compliance mappings, remediation text, remediation code, related controls, dependencies, and assurance claims.

   Implemented in `data/control_metadata_v2.schema.json`, `data/control_metadata_v2.json`, and `src/cris_sme/controls/definitions.py`, covering `IAM-001`, `NET-001`, `DATA-001`, `MON-001`, `GOV-001` with all listed fields.

2. [DONE] Add a control registry and loader.

   Support filtering controls by ID, domain, severity, provider, framework, resource group, and evidence requirement.

   Implemented in `src/cris_sme/controls/registry.py` (`ControlRegistry.filter`), including dependency expansion and assurance-claim filtering.

3. [PARTIAL] Introduce `AssessmentRunner`.

   Refactor the orchestration in `main.py` into a reusable runner with structured phases, events, progress, and artifact manifests.

   `src/cris_sme/engine/assessment_runner.py` exists and `main.py` now drives the assessment through it, emitting `AssessmentEvent`s for `COLLECT_EVIDENCE`, `EVALUATE_CONTROLS`, `SCORE_FINDINGS`, `MAP_COMPLIANCE`, and now `ASSESS_EVIDENCE_SUFFICIENCY` (run-level rollup of per-finding evidence sufficiency via `AssessmentEvidenceSufficiencyOverview`). `main.py` also now writes runner events as JSONL to `CRIS_SME_RUNNER_EVENTS_PATH` if set, and `local_runner.py` sets this per run and exposes the events via `/api/assessments/<run_id>` as `runner_events`, so the local API surfaces live runner progress without waiting for the full report. Remaining: `normalize_profile`, `update_lifecycle`, `build_decisions`, and `generate_artifacts` are still inline in `main.py` rather than runner phases — these require output-directory/history context that sits outside the runner's evidence-to-risk scope, and `local_runner.py` still spawns a CLI subprocess for full report generation (now with live event tailing alongside it).

4. [DONE] Add normalized asset and evidence records.

   Keep `CloudProfile`, but enrich it with asset-level records. Findings should reference assets and evidence IDs.

   `Asset`, `EvidenceRecord`, and `FindingAssetLink` are implemented in `src/cris_sme/models/platform.py`; `src/cris_sme/engine/assessment_context.py` builds `AssessmentResourceContext` from profiles, and `Finding` now carries `asset_ids`/`evidence_ids`.

5. [DONE] Expand provider contracts.

   Add provider identity, scopes, auth mode, permission checks, evidence capabilities, and collector limitations.

   `src/cris_sme/engine/provider_contracts.py` now models identity, scope, auth, permission, evidence-capability, and limitation contracts; `provider_conformance.py` runs executable conformance checks against them.

### P1: Next Layer

6. [DONE] Add governance-aware mute and exception rules.

   Borrow Prowler's operational simplicity, but keep CRIS approval, expiry, compensating control, and decision ledger semantics.

   `ExceptionRecord` (with `approved_by`, `expires_at`, `compensating_control`, `status`) and `FindingStatus` are in `src/cris_sme/models/platform.py`, and `src/cris_sme/engine/lifecycle.py` matches exceptions to findings and emits `exception_applied`/`exception_expired` decision-ledger events. A new `MuteRule` model (`rule_id`, `name`, `enabled`, `control_id`/`provider`/`scope_pattern`/`finding_id_pattern`, `expires_at`) backs an operational mute-rule registry (`data/mute_rules.json`) managed via `python -m cris_sme.cli.mute_rules` (list/add/enable/disable/remove). `enrich_report_finding_lifecycle` applies enabled, non-expired mute rules to set `lifecycle.status = suppressed`, and `compute_adjusted_risk_scores` recomputes `overall_risk_score`/`category_scores` excluding suppressed, resolved, and actively-accepted-risk findings (written to `output["adjusted_risk_scores"]`) — while expired exceptions keep full score weight until renewed, enforcing expiry back into the headline risk posture.

7. [DONE] Add SARIF and OCSF exports.

   This makes CRIS easier to integrate with existing security tools without changing CRIS's canonical report model.

   Implemented in `src/cris_sme/reporting/sarif_export.py` and `ocsf_export.py` (plus `csv_export.py` for SME/MSP consumption), wired into `main.py` output generation.

8. [DONE] Add schema validation for control and compliance packs.

   Run validation in tests and eventually in CI.

   `data/control_metadata_v2.schema.json` plus Pydantic validators in `controls/definitions.py` and `tests/test_control_metadata_v2_registry.py` cover duplicate IDs, framework mappings, and required fields. Remaining: this validation is only exercised via `pytest`, not a standalone CI lint step.

9. [DONE] Add precomputed assessment summaries.

   Summaries should include severity, category, control, compliance, resource, lifecycle, evidence sufficiency, drift, and claim coverage.

   `src/cris_sme/engine/assessment_summary.py` builds `AssessmentSummary` covering all of these dimensions plus top risks/controls.

10. [DONE] Add least-privilege setup artifacts.

   Ship Azure role definitions or Bicep/Terraform for CRIS evidence collection. Add future AWS/GCP permission templates only when the collectors exist.

   `docs/azure-least-privilege-setup.md` and `infra/azure/role-definitions/cris-sme-assessment-reader.json` cover Azure RBAC + Graph permissions. Now that a research-preview AWS collector exists, `docs/aws-least-privilege-setup.md` and `infra/aws/iam-policies/cris-sme-assessment-reader.json` cover the equivalent read-only IAM policy, contract-tested in `tests/test_aws_least_privilege_setup.py`. GCP templates remain deferred until a GCP collector exists.

11. [DONE] Add a live AWS collector.

   `src/cris_sme/collectors/aws_collector.py` implements `AwsCollector`, a boto3-backed collector at structural parity with `AzureCollector` across all seven domains (IAM, Network, Data, Monitoring, Compute, Governance, IoT), using the standard AWS credential chain and the same dependency-injected client-factory pattern Azure's collector uses for testability. It is wired into `AssessmentRunner`, the local API runner (`/api/environment/aws`, `/api/assessments/aws`), and the React console's New Assessment provider toggle. `provider_support.aws` moved from `planned` to `research_preview` for all affected controls — it has been unit-tested against fake boto3 clients (`tests/test_aws_collector.py`) but **not yet verified against a real AWS account**, so `provider_conformance.ACTIVE_LIVE_COLLECTORS` deliberately still excludes `"aws"`.

### P2: Later Platform Ideas

11. [DONE] Add CRIS MCP tools.

   Tools should query assessments, findings, evidence, claims, exceptions, and action plans. AI should cite deterministic IDs.

   `src/cris_sme/mcp/tools.py` implements standalone query functions (`get_assessment_summary`, `list_findings`, `get_finding`, `list_evidence`, `list_claims`, `list_exceptions`, `list_mute_rules`, `list_action_plan`, `list_assessment_history`) over a loaded report, all keyed on deterministic IDs (`finding_id`, `evidence_id`, `claim_id`, `exception_id`, `rule_id`). `src/cris_sme/mcp/server.py` wraps these as `FastMCP` tools behind a guarded optional `mcp` dependency (`pyproject.toml` `mcp` extra).

12. [DONE] Add optional remediation script packs.

   Generate Azure CLI, Bicep, Terraform, or manual steps. Keep execution out of the default path.

   `ControlDefinition` now carries `RemediationCodeDefinition` entries (e.g. Azure CLI snippets for `IAM-001`) via `definitions.py` and `control_metadata_v2.json`. `src/cris_sme/reporting/remediation_export.py` generates a non-executing reference bundle (`remediation_scripts/cris_sme_remediation_manifest.json` plus one `.sh` per remediation kind, e.g. `cris_sme_remediation_azure_cli.sh`) wired into `output["report_artifacts"]["remediation_script_pack"]`, with the manifest's `execution_policy` explicitly set to `non_executing_reference_only`.

13. [DONE] Add attack-path or relationship views.

   Start with asset relationships and blast-radius context. Avoid bringing in a graph database until the resource model is stable.

   `src/cris_sme/engine/graph_context.py` builds `AssetRelationship` edges, blast-radius estimates, toxic-combination detection, and exposure chains as a lightweight context graph (no graph database, as intended). `frontend/console/src/pages/AttackPaths.tsx` now renders a per-organization layered asset graph (React Flow) with severity-ring highlighting on findings-linked assets and a 2-hop blast-radius drawer.

14. [DONE] Expand UI routes.

   Build from CRIS personas rather than copying Prowler routes directly.

   `frontend/console/src/pages/Personas.tsx` adds a `/personas` route with five persona-specific briefings (SME Owner, Technical Lead, Assessor, MSP, Insurer) built from CRIS report sections (`executive_pack`, `report_trust_badge`, `assessment_assurance`, `cyber_insurance_evidence`, `organizations`), wired into `App.tsx` routing and the `Layout.tsx` nav.

## Suggested Implementation Roadmap

### Phase 1: Metadata and Registry — DONE

- Add `data/control_metadata_v2.schema.json`.
- Add `src/cris_sme/controls/definitions.py`.
- Add `src/cris_sme/controls/registry.py`.
- Convert a small set of controls first: `IAM-001`, `NET-001`, `DATA-001`, `MON-001`, `GOV-001`.
- Add validation tests for metadata consistency.

### Phase 2: Assessment Runner — PARTIAL

- Add `src/cris_sme/engine/assessment_runner.py`. **(done)**
- Move orchestration steps out of `main.py`. **(done for collect/evaluate/score/compliance/evidence-sufficiency; normalize, lifecycle, decisions, and artifact generation are still inline in `main.py`)**
- Add progress events and artifact manifest generation. **(events done, including evidence sufficiency; manifest generation still pending)**
- Update local API to consume runner events instead of only spawning the CLI. **(done — `local_runner.py` sets `CRIS_SME_RUNNER_EVENTS_PATH` per run and exposes `runner_events` via the run status endpoint while the CLI subprocess generates the full report)**

### Phase 3: Asset and Evidence Model — DONE

- Add `Asset`, `EvidenceRecord`, and `FindingAssetLink` models.
- Keep aggregate `CloudProfile` for scoring.
- Enrich Azure live collection with asset IDs and evidence IDs.
- Add resource drilldown payloads for the dashboard.

### Phase 4: Provider Contract Expansion — DONE

- Expand provider contracts with identity, scopes, permissions, capabilities, evidence freshness, and limitations.
- Add Azure setup documentation and least-privilege templates.
- Add provider capability tests.

### Phase 5: SaaS Readiness — PARTIAL

- Translate CRIS SaaS docs into persistence models. **(done — `platform.py` models for exceptions, action items, history, run metadata, decision ledger)**
- Add summaries and lifecycle event tables. **(summaries done via `assessment_summary.py`; lifecycle event persistence is in-memory/report-scoped, not a durable table)**
- Add role-specific UI views. **(not started)**
- Add export APIs for reports, evidence, and insurer packs. **(not started — exports are file-based via the CLI, no API endpoints)**

## Bottom Line

Prowler should influence CRIS-SME's engineering architecture, not its soul.

The strongest move is to make CRIS-SME more metadata-driven, resource-aware, provider-capable, and API-ready while keeping the distinctive CRIS layer: evidence quality, confidence, decision provenance, lifecycle governance, assurance artifacts, and SME-focused action.
