# Frontend Architecture

CRIS-SME currently ships a generated interactive dashboard HTML, not a separate SPA service.

## Current Frontend Shape

- Dashboard payload generated in backend pipeline
- HTML dashboard generated with embedded payload
- Client-side filtering and rendering via vanilla JavaScript
- No API server required for local usage
- Static site bundling for platform-neutral publication (Vercel-ready)

## Files

- `src/cris_sme/reporting/dashboard.py`
  - payload builder
  - dashboard HTML builder
  - dashboard writers
- `scripts/build_pages_site.py`
  - assembles `dist/site` with landing page, dashboard page, report page, and data assets

## Why This Approach

Benefits for home-lab and research workflows:

- zero backend deployment overhead
- deterministic, reproducible report-to-dashboard rendering
- easy artifact sharing and archiving
- simple static hosting path for public demo usage

## Future Expansion Path

If needed, the current payload contract can back:

- React/TypeScript UI
- API-backed viewer
- lightweight hosted dashboard service

without rewriting core scoring/decision logic.
