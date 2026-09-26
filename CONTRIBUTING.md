# Contributing To CRIS-SME

Use [GitHub issues](https://github.com/m-khan-97/CRIS-SME/issues) for non-sensitive
bugs and proposals, and pull requests for changes. English reports are welcome.
For vulnerabilities, use the [security policy](SECURITY.md), not a public exploit
report. Contributors do not need cloud credentials to run the fixture tests.

## Before A Pull Request

Discuss substantial architecture or provider changes in an issue first. Keep
changes focused, describe the problem and behavior change, and include the exact
commands/results used to verify them. Explain compatibility and migration risks.
Add automated regression tests for bug fixes and tests for major new behavior,
including permission denial, missing evidence and failure paths where relevant.
Update affected docs, control metadata and capability limitations together.

Never include credentials, unredacted customer artifacts or unsupported claims
of independent validation. Use synthetic fixtures and preserve original evidence
provenance. Cloud tests require the account owner's explicit scoped authorization;
they are not part of ordinary PR validation.

## Local Checks

Use Python 3.11 or 3.12 in a virtual environment and Node 22. From the repository:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements/dev.txt
python scripts/lock_dependencies.py --check
ruff check src tests scripts setup.py --select F,E9
python -m pytest -q --cov
PYTHONPATH=src python scripts/validate_control_metadata.py
python scripts/validate_capabilities.py
python scripts/check_docs.py
python scripts/check_installed_package.py
```

From `frontend/console`:

```bash
npm ci
npm run lint
npm run test:coverage
npm run build
npm run build:demo
npm run build:selfhost
npx playwright install chromium
npm run test:e2e
```

Linux browser hosts may also need Playwright system dependencies. The
[CI workflow](.github/workflows/reusable-python-quality.yml) is the reference for
the selected mypy scope. See [quality baseline](docs/quality-baseline.md) for
coverage definitions and [packaging checks](docs/packaging-and-container.md) for
container verification. Do not weaken a test, disable a rule or lower a coverage
floor merely to make a change pass; document and review any justified adjustment.

## Review And Licensing

Submit a branch/PR with a clear description and test evidence. Address review
comments and record known gaps. Maintainers must inspect required CI results;
the existence of a workflow is not proof that merging is protected.

Project-owned code uses the [MIT license](LICENSE). Contribute only material you
are authorized to provide under the applicable project terms, and preserve
third-party license/attribution notices. Dependency updates must include updated
lockfiles and review of changed license metadata. Do not copy customer reports,
third-party papers or vendor assets into distributable packages without reviewing
their separate rights. See [license inventory](docs/dependency-licenses.md).
