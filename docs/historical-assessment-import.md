# Historical Assessment Import

This operator-only path copies selected legacy Azure/AWS assessments into an
explicit enterprise tenant. It does not scan cloud resources, discover ownership
from names, validate historical findings or change evidence classifications.
It is not an HTTP upload endpoint or managed blob-storage implementation.

## Prepare

Back up PostgreSQL and private artifact storage. Configure the same private
enterprise environment used by the API, including the database URL, encryption
key, issuer and artifact root. Stop services for the schema upgrade, run
`python -m cris_sme.enterprise migrate`, then restart matching API/worker versions.
Schema v2 accepts fresh installations or an additive v1 upgrade; unsupported
versions fail closed. No downgrade command is supplied.

Choose the tenant UUID deliberately and verify the operator's issuer/subject
membership is owner/admin. A matching display name is not authorization. Bootstrap
a tenant separately if required; importing does not create memberships.

```bash
python -m cris_sme.enterprise historical-import \
  --tenant <tenant-uuid> --subject <verified-oidc-subject> \
  --source-root /private/archive \
  --report organization/reports/cris_sme_report.json --include-exports
```

Default execution is a dry run. Inspect source organization/run IDs, original
generation time, reported source type, hashes, selected files and skipped exports.
Repeat the command with `--apply` only after checking the ownership mapping.
Up to 20 explicit `--report` paths are accepted per invocation. Preparation of all
inputs precedes publication, but each assessment commits separately: a later
publication failure does not roll back earlier successful assessments.

## Preservation And Boundaries

- Original JSON bytes, embedded organization/run IDs, timestamps, findings and
  source classifications are preserved. A new internal job UUID provides the
  enterprise namespace; it does not replace the original run ID in the report.
- Imports are completed archival jobs, never queued work. Their disabled archival
  connections contain no cloud credentials and cannot be verified or used to scan.
- `--include-exports` accepts only recognized report filenames referenced beside
  the canonical source JSON. Timestamped history snapshots remain JSON-only;
  they never borrow exports belonging to the latest run.
- Source reads reject traversal and symlinks. Main JSON is limited to 16 MiB,
  individual exports to 32 MiB and a bundle to 64 files/128 MiB. Duplicate JSON
  keys, non-finite values, inconsistent providers and unsupported shapes fail.
- Original source SHA-256 and an export-bundle digest are recorded. A generated
  import manifest records the explicit mapping and the fact that no collector ran.
  This establishes copy integrity, not independent authenticity or valid consent.
- Same-tenant source run/hash duplicates return the existing job after checking
  imported file integrity. Changed source bytes or export inventory conflict;
  existing imports are never silently overwritten. Duplicates across tenants are
  not ownership evidence and must be reviewed independently by the operator.
- Files are private and namespaced by tenant/job. Metadata, artifact entries and
  the audit event publish in one PostgreSQL transaction. Interrupted copies may
  leave unreferenced private files; no unsafe automatic deletion follows an
  uncertain commit. Reconcile those files against committed artifact keys before
  any manual cleanup, and include both storage and metadata in backups.

## Browser Verification

Refresh organizations, select the intended tenant and choose an `[Imported]`
assessment. All report views use that selection and show the original generation
time, source run/hash, import time and **Not rescanned** marker. Reported source
classifications remain explicitly un-revalidated. Downloads retain bearer-auth,
tenant checks, bounded delivery and SHA-256 validation; HTML is an attachment,
not executable console content. Historical archives expose no live connection
actions. Only assigned members can discover or download these reports.

Automated coverage includes parser negatives, v1 upgrades, transaction rollback,
idempotence/concurrency, role and tenant denial, byte preservation, archive controls
and browser selection/downloads. Local Keycloak integration is a separate gate;
neither those tests nor import success qualify a live cloud deployment.
