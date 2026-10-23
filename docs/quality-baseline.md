# Quality Baseline

Updated 23 October 2026. Local measurements and commit-specific hosted results
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
selected-report API cases brought the preceding total to 926. Twenty-two managed
worker/cancellation cases brought the preceding total to 948. Fifteen streaming
output-budget cases brought the preceding total to 963. Nineteen state-commit
failure-injection cases brought the preceding total to 982. Fifteen SQLite lock
retry cases brought the preceding total to 997. Eleven readiness cases and two
process-disappearance checks bring the current total to 1,010. These include native
process-group cleanup, queued/active cancellation, publication exclusion,
shutdown admission, signal handling, persisted recovery, pipe backpressure,
exact/over-budget output, text compatibility, unpublished noisy-worker results,
save-before-cache ordering, rejected completion/cancellation writes, bounded
contention retries, transaction rollback, connection cleanup, write-readiness and
shutdown/error projections. Coverage
measures the whole `cris_sme` package, including unimported modules, with branches
enabled and no module omit list. Scripts, frontend and child-process execution
are outside this measurement. Coverage.py standard exclusions apply (9 lines).

| Measure | Executed / total | Percentage |
| --- | --- | --- |
| Statements | 10,516 / 12,290 | 85.57% |
| Branches | 2,672 / 3,872 | 69.01% |
| Combined coverage.py metric | 13,188 / 16,162 | 81.60% |

Both Python versions passed all 1,010 tests and produced these measurements.
CI requires 78% **combined** coverage,
not 78% branches or a per-module guarantee. JSON/XML evidence is retained for
seven days. Supervisor behavior tested in subprocesses does not contribute to
its in-process coverage. Azure SQL SDK imports emitted three escape-sequence
warnings on the first clean run; they did not fail tests.

Ruff F/E9 checks cover `src`, `tests`, `scripts` and `setup.py`. Mypy checks
fourteen entry/runtime modules: the assessment and AzureGoat entry scripts,
run repository, supervisor, browser policy, public progress, request validation,
worker environment, state ownership, managed worker, data paths, and control definitions/registry/validation.
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
| Statements | 728 / 1,189 | 61.22% | 58% |
| Branches | 696 / 1,486 | 46.83% | 44% |
| Functions | 207 / 446 | 46.41% | 42% |
| Lines | 685 / 1,081 | 63.36% | 60% |

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

Seven Chromium Playwright tests passed against the self-host build:

1. Switch report, retain selection across reload, navigate to artifacts, and
   retrieve the artifact belonging to the selected report.
2. Handle an unavailable backend with explicit missing-report/disconnected states.
3. Submit an authorized mock scan, observe completion, and select its new report.
4. Display a failed mock scan without replacing the previously selected report.
5. Select a saved public scan, retain selection across reload, retrieve its export,
   and select a newly completed authorized scan.
6. On a 390px mobile viewport, select public history, show missing-result errors
   without stale findings and navigate to another view. Check page overflow.
7. Cancel an active mock cloud scan, retain the selected completed report, stop
   polling at cancellation and enable another submission. Check mobile overflow.

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
browser follow-up [hosted run on fd111fd](https://github.com/m-khan-97/CRIS-SME/actions/runs/36996750117)
also passed all configured jobs. Cloud cancellation has local measurements above;
hosted results always
apply to the recorded commit. These gates do not constitute identity authentication
or a browser-engine/proxy penetration test.

23 October: technical changes are published in `2883249`, `18b9962` and `c1c2fcc`.
The [static-site build on c1c2fcc](https://github.com/m-khan-97/CRIS-SME/actions/runs/39926067368)
passed. The [explicit full-matrix run](https://github.com/m-khan-97/CRIS-SME/actions/runs/39926354445)
has passing Python 3.11/3.12 and container jobs; its console job is still running
at this recording. Those hosted results concern the 997-test baseline, not the
subsequent local readiness increment. Readiness and the process-observation race
fix passed 1,010 tests locally on each interpreter. Frontend revalidation passed
56 unit tests, seven Chromium workflows and full lint before publication.

A read-only GitHub settings check found no classic protection for `main` and no
repository rulesets. Required merge checks still need administrator configuration;
workflow YAML alone does not enforce them. No repository settings were changed.

See [CI documentation](ci-cd-and-vercel.md), the
[capability register](capability-evidence.md) and the [roadmap](roadmap.md).
