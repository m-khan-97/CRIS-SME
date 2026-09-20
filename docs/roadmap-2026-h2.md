# Roadmap 2026 H2 — Inspection Findings and Improvement Plan

> Supersedes the priority sections of [roadmap.md](roadmap.md), whose 0/30/60/90-day
> items are now largely complete (RBOM signing, decision ledger, AWS adapter,
> console gap closure, IoMT track). The product themes in that document remain valid.

## Where the project actually stands (September 2026 update)

### Strengths — genuinely done and working

- **Deterministic engine**: ~40 engine modules (scoring, lifecycle, provenance,
  RBOM + signing, claim verification, assurance case, CE evaluation, remediation
  simulation, replay determinism). This is the moat — no competitor in the SME
  space has evidence-sufficiency boundaries or claim-bound narratives.
- **Azure collector is live-verified** (3.7k LOC): identity, governance, policy
  compliance, Defender plans, PIM, IoT Hub. Validated against a real tenant.
- **IoMT research track**: 10 controls, expert-review pack, paper suite, live
  validation. A defensible research niche (NHS DSPT / IEC 80001-1 mapping).
- **Console**: 18 pages, dark/light theme, demo mode with anonymised bundle
  (`npm run build:demo` → static, host-anywhere).
- **Quality discipline**: 321 backend tests passing, 7 CI workflows (CodeQL,
  dependency review, scheduled assessment), zero TODO/FIXME markers in source,
  honest-claims culture enforced by tests (e.g. no-remote-assets guard).
- **Docs**: 60+ documents covering architecture, methodology, evaluation, and
  provider contracts.

### Structural gaps — the things holding it back

| # | Remaining gap | Current evidence | Impact |
|---|---------------|------------------|--------|
| 1 | **Report persistence remains file-based** | Process lifecycle is now persisted in SQLite, but full reports remain JSON files indexed from `outputs/` | Run status survives restart, but cross-org report queries and transactions remain limited |
| 2 | **No API authentication** | `local_runner` still assumes localhost trust | Cannot safely expose the runner as a hosted pilot service |
| 3 | **Azure still depends on runner-side CLI auth** | AWS supports browser-entered Role ARN/External ID end to end; Azure still uses the runner's `az login` session | A new Azure organisation still needs operator involvement |
| 4 | **Shared latest-report output path** | Report history and selection exist, but new standard runs still write canonical artifacts to one output directory | Concurrent or multi-org runs can overwrite the latest artifact set |
| 5 | **AWS remains research preview** | Collector has unit coverage and was exercised in an authorised live AWS assessment; provider-specific semantics and labels still need validation | Live feasibility is shown, but full multi-cloud equivalence remains an unsafe claim |
| 6 | **Frontend testing is smoke-level** | Vitest route smoke coverage exists for full and empty reports | Interaction, accessibility, and browser workflow regressions remain under-tested |
| 7 | **No tenant security boundary** | Organisation labels and report selectors exist without authenticated workspace isolation | Blocks a genuine MSP or hosted multi-tenant deployment |
| 8 | **No scheduled delivery workflow** | Drift/history engines exist, but per-org scheduling and notification do not | Reassessment remains operator-driven |

## Phase 1 — Demo credibility (now → 4 weeks)

Goal: the Aureon Systems demo link is live, fast, and self-explanatory.

1. **[DONE] Ship the static demo**: the console was deployed at the configured
   `crisdemo.aureonsystemsltd.com` domain.
2. **[DONE] Code-split the console**: routes use `React.lazy`; heavy pages are
   emitted as separate chunks.
3. **[DONE] Remove or implement the header search**: findings include a working
   client-side finding/control filter; decorative global search was removed.
4. **[DONE] Frontend smoke tests**: Vitest + Testing Library render routes
   against the demo report fixture (the anonymised JSON already exists — use it
   as the shared fixture) for full and empty states.
5. **[DONE] Dockerfile + compose**: one container runs `local_runner` and serves the
   built console. This is the "self-hosted trial" install path and costs ~a day.

## Phase 2 — From demo to pilot-ready (weeks 4–10)

Goal: one real external organisation can run an assessment without you touching
their machine.

1. **[PARTIAL] Persistence**: a thin SQLite repository now persists assessment
   process state, exposes `/api/assessment-runs`, and marks interrupted runs
   explicitly after restart. Full report snapshots and lifecycle events remain
   file-backed and should move behind the same repository boundary next.
2. **API auth**: static API-key middleware on `local_runner` (header check +
   constant-time compare). Enough for a gated pilot; OAuth comes later.
3. **[DONE] Browser-entered AWS credentials**: Role ARN + External ID are
   honoured end to end through `sts:AssumeRole`, including a preflight role
   verification endpoint. External IDs are never persisted in SQLite.
4. **[PARTIAL] Verify AWS live**: the collector was exercised in an authorised
   live AWS assessment. Keep `research_preview` until provider-specific labels,
   evidence sufficiency, and control semantics pass a dedicated validation run.
5. **[PARTIAL] Per-org report storage**: report history discovers isolated
   evidence-lab outputs and the console can select historical reports. Standard
   assessment writes still need `outputs/orgs/{org_id}/...` keyed by the DB,
   replacing the single-report assumption in `getLatestReport()` with an org
   selector.

## Phase 3 — Product plane (weeks 10–20)

Goal: the SaaS shape described in [saas-api-evolution.md](saas-api-evolution.md),
minimally.

1. **Azure OAuth (Entra app registration)**: "Connect Azure" button → consent
   popup → bearer token → collector uses `management.azure.com` REST instead of
   the CLI. This removes the last need for server-side CLI sessions.
2. **Hosted multi-tenant runner**: the SQLite layer graduates to Postgres only
   when a second concurrent tenant exists — not before.
3. **MSP portfolio view**: one page over the per-org data (the org selector from
   Phase 2 makes this nearly free).
4. **Scheduled re-assessment per org** + drift alerts (the engine's drift
   modules already compute this; it needs delivery, e.g. email digest).

## Deliberately deferred

- **GCP collector** — no user demand signal yet; the provider-contract layer
  means adding it later is bounded work.
- **AI narration layer** — the deterministic story is the differentiator; add
  AI overlay only after pilots, and keep it non-authoritative as
  [product-strategy.md](product-strategy.md) already states.
- **Billing/subscription infrastructure** — premature before a paying pilot.

## Standing improvements (continuous, not phased)

- Keep the honest-claims tests growing with the product (demo mode, provider
  support labels, evidence sufficiency).
- Refresh [roadmap.md](roadmap.md) product themes quarterly; keep this file's
  phase table updated as items land.
- Keep unrelated working-tree material in topical commits; implementation,
  research manuscripts, generated reports, and deployment artifacts are
  separate stories.
