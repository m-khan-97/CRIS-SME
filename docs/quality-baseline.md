# Quality Baseline

Measured 26 September 2026. These are local results and configured CI gates,
not hosted CI success, independent security validation or enterprise readiness.

## Runtime Matrix

Backend checks target Python 3.11 and 3.12 on Ubuntu. Local runs used Python
3.11.15 and 3.12.3 with hash-locked development dependencies. Package metadata
allows Python >=3.11; newer interpreters and other operating systems are not
qualified by this matrix. The sdist-to-wheel smoke test passed on Python 3.12,
including an installed mock assessment outside the source checkout.

Console checks used Node 22.23.3, matching the Node 22 CI major. A clean
`npm ci`, full zero-warning ESLint, TypeScript project builds and production,
demo and self-host bundles passed. Test/browser configuration is also type-checked.

## Python Coverage

```bash
python -m pip install --require-hashes -r requirements/dev.txt
python -m pytest -q --cov --cov-report=term --cov-report=json:coverage.json --cov-report=xml:coverage.xml
```

The P0-06 baseline was 384 passing tests on each interpreter. P0-07 added 22
capability-register tests; P0-08 added 16 inventory/governance checks and 22 release
preflight cases, followed by 12 release-checksum cases. The current total is 456
passing on each. Coverage
measures the whole `cris_sme` package, including unimported modules, with branches
enabled and no module omit list. Scripts, frontend and child-process execution
are outside this measurement. Coverage.py standard exclusions apply (24 lines).

| Measure | Executed / total | Percentage |
| --- | --- | --- |
| Statements | 9,592 / 11,473 | 83.60% |
| Branches | 2,362 / 3,586 | 65.87% |
| Combined coverage.py metric | 11,954 / 15,059 | 79.38% |

Both interpreters produced this result. CI requires 78% **combined** coverage,
not 78% branches or a per-module guarantee. JSON/XML evidence is retained for
seven days. Supervisor behavior tested in subprocesses does not contribute to
its in-process coverage. Azure SQL SDK imports emitted three escape-sequence
warnings on the first clean run; they did not fail tests.

Ruff F/E9 checks cover `src`, `tests`, `scripts` and `setup.py`. Mypy checks
eight entry/runtime modules: the assessment and AzureGoat entry scripts,
run repository, supervisor, data paths, and control definitions/registry/validation.
Imported modules use silent checking and missing-import tolerance; this is not a
whole-backend strict type gate.

## Frontend Coverage

All 52 Vitest component/unit tests passed. Route smoke tests now wait for settled
report or missing-data states, rather than passing on loading text. Dedicated
fixtures cover populated governance, native-validation and trend views, including
nullable scores, filtering, missing sections and errors. Explicit test cleanup
prevents DOM state leaking between cases.

| Measure | Executed / total | Percentage | CI floor |
| --- | --- | --- | --- |
| Statements | 686 / 1,151 | 59.60% | 58% |
| Branches | 640 / 1,422 | 45.00% | 44% |
| Functions | 185 / 427 | 43.32% | 42% |
| Lines | 643 / 1,043 | 61.64% | 60% |

V8 coverage includes runtime source files, even unimported ones. Tests, ambient
Vite declarations and the two type-only API contract files are excluded. Browser
test execution is not included in these figures. These are initial regression
floors, not adequate coverage of every interaction; several assurance pages
still need richer populated fixtures and negative-path tests.

Report interfaces replace untyped page access. They are compile-time contracts,
**not runtime validation of imported JSON**. Full ESLint has zero errors and
warnings; `lint:core` now aliases the full gate. Generated coverage/browser output
is ignored by lint, but no source rules were disabled for this migration.

## Browser Workflows

Four desktop Chromium Playwright tests passed against the self-host build:

1. Switch report, retain selection across reload, navigate to artifacts, and
   retrieve the artifact belonging to the selected report.
2. Handle an unavailable backend with explicit missing-report/disconnected states.
3. Submit an authorized mock scan, observe completion, and select its new report.
4. Display a failed mock scan without replacing the previously selected report.

Network interception supplies synthetic fixtures and rejects external requests.
No cloud credentials or customer scans are involved. CI retains screenshots,
failure traces and HTML reports for seven days. Mobile and other browser engines
are not part of this gate. The test preview server shuts down after completion.

## Dependency And Delivery Limits

Targeted compatible frontend dependency updates reduced the clean-install npm
audit result from ten advisories to zero on 26 September. This is an advisory
snapshot, not proof that all dependencies are secure. No forced major upgrade was
used. Python lock fingerprints and the 36-control metadata gate passed.

Commit `8eb0595` was pushed to main. Its
[hosted static-site run](https://github.com/m-khan-97/CRIS-SME/actions/runs/36265166338)
passed the reusable Python 3.11 quality job and static build. This does not run
the full PR matrix, console browser gate or container job; those hosted gates
remain open. Container execution has not been independently reverified during
this increment. The subsequent P0-08 additions are locally verified separately.

A read-only GitHub settings check found no classic protection for `main` and no
repository rulesets. Required merge checks still need administrator configuration;
workflow YAML alone does not enforce them. No repository settings were changed.

See [CI documentation](ci-cd-and-vercel.md), the
[capability register](capability-evidence.md) and the [roadmap](roadmap.md).
