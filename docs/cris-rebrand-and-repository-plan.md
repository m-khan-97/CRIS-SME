# CRIS Rebrand and Repository Plan

This note defines a controlled path from **CRIS-SME** to a broader **CRIS** product family without breaking the working codebase, paper artifacts, demo console, or current GitHub links.

## Recommendation

Keep this repository named `CRIS-SME` until the Cyber Essentials paper package and live Azure evaluation work are frozen.

Use **CRIS** as the umbrella brand now, and treat **CRIS-SME** as the first edition:

- **CRIS**: the core evidence-driven cloud risk intelligence platform.
- **CRIS-SME**: the SME-focused edition with Cyber Essentials, insurance-readiness, budget-aware remediation, and lightweight governance reporting.
- **CRIS-CNI**: the future UKRI/CNI research track for NCSC CAF outcome readiness and critical-sector operational validation.
- **CRIS-Cloud**: optional later name for the provider-neutral engine if AWS/GCP become first-class collectors.

This avoids a disruptive rename while still positioning the project as more than an SME-only tool.

## Proposed GitHub Organization

Create a GitHub organization when there are at least two active repositories or collaborators need role-based access. A clean structure would be:

| Repository | Purpose | Visibility |
| --- | --- | --- |
| `cris-sme` | Current production-shaped research/product repo | Public or private depending paper strategy |
| `cris-cni` | UKRI/CNI demonstrator branch or separate funded-project repo | Private until application or partner approval |
| `cris-research-artifacts` | Frozen paper datasets, figures, ledgers, and reproducibility bundles | Public after anonymization |
| `cris-docs` | Product docs, website, case-study pages, and grant collateral | Public when ready |
| `cris-labs` | Controlled Azure/AWS/GCP lab templates and teardown scripts | Public if no sensitive defaults |

Suggested organization names:

- `cris-security`
- `cris-cloud`
- `cris-risk`
- `cris-assurance`

Avoid names that lock the project to one market, such as `cris-sme-only` or `cyber-essentials-cris`.

## Naming Conventions

Use stable names at different layers:

| Layer | Current | Future-safe convention |
| --- | --- | --- |
| Brand | CRIS-SME | CRIS |
| Edition | SME cloud governance | CRIS-SME |
| Python package | `cris_sme` | Keep until a major-version migration |
| CLI/module | `python -m cris_sme.main` | Keep compatibility alias if future `cris` package is added |
| Reports | CRIS-SME report | CRIS-SME report for SME edition; CRIS report for generic platform outputs |
| Cyber Essentials workflow | CRIS-SME CE workflow | CRIS-SME Cyber Essentials pre-assessment |
| UKRI/CNI path | not yet separate | CRIS-CNI |

The package name should not be renamed casually. Python imports, test paths, CI workflows, artifact names, and paper reproduction commands already depend on `cris_sme`.

## Migration Strategy

Use a three-stage migration if the project moves to a CRIS organization.

### Stage 1: Brand-Layer Repositioning

- Keep repository and package names unchanged.
- Update README wording so CRIS-SME is described as the SME edition of CRIS.
- Add a product-family diagram or short table in docs.
- Keep all artifact filenames unchanged for paper reproducibility.

### Stage 2: Organization Move

- Move the existing repo to the organization as `cris-sme`.
- Keep GitHub redirects from `m-khan-97/CRIS-SME` active.
- Protect `main`, enable branch rules, and add collaborators by role.
- Keep CI, Vercel, and any GitHub Actions secrets verified after transfer.

### Stage 3: Core Package Split

Only do this when AWS/GCP or CNI work makes the split worthwhile.

- Create a new `cris` core package for provider-neutral models, scoring, evidence taxonomy, and reporting primitives.
- Keep `cris_sme` as an edition package that imports from `cris`.
- Provide a compatibility layer so existing commands continue to work.
- Freeze paper artifacts before any package rename.

## Compatibility Rules

- Do not rename `src/cris_sme` before the Cyber Essentials paper is submitted.
- Do not rename generated artifact files used by the paper package.
- Do not rename existing GitHub Actions workflows unless a workflow migration PR proves equivalent output.
- Keep `CRIS_SME_*` environment variables until a major-version boundary.
- If new `CRIS_*` variables are added, support both names for at least one release cycle.

## Risks

- **Broken reproducibility:** paper commands and artifact paths could drift if package names change too early.
- **Confused positioning:** using CRIS and CRIS-SME interchangeably without defining edition boundaries can make the project look unfocused.
- **GitHub integration drift:** Vercel, Actions secrets, Pages, branch protection, and badges may need reconfiguration after organization transfer.
- **Premature abstraction:** splitting a core package before AWS/GCP/CNI requirements are real could create unnecessary maintenance overhead.

## Decision

For now:

1. Keep the repository as `CRIS-SME`.
2. Use CRIS as the umbrella brand in strategic documents.
3. Treat SME, Cyber Essentials, and UKRI/CNI as editions or tracks.
4. Revisit an organization transfer after the current paper package and local API/frontend work are stable.

