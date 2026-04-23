# CI/CD and Vercel Delivery

This document describes the CRIS-SME validation, release, and static-hosting delivery model.

The repository keeps GitHub Actions for engineering quality and artifact generation, while Vercel (Option 1 direct Git integration) is the hosting target for the static dashboard/report site.

## Workflow Topology

| Workflow | Trigger | Purpose |
| --- | --- | --- |
| `pr-validation.yml` | `pull_request` | Merge quality gate (lint, type-check, tests, mock pipeline, output checks) |
| `build-static-site-artifacts.yml` | `push` to `main`, `workflow_dispatch` | Build deterministic static bundle and upload `dist/` artifact |
| `release.yml` | tags `v*.*.*`, `workflow_dispatch` | Build release bundle and publish GitHub Release assets |
| `scheduled-assessment.yml` | `schedule`, `workflow_dispatch` | Run recurring assessments with safe collector fallback |
| `codeql.yml` | `push`, `pull_request`, `schedule` | CodeQL security analysis |
| `dependency-review.yml` | `pull_request` | Dependency risk review |
| `reusable-python-quality.yml` | `workflow_call` | Shared Python quality checks |

## Security and Permissions Model

Workflows use explicit least-privilege permissions:

- default read-only permissions where possible
- release publishing scoped to `contents: write`
- no GitHub Pages deployment permissions are required

## Static Bundle Build Path

The standardized bundle entrypoint is:

```bash
python scripts/build_static_site_bundle.py --collector mock --reports-dir outputs/reports --figures-dir outputs/figures --dist-dir dist
```

This command:

1. runs the deterministic assessment pipeline
2. generates dashboard/report outputs
3. assembles deployable static files in `dist/site`
4. writes build metadata in `dist/manifests/build-metadata.json`

## Static Bundle Layout

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

## Vercel Option 1 Setup (Direct Git Integration)

Repository-side readiness is already implemented via `vercel.json`.

### Recommended Vercel project settings

- Framework Preset: `Other`
- Install Command: `pip install -r requirements.txt`
- Build Command: `python scripts/build_static_site_bundle.py --collector mock --reports-dir outputs/reports --figures-dir outputs/figures --dist-dir dist`
- Output Directory: `dist/site`

### Vercel dashboard steps

1. Import this GitHub repository in Vercel.
2. Confirm the project uses `main` as production branch.
3. Verify the build/output settings above (or rely on `vercel.json`).
4. Trigger deployment.

## Scheduled Assessment Behavior

`scheduled-assessment.yml` supports `auto`, `mock`, and `azure` modes.

Safety behavior:

- defaults to mock when Azure credentials are unavailable
- falls back to mock if Azure collector execution fails
- always uploads generated report/figure artifacts for traceability

## Local Reproduction

```bash
PYTHONPATH=src python3 scripts/run_assessment_snapshot.py --collector mock
python3 scripts/build_static_site_bundle.py --collector mock --reports-dir outputs/reports --figures-dir outputs/figures --dist-dir dist
python3 -m http.server 8080 --directory dist/site
```

Open:

- `http://127.0.0.1:8080/`
- `http://127.0.0.1:8080/dashboard.html`
- `http://127.0.0.1:8080/report.html`

## Notes on Responsibility Boundaries

- GitHub Actions: validation, artifact generation, release engineering, security scanning.
- Vercel: static hosting and public deployment surface.

This split avoids repository-level dependency on GitHub Pages settings while preserving a strong CI/CD posture.
