# Prowler Comparison and CRIS-SME Ideas

> Historical design comparison. For the current source-based review, use the [enterprise reference audit](enterprise-reference-audit.md); for all priorities, use the [canonical roadmap](roadmap.md).

This note compares a local Prowler checkout with CRIS-SME. The goal is not to turn CRIS-SME into another scanner. Prowler is strongest as a broad cloud security scanning platform. CRIS-SME is strongest as an evidence-to-decision governance and assurance platform for SMEs.

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

## Current Audit And Execution Plan

The previous priority lists and implementation phases have been removed to avoid competing roadmaps. The [September reference audit](enterprise-reference-audit.md) now records the inspected Prowler and OpenShield strengths, CRIS implementation gaps and source evidence. The [canonical roadmap](roadmap.md) owns all delivery priorities and acceptance gates.

Earlier architecture comparisons in this document remain background, not a current support matrix or claim that every metadata entry, provider or SaaS feature is complete.

## Bottom Line

Prowler should influence CRIS-SME's engineering architecture, not its soul.

The strongest move is to make CRIS-SME more metadata-driven, resource-aware, provider-capable, and API-ready while keeping the distinctive CRIS layer: evidence quality, confidence, decision provenance, lifecycle governance, assurance artifacts, and SME-focused action.
