# Roadmap 2026 H2 — Inspection Findings and Improvement Plan

> Supersedes the priority sections of [roadmap.md](roadmap.md), whose 0/30/60/90-day
> items are now largely complete (RBOM signing, decision ledger, AWS adapter,
> console gap closure, IoMT track). The product themes in that document remain valid.

## Where the project actually stands (July 2026 inspection)

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

| # | Gap | Evidence | Impact |
|---|-----|----------|--------|
| 1 | **No persistence layer** | `local_runner.py` keeps runs in an in-memory dict; history is loose JSON files in `outputs/reports/history/` | Restart loses runs; no queryable history; blocks multi-org |
| 2 | **No API authentication** | `local_runner` assumes localhost trust | Cannot be hosted; blocks any client-facing deployment |
| 3 | **No browser-side credential flow** | Auth = whatever `az`/`aws` CLI session exists on the server machine | A new org cannot connect without shell access to the runner box |
| 4 | **Single-report architecture** | One 1.4 MB `cris_sme_report.json` is the whole data plane | No per-org storage, heavy payload, everything re-read per page |
| 5 | **AWS collector unverified live** | Marked `research_preview`; mock-tested only | Cannot honestly claim multi-cloud yet |
| 6 | **Zero frontend tests** | No test files in `frontend/console/src/` | 18 pages regress silently; only guard is `tsc` |
| 7 | **No container packaging** | No Dockerfile anywhere | Self-hosted clients have no install path besides "clone + pip + npm" |
| 8 | **Bundle size** | 614 kB JS, no code splitting | Slow first load on the hosted demo |
| 9 | **Decorative UI elements** | Header search box is a non-functional label | Erodes trust in a product whose brand is honesty |

## Phase 1 — Demo credibility (now → 4 weeks)

Goal: the Aureon Systems demo link is live, fast, and self-explanatory.

1. **Ship the static demo** (built, needs deploy): `dist/demo/` →
   `demo.aureonsystems.com`. Fix `VITE_CONTACT_URL` to the real domain.
2. **Code-split the console**: lazy-load routes (`React.lazy` per page) to cut
   the initial bundle; recharts and @xyflow/react are the heavy imports and only
   3 pages need them.
3. **Remove or implement the header search**. Cheapest honest fix: a client-side
   finding/control filter over the already-loaded report.
4. **Frontend smoke tests**: Vitest + Testing Library; one render test per page
   against the demo report fixture (the anonymised JSON already exists — use it
   as the shared fixture). Target: every route renders without throwing on both
   full and empty reports.
5. **Dockerfile + compose**: one container running `local_runner` + serving the
   built console. This is the "self-hosted trial" install path and costs ~a day.

## Phase 2 — From demo to pilot-ready (weeks 4–10)

Goal: one real external organisation can run an assessment without you touching
their machine.

1. **Persistence**: SQLite via a thin repository layer (runs, report snapshots,
   lifecycle events). Local-first stays true — a file DB, no server dependency.
   This unblocks history queries, multi-org, and survives restarts.
2. **API auth**: static API-key middleware on `local_runner` (header check +
   constant-time compare). Enough for a gated pilot; OAuth comes later.
3. **Browser-entered AWS credentials**: the Role ARN + External ID fields already
   exist in the form; make the backend honour them end-to-end
   (`sts:AssumeRole` from the runner's base identity) instead of defaulting to
   the local credential chain. This is the *smallest* real "connect a new org
   from the browser" path.
4. **Verify AWS live**: run the collector against a real (personal/free-tier)
   AWS account, fix what breaks, and only then lift `research_preview` — the
   provider-contract machinery for this already exists.
5. **Per-org report storage**: `outputs/orgs/{org_id}/...` keyed by the new DB,
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
- The 92 uncommitted working-tree files should be reviewed and committed in
  topical chunks — the demo-mode work, the IoMT docs, and the collector
  expansion are separate stories and deserve separate commits.
