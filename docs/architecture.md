# CRIS-SME Architecture

This document is the architectural source of truth for CRIS-SME. It describes
the implementation that exists today, the trust boundaries around live cloud
collection, and the deliberate boundary between the local/self-hosted product
and the planned hosted multi-tenant platform.

## System Context

CRIS-SME is an evidence-to-decision system. Cloud APIs provide read-only posture
evidence; deterministic controls turn that evidence into explainable findings;
and one canonical assessment model feeds technical, executive, compliance, and
assurance outputs.

```mermaid
flowchart LR
    operator["Security operator<br/>or authorised assessor"]
    stakeholder["SME leadership, engineers,<br/>auditors and insurers"]

    subgraph estate["Authorised assessment scope"]
        azure["Microsoft Azure<br/>control-plane APIs"]
        aws["Amazon Web Services<br/>control-plane APIs"]
        public["Explicitly authorised<br/>public endpoints"]
    end

    subgraph cris["CRIS-SME trust boundary"]
        console["Assurance Console<br/>React + TypeScript"]
        api["Local Assessment API<br/>Python HTTP service"]
        engine["Deterministic Decision Engine<br/>controls, scoring and governance"]
        reports["Assurance Artifacts<br/>reports, packs and evidence lineage"]
    end

    operator --> console
    console -->|"assessment request"| api
    api -->|"read-only collection"| azure
    api -->|"read-only collection"| aws
    api -->|"bounded observation"| public
    api --> engine
    engine --> reports
    reports --> console
    reports --> stakeholder

    classDef external fill:#f6f7f9,stroke:#697386,color:#172033
    classDef product fill:#eef4ff,stroke:#3457d5,color:#172033
    class azure,aws,public,operator,stakeholder external
    class console,api,engine,reports product
```

## Component Architecture

The major components are separated so provider authentication, collection,
decision logic, persistence, and presentation can evolve independently. Solid
arrows below are implemented paths. The final dashed boundary is the planned
hosted-service evolution, not a claim about the current product.

```mermaid
flowchart TB
    subgraph experience["Experience and integration plane"]
        ui["Assurance Console<br/>18 focused views"]
        static["Static demonstration bundle<br/>Vercel or any static host"]
        cli["CLI and automation scripts"]
        mcp["Optional MCP tools"]
    end

    subgraph delivery["Assessment orchestration plane"]
        localapi["Local API runner<br/>request validation and job orchestration"]
        processdb[("SQLite run ledger<br/>queued, running, completed, failed")]
        events["Structured phase events<br/>JSONL progress stream"]
        runner["AssessmentRunner<br/>five deterministic phases"]
    end

    subgraph access["Provider access and evidence plane"]
        azidentity["Azure CLI identity<br/>runner-side az login"]
        awsidentity["AWS credential chain<br/>optional STS AssumeRole"]
        azurecollector["Azure collector<br/>live verified"]
        awscollector["AWS collector<br/>research preview"]
        mockcollector["Mock collector<br/>reproducible fixtures"]
        exposure["Public exposure observer<br/>DNS, HTTP, TLS and headers"]
        contracts["Provider evidence contracts<br/>coverage, permissions and gaps"]
    end

    subgraph decision["Provider-neutral decision plane"]
        normalized["Normalized CloudProfile<br/>assets, relationships and evidence"]
        controls["Versioned control registry<br/>7 domains and policy metadata"]
        evaluation["Deterministic evaluation<br/>finding trace and evidence refs"]
        risk["Risk and confidence<br/>scoring, graph context and priority"]
        governance["Governance and readiness<br/>lifecycle, exceptions and mappings"]
        sufficiency["Evidence sufficiency<br/>observed, inferred and unresolved"]
    end

    subgraph assurance["Assurance and output plane"]
        canonical["Canonical JSON assessment"]
        history[("File-backed report history<br/>and assessment snapshots")]
        technical["Technical outputs<br/>HTML, CSV, SARIF and OCSF"]
        action["Decision outputs<br/>remediation and budget simulation"]
        compliance["Compliance outputs<br/>Cyber Essentials and mappings"]
        trust["Trust outputs<br/>RBOM, replay, provenance and claims"]
        executive["Stakeholder outputs<br/>executive, insurer and disclosure packs"]
    end

    subgraph future["Planned hosted platform boundary"]
        auth["Authentication and RBAC"]
        tenants["Tenant-isolated API and data stores"]
        schedules["Scheduled assessments and notifications"]
    end

    ui --> localapi
    cli --> runner
    mcp --> runner
    canonical --> static
    localapi <--> processdb
    localapi --> runner
    runner --> events
    events --> localapi

    azidentity --> azurecollector
    awsidentity --> awscollector
    azurecollector --> normalized
    awscollector --> normalized
    mockcollector --> normalized
    exposure --> canonical
    contracts --> azurecollector
    contracts --> awscollector

    normalized --> evaluation
    controls --> evaluation
    evaluation --> risk
    evaluation --> sufficiency
    risk --> governance
    sufficiency --> governance
    governance --> canonical

    canonical --> history
    canonical --> technical
    canonical --> action
    canonical --> compliance
    canonical --> trust
    canonical --> executive
    history --> localapi
    canonical --> ui

    localapi -. "future evolution" .-> auth
    auth -.-> tenants
    tenants -.-> schedules

    classDef current fill:#eef4ff,stroke:#3457d5,color:#172033
    classDef evidence fill:#ecf8f1,stroke:#23855b,color:#172033
    classDef store fill:#fff6df,stroke:#a66b00,color:#172033
    classDef planned fill:#f5f5f5,stroke:#707070,color:#333,stroke-dasharray:5 5
    class ui,static,cli,mcp,localapi,events,runner,normalized,controls,evaluation,risk,governance,sufficiency,canonical,technical,action,compliance,trust,executive current
    class azidentity,awsidentity,azurecollector,awscollector,mockcollector,exposure,contracts evidence
    class processdb,history store
    class auth,tenants,schedules planned
```

## Assessment Flow

Each live run keeps cloud credentials outside the browser. The API starts a
background process, records process state in SQLite, emits structured progress,
and publishes the completed report snapshot and derived artifacts.

```mermaid
sequenceDiagram
    autonumber
    actor User as Authorised operator
    participant UI as Assurance Console
    participant API as Local API runner
    participant DB as SQLite run ledger
    participant Auth as Provider identity
    participant Cloud as Cloud control plane
    participant Run as AssessmentRunner
    participant Core as Decision engine
    participant Files as Report and artifact store

    User->>UI: Select provider, organisation and scope
    UI->>API: POST assessment with authorisation acknowledgement
    API->>Auth: Validate Azure session or AWS role
    Auth-->>API: Account and permission context
    API->>DB: Persist queued run
    API-->>UI: 202 Accepted with run ID
    API->>Run: Start assessment subprocess
    Run->>DB: Mark run running
    Run->>Cloud: Read authorised control-plane evidence
    Cloud-->>Run: Provider observations and visibility gaps
    Run->>Core: Normalized profiles and evidence records
    Core->>Core: Evaluate controls and build finding lineage
    Core->>Core: Score risk, confidence and graph context
    Core->>Core: Map compliance and assess sufficiency
    Core-->>Run: Deterministic assessment result
    Run->>Files: Write canonical report and derived artifacts
    Run->>DB: Persist terminal state and output location
    loop Until terminal state
        UI->>API: GET run status
        API->>DB: Read durable process state
        API-->>UI: Phase events and status
    end
    UI->>API: GET selected assessment report
    API->>Files: Resolve report snapshot
    Files-->>UI: Findings, evidence, history and artifacts
```

## Core Data Contracts

| Contract | Purpose | Authoritative implementation |
| --- | --- | --- |
| `CloudProfile` | Provider-normalized posture consumed by every control domain | `models/cloud_profile.py` |
| `Asset`, `AssetRelationship` | Resource inventory and graph context | `models/platform.py` |
| `EvidenceRecord`, `CollectorCoverage` | Evidence provenance and observability boundaries | `models/platform.py` |
| `Finding`, `FindingTrace` | Stable control decision, evidence lineage and rationale | `models/finding.py`, `models/platform.py` |
| `ScoringResult` | Deterministic priority and aggregate risk outputs | `engine/scoring.py` |
| `AssessmentRunnerResult` | Provider-neutral result before artifact generation | `engine/assessment_runner.py` |
| Canonical JSON report | Shared payload for every console and export view | `reporting/json_report.py` |
| Assessment run record | Durable orchestration status; never stores AWS External IDs | `api/run_repository.py` |

The console is intentionally non-authoritative: it displays these contracts but
does not calculate findings, modify scores, or infer unavailable evidence.

## Security and Trust Boundaries

1. **Authorisation boundary.** A live assessment requires explicit operator
   acknowledgement and must target an estate the operator is authorised to test.
2. **Credential boundary.** Azure uses the runner's existing Azure CLI session.
   AWS uses the standard SDK credential chain and can assume a customer role with
   short-lived STS credentials. Provider credentials are not sent to the React UI.
3. **Collection boundary.** Collectors make read-only control-plane calls. Public
   exposure mode is limited to DNS, HTTP, HTTPS, TLS, redirect, and header
   observation; it does not exploit, crawl, or brute force targets.
4. **Decision boundary.** Controls and scores are deterministic and versioned.
   Optional narrative features cannot create findings or alter risk values.
5. **Evidence boundary.** Missing, partial, stale, or inferred evidence remains
   visible through coverage, confidence, and evidence-sufficiency metadata.
6. **Persistence boundary.** Run process state is durable in SQLite. Full reports
   and artifacts are currently file-backed. Multi-tenant isolation is not yet
   implemented, so the local API must not be exposed directly to the internet.
7. **Integrity boundary.** Replay, RBOM, hashes, decision provenance, and
   claim-verification artifacts make the path from evidence to stakeholder claim
   inspectable.

## Deployment Modes

| Mode | UI | Assessment execution | Persistence | Intended use |
| --- | --- | --- | --- | --- |
| Static demo | Prebuilt React bundle | None; reads bundled assessment data | Static files | Product demonstration and report exploration |
| Local development | Vite dev server | Local Python API and provider CLI/SDK identity | SQLite runs plus file-backed reports | Engineering and authorised testing |
| Self-hosted trial | Container-built console and local API | Customer-controlled runtime | Mounted SQLite/report volumes | Private pilot in a controlled network |
| Hosted multi-tenant service | Planned | Planned isolated workers | Planned tenant database and object storage | Future MSP/SaaS operation |

## Architectural Invariants

- The same normalized evidence and deterministic engine feed every audience view.
- Provider-specific behavior ends at the normalization boundary.
- A generated narrative cannot become evidence and cannot change a score.
- Every risk decision should retain a control ID, evidence reference, rule version,
  confidence rationale, and lifecycle identity.
- Unsupported visibility is represented as a gap, not silently treated as a pass.
- Static publication contains generated artifacts, never live provider credentials.

## Current Maturity and Next Boundary

Azure collection is live-verified. AWS collection and cross-account role
assumption are implemented and have been exercised in an authorised live
assessment, while AWS provider semantics remain labelled `research_preview`
until broader provider-specific validation is complete. Mock mode remains the
reproducible development and CI path.

The next architectural milestone is pilot readiness: API authentication,
per-assessment artifact isolation, database-backed report metadata, and Azure
browser-based delegated onboarding. Tenant isolation, RBAC, scheduling, and
hosted worker orchestration belong to the later multi-tenant platform boundary.

Related detail:

- [Frontend console](frontend-console.md)
- [Data model](data-model.md)
- [Provider evidence contracts](provider-evidence-contracts.md)
- [Security and trust model](security-trust-model.md)
- [SaaS and API evolution](saas-api-evolution.md)
- [2026 H2 roadmap](roadmap-2026-h2.md)
