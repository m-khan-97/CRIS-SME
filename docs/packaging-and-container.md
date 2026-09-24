# Packaging And Private Container Runtime

## Installed Packages

Python 3.11 or newer is required: the application already uses `datetime.UTC`.
The previous Python 3.10 metadata did not match that runtime requirement.

The canonical read-only JSON assets remain in repository `data/`. Setuptools includes them
in wheels as `cris_sme/_data/`; source distributions include the same assets.
`policy_data_path()` selects installed assets or the source checkout without
depending on the current directory. Explicit loader paths remain supported.
An unrelated working-directory `data/` cannot silently replace built-in policy.

Mutable exception and mute registries retain their separate relative paths:
`data/finding_exceptions.json` and `data/mute_rules.json`. Missing registries mean
no exceptions/mutes. These mutable files are excluded from distribution archives
and the Docker build context. The application does not write changes into installed policy
assets. In the container these mutable paths are beneath `/data/data/`.

Verify the source distribution, wheel and installed mock assessment:

```bash
python -m pip install --require-hashes -r requirements/dev.txt
python scripts/check_installed_package.py
```

This test copies only packaging inputs to a temporary directory, builds an sdist
and a wheel from it, checks JSON asset bytes, installs into a fresh virtual
environment, deletes the copied source and runs a mock assessment from an empty
working directory. Dependencies/build tools are downloaded as needed. Reports are
checked and temporary outputs removed; customer reports are not overwritten.

Provider conformance currently inspects repository-local test/document files.
Those files are not shipped as executable package assets, so installed reports
can show unavailable source-conformance evidence. This test establishes usable
packaging, not provider validation or identical source-conformance results.

## Private Container

Read the [deployment restrictions](deployment-security.md) first. The container
does not add authentication or tenant isolation to the runner.

```bash
docker compose up --build -d
docker compose logs -f
docker compose stop
```

Open `http://127.0.0.1:8080`. Compose binds localhost deliberately: the local API
still lacks a hosted tenant/authentication boundary. Do not expose the port
publicly or treat this image as enterprise SaaS.

The image runs as UID/GID `10001`, with writable report/database storage in the
`/data` volume and nginx temporary files in `/tmp`. New Docker volumes inherit
the prepared data-directory ownership. Existing volumes or bind mounts must be
writable by UID 10001; the container does not silently chown customer storage.

Tini reaps orphaned descendants. A Python supervisor starts nginx and the API in
separate process groups, forwards termination to both, allows ten seconds for
shutdown and then kills remaining descendants. Unexpected exit of either service
stops the other and produces a nonzero container exit, even if the service itself
returned zero. Compose allows twenty seconds before forced shutdown.

The health check requests `/health` through nginx; it verifies proxy/API liveness,
not cloud credentials or scan completion. Cloud SDKs are included, but cloud login
and authorization are not performed by building the image. Azure CLI-dependent
onboarding is not provided by this image; live credential workflows remain a
separate validation task. Never copy credentials into an image.

## Container Acceptance Test

```bash
docker build -t cris-sme:local .
python scripts/check_container.py --image cris-sme:local
```

The test uses a uniquely named disposable volume/container, no host port and no
cloud credentials. It checks UID, read-only root filesystem operation, mock report
generation/retrieval through nginx, console delivery, graceful stop, persisted
reports after restart and service-failure propagation. Its own container and
volume are removed on exit. The PR container job runs this same test.

### Operator Verification: 24 September 2026

After installing Docker, the operator supplied this successful acceptance-test
output:

```text
Container nonroot, report retrieval, persistence, stop and failure checks passed.
cris-smoke-73e2f9b52fc8
cris-smoke-73e2f9b52fc8-data
```

The final two lines are the disposable container and volume names printed by
cleanup commands. This is operator-reported verification, not an independently
rerun assistant test: the assistant session still lacks Docker socket access and
non-interactive sudo authorization. No image digest or full build log was supplied,
so this record is not an attestation tied to a specific image digest.

Hosted CI confirmation remains pending. Required status checks must be configured
in GitHub branch protection by a repository administrator. Cloud-specific container
authentication tests remain follow-up work.

## Dependency Locks And Base Images

`requirements/` contains hash-locked profiles generated from `pyproject.toml` and
`requirements/build.in`:

| Profile | Consumer |
| --- | --- |
| `runtime.txt` | Minimal installed application smoke test |
| `cloud.txt` | Container runtime, including AWS and Azure SDKs |
| `mcp.txt` | Optional MCP integration environment |
| `build.txt` | Build frontend/backend and their dependencies |
| `dev.txt` | Tests, cloud SDK fixtures, lint/types, documentation and build tooling in CI |

The root `requirements.txt` remains a compatibility entry point to the dev lock.
Use `pip install --require-hashes -r requirements/<profile>.txt`; transitive
packages are pinned too. CI no longer upgrades pip or resolves unpinned QA tools.
Container installation preinstalls locked build/cloud dependencies and installs
the local project with `--no-deps --no-build-isolation`. The wheel test likewise
builds without an implicit download of newer build backends.

Regeneration requires uv (the exact generating version is recorded in the lock
manifest). Existing pins are preserved unless an upgrade is requested:

```bash
python scripts/lock_dependencies.py
python scripts/lock_dependencies.py --check
python scripts/lock_dependencies.py --upgrade
```

Review lock diffs, run tests and installed-package/container checks before merging
an upgrade. The manifest detects changed inputs or manually altered lock outputs;
it is a consistency check, not a signature or vulnerability audit. Universal
resolution records platform markers, but does not prove every OS/Python version
has been tested. See [uv's locking documentation](https://docs.astral.sh/uv/pip/compile/).

Both `FROM` lines use verified Docker Hub manifest-list SHA-256 digests. Node 22
replaces Node 20 in the frontend builder; Python remains 3.12 on explicit Debian
Bookworm. For updates, inspect the intended official image using
`docker buildx imagetools inspect`, review the new digest, update the Dockerfile,
and rerun the container test. Never remove the digest just to pick up updates.

Digest and Python locks do not make the whole image bit-for-bit reproducible:
Debian package repositories used for nginx/tini are still live, and build outputs
can contain timestamps. OS snapshot pinning, release attestations and image
vulnerability scans are separate roadmap work. The existing frontend lock remains
enforced with `npm ci`.

Verified locally with the locked Python 3.12 environment: 362 tests, critical-rule
lint, the two workflow-entrypoint type checks, `pip check`, and the sdist/wheel
mock assessment. The cloud lock also passed pip's hash-checked resolution. The
separate operator-reported Docker acceptance result is recorded above.
