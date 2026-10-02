# Quality Baseline

Updated 2 October 2026. Local measurements and commit-specific hosted results
are distinguished below. Neither establishes independent security validation or
enterprise readiness.

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
preflight cases, followed by 12 release-checksum cases. Replay and request-body
regressions added 61 cases; browser-policy tests add 56 more, request-deadline
tests add 13, outbound-probe boundaries add 20, and pinned-transport tests add
36. Artifact access adds 28 cases; header deadlines and connection admission add
17. Bounded artifact/report reads add 21 cases and scan admission adds 16.
Error-disclosure checks add 26 cases, public run projections add 31, request
validation adds 65, worker environments add 15, and state ownership/startup
recovery adds 24. Cloud run namespaces add 17 checks, including a real mock-mode
child assessment and artifact retrieval. Public run storage adds 19 checks for
retention, restart, failures and publication boundaries. Five public-history and
selected-report API cases bring the current total to 926 passing
on each. Coverage
measures the whole `cris_sme` package, including unimported modules, with branches
enabled and no module omit list. Scripts, frontend and child-process execution
are outside this measurement. Coverage.py standard exclusions apply (9 lines).

| Measure | Executed / total | Percentage |
| --- | --- | --- |
| Statements | 10,320 / 12,092 | 85.35% |
| Branches | 2,608 / 3,804 | 68.56% |
| Combined coverage.py metric | 12,928 / 15,896 | 81.33% |

Both Python versions produced these measurements and passed all 926 tests.
CI requires 78% **combined** coverage,
not 78% branches or a per-module guarantee. JSON/XML evidence is retained for
seven days. Supervisor behavior tested in subprocesses does not contribute to
its in-process coverage. Azure SQL SDK imports emitted three escape-sequence
warnings on the first clean run; they did not fail tests.

Ruff F/E9 checks cover `src`, `tests`, `scripts` and `setup.py`. Mypy checks
thirteen entry/runtime modules: the assessment and AzureGoat entry scripts,
run repository, supervisor, browser policy, public progress, request validation,
worker environment, state ownership, data paths, and control definitions/registry/validation.
Imported modules use silent checking and missing-import tolerance; this is not a
whole-backend strict type gate.

## Frontend Coverage

All 56 Vitest component/unit tests passed. Four public-history tests cover saved
selection, exact exports, missing results and new completed scans. Route smoke tests wait for settled
report or missing-data states, rather than passing on loading text. Dedicated
fixtures cover populated governance, native-validation and trend views, including
nullable scores, filtering, missing sections and errors. Explicit test cleanup
prevents DOM state leaking between cases.

| Measure | Executed / total | Percentage | CI floor |
| --- | --- | --- | --- |
| Statements | 727 / 1,183 | 61.45% | 58% |
| Branches | 695 / 1,469 | 47.31% | 44% |
| Functions | 207 / 443 | 46.72% | 42% |
| Lines | 684 / 1,075 | 63.62% | 60% |

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

Six Chromium Playwright tests passed against the self-host build:

1. Switch report, retain selection across reload, navigate to artifacts, and
   retrieve the artifact belonging to the selected report.
2. Handle an unavailable backend with explicit missing-report/disconnected states.
3. Submit an authorized mock scan, observe completion, and select its new report.
4. Display a failed mock scan without replacing the previously selected report.
5. Select a saved public scan, retain selection across reload, retrieve its export,
   and select a newly completed authorized scan.
6. On a 390px mobile viewport, select public history, show missing-result errors
   without stale findings and navigate to another view. Check page overflow.

Network interception supplies synthetic fixtures and rejects external requests.
No cloud credentials or customer scans are involved. CI retains screenshots,
failure traces and HTML reports for seven days. Desktop/mobile screenshots were
inspected locally. Other browser engines remain outside this gate. The test
preview server shuts down after completion.

## Dependency And Delivery Limits

Targeted compatible frontend dependency updates reduced the clean-install npm
audit result from ten advisories to zero on 26 September. This is an advisory
snapshot, not proof that all dependencies are secure. No forced major upgrade was
used. Python lock fingerprints and the 36-control metadata gate passed.

Commit `8eb0595` was pushed to main. Its
[hosted static-site run](https://github.com/m-khan-97/CRIS-SME/actions/runs/36265166338)
passed the reusable Python 3.11 quality job and static build. This does not run
the full PR matrix, console browser gate or container job; those hosted gates
were initially open. The subsequent full
[run on 5fb89ce](https://github.com/m-khan-97/CRIS-SME/actions/runs/36267721918)
passed the console/browser and container jobs. Both Python jobs passed tests,
package installation and mock assessment, but failed the replay gate: replay
omitted resource links included in runner-produced snapshots. Commit `8c99b8a`
fixes this and checks captured finding contents against their stored hash.
Local replay of the failing snapshot now passes. The full
[hosted rerun on 8c99b8a](https://github.com/m-khan-97/CRIS-SME/actions/runs/36281224558)
also passed: both Python versions, installed packages, mock assessment/replay,
console/browser and container jobs. This establishes execution of the configured
gates for that commit, not independent rule correctness or tenant isolation.
GitHub reported action-runtime and upcoming runner-image migration warnings;
review those upgrades separately rather than treating a passing run as permanence.
Commit `5ce5d3a` publishes the subsequent API hardening and run-storage changes.
The [full hosted run](https://github.com/m-khan-97/CRIS-SME/actions/runs/36995365921)
passed both Python versions, console/browser and Docker checks. The public-history
browser follow-up has local measurements recorded above; hosted results always
apply to the recorded commit. These gates do not constitute identity authentication
or a browser-engine/proxy penetration test.

A read-only GitHub settings check found no classic protection for `main` and no
repository rulesets. Required merge checks still need administrator configuration;
workflow YAML alone does not enforce them. No repository settings were changed.

See [CI documentation](ci-cd-and-vercel.md), the
[capability register](capability-evidence.md) and the [roadmap](roadmap.md).
