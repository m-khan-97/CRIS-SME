# Paper Pack — Compliance-as-Code for Cloud Security Baselines (GDPR + Cyber Essentials, Azure)

Instructions for the writing assistant: this bundle contains everything needed
to draft the WIP paper. Read `01-paper-material-pack.md` first — it contains
the verified facts, final numbers, the recommended paper structure (§10), and
the framing decision (§11: one methodology, two implementations).

## Target abstract (author's draft — needs one edit)

> Compliance-as-Code for Cloud Security Baselines: Automating GDPR and Cyber
> Essentials Verification in Azure
>
> [Original abstract as drafted by the author — see note below on the one
> required change.]

**Required abstract edit:** change "implemented as open-source contributions
to the Prowler cloud security posture framework" to "implemented in an
open-source assessment engine (CRIS-SME) and contributed as compliance
framework mappings to the Prowler cloud security posture framework" — per the
two-implementation framing in `01`, §11.

## File manifest

| File | What it is | Use in paper |
|---|---|---|
| `01-paper-material-pack.md` | Master material: verified facts about Prowler/Checkov, final artifact stats, mapping methodology, evaluation design, limitations, related-work table, section-by-section structure | Primary source for every section |
| `02-artifact-cyber_essentials_3.3_azure.json` | Superseded draft — see `09`. Kept for history only; do not cite numbers from this file | — |
| `03-artifact-gdpr_azure.json` | Superseded draft — see `10`. Kept for history only; do not cite numbers from this file | — |
| `04-ce-paper-skeleton.md` | Earlier CRIS-SME CE paper skeleton — reuse its guardrail language ("pre-population, not certification") and RQ framing | Introduction, method, ethics/claims discipline |
| `05-ce-question-coverage-analysis.md` | Evidence-class taxonomy definitions + measured CE question coverage (106 questions; 5 direct / 23 inferred / 24 endpoint...) | Methodology + CRIS-SME evaluation numbers |
| `06-three-mode-evaluation-comparison.md` | Synthetic / live-tenant / vulnerable-lab evaluation with real score tables | Evaluation section (CRIS-SME half) |
| `07-ce-evaluation-protocol.md` | The CE evaluation protocol used for the CRIS-SME measurements | Evaluation method description |
| `08-cris-compliance-mapping.md` | CRIS-SME's 13-framework compliance interpretation layer | Background on the reference implementation |
| `09-merged-artifact-cyber_essentials_3.3.json` | **This paper's reference schema** (not submitted to Prowler): CE v3.3, 18 requirements, 64 checks, evidence classes in `Type` attributes | Implementation section; quote requirement examples |
| `10-merged-artifact-gdpr_azure.json` | **This paper's reference schema** (not submitted to Prowler): GDPR Arts. 5(1)(f), 25, 30, 32(1)(a–d), 33–35; 10 requirements, 89 checks (76 original + 13 folded in from the upstream-approved PR mapping, re-verified) | Implementation section |
| `11-merge-reconciliation-and-corrected-numbers.md` | Reconciliation of the reference schema against the actual upstream PRs; derivation of every number below; real baseline scan data (2026-07-15) | Evaluation section (Prowler half); audit trail for the numbers in this file |

## Key verified numbers (do not invent others)

- Prowler Azure: 191 checks, 22 services; **no prior CE framework for any
  provider; prior GDPR is AWS-only, 3 articles**.
- Contributed to Prowler upstream (PR
  [#11588](https://github.com/prowler-cloud/prowler/pull/11588), PR
  [#11590](https://github.com/prowler-cloud/prowler/pull/11590) — both open,
  maintainer-approved, awaiting merge): CE framework, 28 requirements
  (16 automated, 12 explicitly non-automatable), 30 unique checks; GDPR
  framework, 3 requirements (Articles 25/30/32), 51 unique checks.
- This paper's reference schema (evidence-class taxonomy, richer requirement
  decomposition — files `09`/`10`, not submitted to Prowler, described as
  this paper's own contribution): CE, 18 requirements, 64 unique checks;
  GDPR, 10 requirements (Articles 5(1)(f), 25, 30, 32(a–d), 33, 34, 35),
  89 unique checks (includes 13 checks folded in from the upstream-approved
  mapping, all re-verified against the current Azure check inventory).
- Combined reference-schema union: **114/191 Azure checks (59.7%) exercised;
  39 checks shared** between the two baselines. (The narrower upstream
  contribution alone exercises 69/191 checks (36%), 12 shared.)
- CRIS-SME CE mapping: 106 questions, 62 technical, 28 cloud-supported
  overall / 22 technical cloud-supported.
- Checkov (related work): IaC-static, 244 Terraform + 195 ARM Azure checks,
  no regulatory mappings in OSS.

## Honest status — what is NOT yet done

The paper can be fully drafted now. Both blockers from the previous version
of this file are now resolved:

1. **Prowler evaluation runs**: a baseline scan (`--compliance
   cyber_essentials_3.3` / `gdpr_azure`) has been run against a live
   university-affiliated Azure subscription (identifiers withheld from this
   pack) — see `11` for the real numbers (10/13 checks
   executed respectively, since the subscription was still near-empty at
   scan time; a lab-provisioning script exists to exercise the remaining
   storage/network/database/App Service checks — re-run after deploying it
   for the main evaluation numbers, and replace the baseline figures below
   with the post-lab ones once available). The CRIS-SME half has real
   evaluation data (file `06`).
2. **Upstream PRs**: pushed. PR #11588 (Cyber Essentials) and PR #11590
   (GDPR) are open on `prowler-cloud/prowler` and both maintainer-approved
   as of 2026-07-15, awaiting merge. "Contributed to Prowler (under review)"
   is now accurate — but only for the narrower artifact (28 req/30 checks
   CE; 3 req/51 checks GDPR), not the richer reference schema in `09`/`10`.

## Claims discipline (non-negotiable)

- Never claim CE certification automation — verification of the
  cloud-infrastructure slice of technical controls only.
- Never claim GDPR compliance is established by passing checks — technical
  proxies for legal requirements; interpretation stays with the controller.
- CE is endpoint-heavy by design: the majority of the full scheme is NOT
  cloud-observable, and the paper must say so plainly (it is the point of
  the evidence-class taxonomy, not a weakness to hide).
- IASME question text is licensed: paraphrase only, no verbatim reproduction.
