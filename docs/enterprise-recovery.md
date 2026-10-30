# Enterprise Backup And Recovery

The operator CLI supplies a bounded **offline logical recovery bundle** for the
current PostgreSQL metadata schema and committed report artifacts. It is intended
for controlled private pilots and restore drills. It is not PostgreSQL physical
backup/PITR, an online backup service, managed object storage or a production
disaster-recovery qualification.

The optional [S3 artifact transport](enterprise-storage.md) can supply backup
reads and restore publication. Remote restores additionally require an unused
deployment prefix and prefix-scoped listing permission; no source bucket is
created, reconfigured or deleted by recovery commands.

## Boundaries

- Stop API admission and drain/stop workers before operating. All jobs must be
  completed, failed or cancelled. The command acquires PostgreSQL table locks
  that exclude metadata writes; it fails immediately on conflicting writers.
  These locks can block API writes while copying files. The tool does not control
  other local processes or lock the filesystem against trusted local writers.
- Backup includes tenants, memberships, encrypted connection secrets, jobs,
  committed artifact metadata, audit events and historical-import records. It
  copies only referenced artifacts, not worker scratch directories or orphans.
- The encryption key, database credentials, Keycloak state, TLS material, gateway
  settings and deployment configuration are **not** included. Back up required
  configuration and identity-provider state separately under an appropriate
  secret-management policy. The original connection encryption key is required
  to validate/restore a bundle containing connections.
- Bounds are 100,000 metadata rows, 16 MiB metadata, 10,000 artifacts, 32 MiB per
  artifact and 512 MiB total artifact bytes. Exceeding a bound fails; it does not
  silently omit records. Larger deployments need a qualified backup/storage
  design rather than raising these values without resource testing.

## Create And Check

Use the same private enterprise environment as the source API. The destination
must not exist and must be outside the artifact root:

```bash
python -m cris_sme.enterprise backup --backup-dir /private/backups/new-snapshot
python -m cris_sme.enterprise check-backup --backup-dir /private/backups/new-snapshot
```

The directory is owner-only and files are mode 600. Artifacts are copied
byte-for-byte and checked against their registered size/SHA-256. Metadata is
bounded JSON, with an integrity digest and completion marker written last. An
interrupted backup without `complete.json` is not restorable. Existing backups
are never overwritten. Partial backups require explicit operator reconciliation.

Bundles contain sensitive customer reports and identity/membership metadata.
Connection secrets remain encrypted, but **the bundle as a whole is not
encrypted or signed**. Digests detect accidental damage, not malicious replacement
of both files and metadata. Keep bundles on protected storage; use your approved
authenticated encryption/backup system for transport/off-host retention. Never
commit, upload as CI artifacts or serve these directories publicly. Protect the
encryption key separately. The logical bundle does not independently establish
the authenticity or correctness of original assessment evidence.

## Isolated Restore

Provision a separate empty PostgreSQL database and an unused artifact directory.
Keep API, workers, cloud egress and public ingress off for the target. Configure a
private environment pointing to that target and the original connection
encryption key, then run:

```bash
python -m cris_sme.enterprise migrate
python -m cris_sme.enterprise restore \
  --backup-dir /private/backups/new-snapshot --apply
```

Restore is refused if the target contains any enterprise metadata or if its
artifact directory exists, even when empty. Existing customer workspaces are
never replaced. Unsupported versions, missing/damaged files, symlinks, traversal,
cross-namespace artifact paths and wrong connection keys are rejected.

Original record IDs, tenant membership, history, report bytes and audit records
are retained. Holds, hold events and report-expiry markers are preserved. Expired
bytes are retained privately in quarantine rather than republished; pending
retention approvals are invalidated. Remote restore of local-quarantine history
is refused. See [controlled retention](enterprise-retention.md).
**All restored cloud connections are disabled and their verification
deadlines cleared**, so restored workers cannot start new collection. This does
not revoke or delete credentials at AWS/Azure. Reconnection requires deliberate
new connection creation and verification; do not automatically re-enable restored
credentials. No queued/running jobs are restored or replayed.

Metadata publishes in one transaction after verified artifact copies. A failure
rolls back database publication, but may leave unreferenced private files; an
uncertain commit must be reconciled before any cleanup. Do not retry against an
existing target directory or automatically delete possibly committed data. Preserve
the failed target for investigation and use a new isolated target for another drill.

Compare tenant/membership, job/history and audit records against the snapshot;
verify every artifact digest and test owner/nonmember report access. Confirm no
worker can claim work and that source records/files remain unchanged. Only after
a separately approved recovery review should a recovered service receive network
access or become a replacement deployment.

## Remaining Gates

Retention schedules, automatic encrypted off-host backups, backup expiry,
WAL/PITR, key/IdP disaster recovery, object-store snapshots, measured RPO/RTO and
independent recovery review remain deployment responsibilities. This tool closes
a local logical restore increment, not the shared-hosting P1 release gate or
live-cloud qualification.
