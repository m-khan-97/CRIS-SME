# Quality Baseline

Measured 24 September 2026. P0-06 is in progress, not complete. This records
reproducible local evidence and configured CI gates, not hosted CI success or
independent security validation.

## Runtime Matrix

PR backend jobs now target Python 3.11 and 3.12 on Ubuntu. Local measurements
below used Python 3.12.3; the 3.11 hosted result remains pending. Package metadata
allows Python >=3.11, but newer interpreters and other operating systems are not
yet qualified by this matrix. The existing package smoke check builds an sdist,
builds its wheel and runs the installed wheel outside the checkout.

PR console and static-site CI use Node 22, matching the container frontend builder.
Local console checks used Node 20.20.2; a passing local run is not evidence for
the Node 22 hosted job. Dependencies install through `npm ci` and hash-locked pip
profiles; upgrading them is a separate reviewed change.

## Python Coverage

```bash
python -m pip install --require-hashes -r requirements/dev.txt
python -m pytest -q --cov --cov-report=term --cov-report=json:coverage.json --cov-report=xml:coverage.xml
```

Baseline: 384 tests passed. Measurement covers the whole `cris_sme` package,
including unimported modules, with branches enabled and no module omit list.
Scripts, frontend code and child-process execution are outside this measurement.
Coverage.py's standard exclusions still apply (24 excluded lines in this run).

| Measure | Executed / total | Percentage |
| --- | --- | --- |
| Statements | 9,592 / 11,473 | 83.60% |
| Branches | 2,362 / 3,586 | 65.87% |
| Combined coverage.py metric | 11,954 / 15,059 | 79.38% |

The initial CI floor is 78% **combined**, allowing modest interpreter variance.
It is not a 78% branch threshold, a per-module guarantee or a security score.
CI retains JSON/XML reports for seven days, including when tests fail after
producing a report. The tests step fails when the combined floor is missed.
Subprocess-only supervisor checks can pass while its in-process measured coverage
is zero; improve measurement before treating that as missing behavioral tests.

## Frontend And Static Checks

PR CI installs the console lockfile, runs its 36 jsdom route/component smoke tests,
and type-checks/builds production, demo and self-host modes. These checks do not
launch a browser, validate actual navigation or prove scan/report workflows.
The current route tests can pass on nonempty loading states; stronger settled-data
assertions and real browser interaction tests remain required.

Backend lint covers `src`, `tests`, `scripts` and `setup.py` with Ruff F/E9 rules.
Mypy covers only the two workflow entry scripts with silent imported-module
checking; it is not a whole-backend strict type gate. Console builds run `tsc -b`.

Full console ESLint currently reports 101 errors and 17 warnings, including
explicit `any`, React effect/static-component rules and fast-refresh boundaries.
`npm run lint` is not yet a required PR gate; no rules were disabled or errors
suppressed to create a passing result. `npm ci` reported 10 dependency advisories
(4 moderate, 6 high); severity totals alone do not establish exploitability.
Triage affected dependency paths and fixes separately before asserting release
security. Do not run blind `npm audit fix --force` upgrades.

## Remaining P0-06 Work

Progress, 25 September: shared components/hooks/API/context/tests plus Attack Paths
and Public Exposure now pass `npm run lint:core` with zero warnings; PR CI requires
that scoped gate. No existing lint rules were disabled. The full-console backlog
is now 95 errors and 13 warnings. Severity normalization moved out of the component
module, attack-path memo dependencies are stable, and public-exposure counters have
explicit types. Animation handles invalid durations and recovers from nonfinite
targets; seven regression cases bring the console suite to 43 passing tests.
The self-host TypeScript/build check also passes locally. Browser workflows remain
pending, and the scoped gate must not be presented as whole-console lint success.

1. Resolve console lint findings and enable a required full lint gate.
2. Add Playwright browser workflows: report selection, findings navigation,
   artifact retrieval, missing backend and mocked scan lifecycle. Use generated
   fixtures, not customer credentials or automatic live cloud scans.
3. Measure frontend coverage and improve async component assertions.
4. Expand Python type checking in reviewed module groups; document remaining scope.
5. Triage dependency advisories and obtain passing hosted matrix/container jobs.
6. Configure required branch checks in repository settings; workflow YAML alone
   does not enforce merge protection.

See [CI documentation](ci-cd-and-vercel.md) and the [roadmap](roadmap.md).
