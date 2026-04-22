# CI/CD and GitHub Pages Delivery

This document describes CRIS-SME's GitHub-native delivery model.

The goal is to keep the project easy to validate, easy to release, and easy to demo without introducing unnecessary enterprise complexity.

## Workflow Topology

| Workflow | Trigger | Primary Purpose |
| --- | --- | --- |
| `pr-validation.yml` | `pull_request` | Merge-quality gate (lint, type-check, tests, mock run, output checks) |
| `build-pages-artifacts.yml` | `push` to `main`, `workflow_dispatch` | Build report/dashboard outputs and assemble `dist/site` bundle |
| `deploy-pages.yml` | `workflow_call` | Reusable GitHub Pages deploy job from built artifact |
| `release.yml` | tags `v*.*.*`, `workflow_dispatch` | Build release bundle and publish GitHub Release assets |
| `scheduled-assessment.yml` | `schedule`, `workflow_dispatch` | Run periodic assessment generation and archive artifacts |
| `codeql.yml` | `push`, `pull_request`, `schedule` | Static security analysis with CodeQL |
| `dependency-review.yml` | `pull_request` | Dependency risk review for incoming changes |
| `reusable-python-quality.yml` | `workflow_call` | Shared Python quality pipeline used by multiple workflows |

## Security and Permissions Model

CRIS-SME workflows follow least-privilege defaults:

- global `permissions` are set explicitly per workflow
- jobs that only read source use `contents: read`
- only Pages deployment jobs receive `pages: write` and `id-token: write`
- only release publishing jobs receive `contents: write`
- pull-request dependency review uses scoped permissions for PR comments/status

## Quality Gate Behavior

`reusable-python-quality.yml` performs:

1. dependency install
2. critical lint checks
3. script-focused type checks
4. deterministic test suite
5. optional mock pipeline execution
6. generated output verification
7. docs sanity checks

This reusable pipeline is used by:

- `pr-validation.yml`
- `build-pages-artifacts.yml`
- `release.yml`

## Pages Build and Publication

`build-pages-artifacts.yml` executes:

1. quality validation
2. deterministic mock assessment generation
3. static site assembly via `scripts/build_pages_site.py`
4. artifact upload (`pages-site-bundle`)
5. deployment via reusable `deploy-pages.yml`

`deploy-pages.yml` performs:

1. GitHub Pages environment configuration
2. artifact retrieval
3. Pages artifact upload (`dist/site`)
4. deployment to the `github-pages` environment

## Site Bundle Layout

The generated Pages bundle is intentionally clean and static:

```text
dist/
├── manifests/
│   └── build-metadata.json
└── site/
    ├── index.html
    ├── dashboard.html
    ├── report.html
    ├── data/
    │   ├── build-metadata.json
    │   ├── cris_sme_dashboard_payload.json
    │   ├── cris_sme_report.json
    │   └── cris_sme_summary.txt
    └── assets/figures/
```

## Build Metadata Manifest

`dist/manifests/build-metadata.json` includes:

- commit SHA
- ref
- workflow run ID and run number
- actor
- build time
- Python version
- project version
- artifact checksums for key site files

This keeps published artifacts traceable and audit-friendly.

## Release Workflow

`release.yml` is tag-driven and semver-oriented:

- trigger: push tags matching `v*.*.*`
- optional manual dispatch with explicit `release_tag`
- produces packaged site/report archives
- publishes GitHub Release assets
- includes build metadata manifest in release artifacts

## Scheduled Assessment Behavior

`scheduled-assessment.yml` prioritizes safe execution:

- supports `auto`, `mock`, and `azure` modes
- defaults to `mock` when Azure credentials are unavailable
- gracefully falls back to `mock` if Azure execution fails
- uploads report and figure artifacts for inspection
- writes summary stats into workflow summary

## Local Reproduction

You can locally reproduce the Pages bundle generation:

```bash
PYTHONPATH=src python3 scripts/run_assessment_snapshot.py --collector mock
python3 scripts/build_pages_site.py --reports-dir outputs/reports --figures-dir outputs/figures --dist-dir dist
python3 -m http.server 8080 --directory dist/site
```

## Enabling GitHub Pages

1. Go to repository **Settings** -> **Pages**.
2. Set Source to **GitHub Actions**.
3. Run `build-pages-artifacts.yml` (push to `main` or manual dispatch).
4. Access the published site URL from the `github-pages` deployment environment.
