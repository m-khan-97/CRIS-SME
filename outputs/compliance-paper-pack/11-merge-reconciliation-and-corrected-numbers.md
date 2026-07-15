# Merge reconciliation — corrected numbers (2026-07-15)

This reconciles the two artifact lineages that existed for this paper and proposes the
exact replacement text for `00-README-START-HERE.md` and `01-paper-material-pack.md`.
Nothing has been written into those two files yet — review the proposed text below first.

## What existed, and what happened to each

| | Prowler-upstream (real, live) | Reference schema (this paper's own artifact) |
|---|---|---|
| **Files** | `feat/cyber-essentials-compliance-azure` branch → PR **#11588**; `feat/gdpr-compliance-azure` branch → PR **#11590** | `09-merged-artifact-cyber_essentials_3.3.json`, `10-merged-artifact-gdpr_azure.json` (this folder) |
| **Status** | Open on `prowler-cloud/prowler`, **approved by 2 maintainers** (#11588: pedrooot + Alan-TheGentleman; #11590: pedrooot — "Love this work 🥇"), awaiting merge. pedrooot has already built UI/dashboard integration around #11588's schema. | Never pushed anywhere; exists only in this repo and the local fork clone. Not a Prowler citation target. |
| **CE schema** | `AssessmentStatus` (Automated/Manual) + `CloudApplicability` (full/partial/non-applicable) — mirrors Prowler's existing ASD Essential Eight idiom | `Type` (direct_cloud/inferred_cloud/endpoint_required/policy_required/manual_required) + per-requirement `Comment` rationale — finer-grained |
| **CE requirements / checks** | 28 requirements, 30 unique Azure checks | 18 requirements, 64 unique Azure checks |
| **GDPR schema** | Plain `Section`/`Service` (matches the pre-existing AWS `gdpr_aws.json` structure) | Same `Type` taxonomy as CE |
| **GDPR requirements / checks** | 3 requirements (Arts. 25, 30, 32 only) | 10 requirements (Arts. 5(1)(f), 25, 30, 32(a–d), 33, 34, 35) |

**Decision taken (2026-07-15):** do not touch #11588/#11590 — they stay exactly as the
maintainers approved them. The reference schema is the paper's own artifact, merged with
the checks that only exist in the upstream version (added during maintainer review, and
independently checked against the current Azure check inventory).

## The merge

GDPR requirement `article_25` gained 7 checks, `article_30` gained 2, `article_32_1_a`
gained 1, `article_32_1_b` gained 3 — all copied from PR #11590's approved mapping,
placed under the closest matching Article in the 10-requirement structure. CE needed no
merge: every check in the approved #11588 mapping already existed in the richer draft.

All 114 unique checks in the resulting union (64 CE + 89 GDPR, 39 shared) were
independently re-verified against the current Azure check inventory
(`prowler/providers/azure/services/**/*.metadata.json`, 191 checks / 22 services as of
this session) — zero missing.

## Corrected numbers

| Metric | Old (wrong) value in `00`/`01` | Corrected value |
|---|---|---|
| Azure check inventory | 169 checks, 22 services | **191 checks, 22 services** |
| CE (reference schema) | 18 requirements, 64 checks | unchanged — 18 requirements, **64 checks** |
| GDPR (reference schema) | 10 requirements, 76 checks | 10 requirements, **89 checks** (+13 folded in from upstream review) |
| Combined union | 107/169 (63%) | **114/191 (59.7%)**, 39 shared |
| Prowler contribution status | "committed locally on `feat/azure-gdpr-cyber-essentials-compliance`, not yet pushed" | **PR #11588 and PR #11590 open on `prowler-cloud/prowler`, both maintainer-approved, awaiting merge** — but note: the *contributed* artifact is the smaller upstream one (28 req/30 checks CE; 3 req/51 checks GDPR), not the reference schema above |

## Proposed replacement text for `00-README-START-HERE.md`, "Key verified numbers" section

```markdown
## Key verified numbers (do not invent others)

- Prowler Azure: 191 checks, 22 services; **no prior CE framework for any
  provider; prior GDPR is AWS-only, 3 articles**.
- Contributed to Prowler upstream (PR #11588, PR #11590 — both open,
  maintainer-approved, awaiting merge): CE framework, 28 requirements
  (16 automated, 12 explicitly non-automatable), 30 unique checks;
  GDPR framework, 3 requirements (Articles 25/30/32), 51 unique checks.
- This paper's reference schema (evidence-class taxonomy, richer requirement
  decomposition — not submitted to Prowler, described as the paper's own
  contribution): CE, 18 requirements, 64 unique checks; GDPR, 10 requirements
  (Articles 5(1)(f), 25, 30, 32(a–d), 33, 34, 35), 89 unique checks
  (includes 13 checks folded in from the upstream-approved mapping).
- Combined reference-schema union: **114/191 Azure checks (59.7%) exercised;
  39 checks shared** between the two baselines.
- CRIS-SME CE mapping: 106 questions, 62 technical, 28 cloud-supported
  overall / 22 technical cloud-supported.
- Checkov (related work): IaC-static, 244 Terraform + 195 ARM Azure checks,
  no regulatory mappings in OSS.
```

## Proposed replacement text for `01-paper-material-pack.md`, §1

Replace the opening paragraph and headline-numbers paragraph with:

```markdown
## 1. Status: two artifacts — a Prowler contribution and a richer reference schema

Two related but distinct artifacts exist. **Contributed upstream to Prowler**
(`prowler-cloud/prowler`, PRs #11588 and #11590, both open and approved by
maintainers as of 2026-07-15): a CE 3.3 framework (28 requirements, 30 unique
checks, using Prowler's existing `AssessmentStatus`/`CloudApplicability`
attribute idiom) and a GDPR framework (3 requirements — Articles 25/30/32 —
51 unique checks, matching the structure of Prowler's pre-existing AWS-only
GDPR mapping). These are real, live, reviewed PRs — citable as "contributed
to Prowler (under review)".

Separately, this paper defines a **richer reference schema** (this repository,
not submitted to Prowler): CE, 18 requirements decomposed with a fine-grained
evidence-class `Type` attribute (direct_cloud / inferred_cloud /
endpoint_required / policy_required / manual_required) and per-requirement
`Comment` rationale, 64 unique checks; GDPR, 10 requirements spanning
Articles 5(1)(f), 25, 30, 32(a–d) decomposed, 33, 34, 35, 89 unique checks.
The evidence-class taxonomy design note below describes *this* schema, not
the upstream contribution — frame it as the paper's own methodological
contribution, informed by and partly validated against the upstream review
(13 of the reference schema's GDPR checks were confirmed correct by
independent maintainer review during the #11590 approval process).

**Headline numbers for the paper:** the reference schema exercises **114 of
Prowler's 191 Azure checks (59.7%)**, with 39 checks shared between the two
baselines (evidence reuse across frameworks). The narrower, upstream-approved
contribution exercises 69 checks (36%) with 12 shared.
```

## Real evaluation data (Prowler half) — captured 2026-07-15

Baseline scan against a live university-affiliated Azure subscription
(tenant and subscription identifiers withheld from this pack; the paper should
describe it as "a live university-affiliated Azure subscription"), **before**
the lab-provisioning script was run (near-empty subscription — only
IAM/Entra/Defender/Monitor findings, since no storage/network/database
resources existed yet):

| Framework | Checks executed | Runtime | Result |
|---|---|---|---|
| Cyber Essentials 3.3 (`--compliance cyber_essentials_3.3`) | 10 (of 30 mapped) | 1m59s | 70% PASS (7) / 30% FAIL (3) |
| GDPR Azure (`--compliance gdpr_azure`) | 13 (of 51 mapped) | 1m36s | 38.5% PASS (5) / 61.5% FAIL (8) |

Mark this explicitly as a **baseline, pre-lab** measurement in the paper; the
main evaluation numbers should come from a second run after the lab-provisioning
script (`provision-ce-gdpr-lab.sh`) is deployed, which exercises the
storage/network/database/App Service checks this baseline couldn't reach.
Raw CSV/OCSF output was deliberately **not** copied into this pack: it contains
live tenant/subscription identifiers and resource-level findings, and this pack
is intended to be shared with external writing sessions. As of 2026-07-15 the
raw files still exist at
`/tmp/claude-1000/-home-muhammad-ibrahim-Github-prowler/b270dd7c-b3dd-4244-923e-ae04ef5e033d/scratchpad/results-baseline/`
— that location does not survive a reboot, so if the raw evidence is wanted,
copy it to a private location outside this pack before rebooting. The aggregate
numbers in the table above are the only figures the paper needs.
