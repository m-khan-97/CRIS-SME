# Release Preparation

Releases are not yet a production-readiness claim. The workflow creates a draft;
a maintainer must review evidence and explicitly publish it. No real release notes
are supplied here because no release has been approved by this change.

## Prepare The Source

1. Select a stable version `vMAJOR.MINOR.PATCH` with no leading zeros. Prerelease
   tag formats are not supported by this gate yet.
2. Set the Python project version in `pyproject.toml` to the same version without
   `v`. Review dependency lock fingerprints and update them through the existing
   lock-generation process if their inputs change.
3. Author and commit `docs/releases/vMAJOR.MINOR.PATCH.md`. Use the exact tag as
   its H1 and include each of these H2 sections with meaningful content:
   `Changes`, `Upgrade Notes`, `Security`, `Known Limitations`, `Verification`.
   State breaking changes, migrations, vulnerability fixes/identifiers where
   applicable, measured checks and outstanding risks. Do not paste only a git log
   or imply that no vulnerabilities exist because no audit was performed.
4. Run the documented quality, browser, packaging, container and license-review
   checks. Retain results for the exact release commit. Review third-party notices
   and ensure release artifacts contain only approved synthetic/demo evidence.
5. Commit reviewed source and notes, then have an authorized maintainer create
   the tag at that exact commit. This instruction does not create or authorize a
   release automatically.

## Preflight And Workflow

```bash
python scripts/check_release.py --tag v0.1.0
```

Replace the example with the actual prepared tag. The gate requires an existing
tag resolving to HEAD, a clean working tree, matching Python project version,
and tracked repository-local release notes with the required sections. Markdown
structure is parsed, but meaningful content and independent approval still need
human review. A syntactically valid note is not an approval record.

Tag pushes invoke the release workflow. For manual dispatch, select the workflow
ref at the tagged commit and supply that existing tag; a tag pointing elsewhere
is rejected rather than building main and attaching it to another version.
Inputs are passed as environment data, not interpolated into shell programs.

The workflow runs preflight before the reusable full validation suite (Python
3.11/3.12, console lint/coverage/builds/browser tests and container smoke), rechecks
identity in the build job, installs Node 22 console dependencies, builds mock artifacts and
creates a **draft** release using the authored notes. Inspect all artifacts and
the exact source identity before publishing. Do not reuse or move published tags.

The same validation workflow supports manual dispatch without a release or cloud
scan. Once the workflow changes are published, select the exact ref in GitHub
Actions or run `gh workflow run pr-validation.yml --ref <reviewed-ref>`. Record
the resulting commit and all job outcomes; a dispatch request is not a passing run.

## Download Integrity

Each draft includes three archives, authored release notes, build metadata,
Python/npm license inventories and `SHA256SUMS`. The checksum generator rejects
missing, unexpected, empty or symlinked assets instead of including arbitrary
files from the output directory. It runs only after the expected assets exist.

Download all eight files into an otherwise empty directory and run:

```bash
sha256sum --check SHA256SUMS
```

Checksums cover the seven payload files, not the checksum file itself. They detect
changes relative to the downloaded list; an attacker able to replace both files
and list can replace the hashes too. This is **not signed provenance or source
authenticity verification**. Archive content review, trusted delivery and future
signing remain necessary. License inventories contain declarations, not approvals.

## Remaining Gates

This preflight is not a signature, provenance attestation or branch-protection
mechanism. Protected tags/environments, independent release review, a backup
maintainer and signed artifact verification remain open. The full release quality
gate is now configured but has not been exercised in hosted CI for this revision.
Existing unauthenticated deployment restrictions still
apply. See [quality evidence](../quality-baseline.md),
[license inventory](../dependency-licenses.md) and [roadmap](../roadmap.md).
