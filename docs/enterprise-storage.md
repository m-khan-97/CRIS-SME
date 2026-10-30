# Enterprise Report Storage

The enterprise API, worker, historical importer and logical recovery tool share
an artifact transport. Local POSIX storage remains the default. An optional AWS
S3 general-purpose-bucket backend is implemented and fixture-tested; no live
customer S3 qualification is claimed. No bucket or cloud infrastructure is
created automatically. Scan-account access and storage-account access are
separate authorization concerns.

## Configure S3

Configure the **same backend, bucket, region and deployment prefix** on the API,
workers and operator commands. Keep these private server settings out of Vite:

```dotenv
CRIS_ENTERPRISE_STORAGE_BACKEND=s3
CRIS_ENTERPRISE_S3_BUCKET=<private-general-purpose-bucket>
CRIS_ENTERPRISE_S3_REGION=eu-west-2
CRIS_ENTERPRISE_S3_PREFIX=cris-private-pilot/artifacts
```

Use a dedicated workload identity with scoped storage permissions. This transport
uses the maintained boto3 credential chain, not a connection's customer scan
credentials. No keys are accepted from the browser. AWS credentials/configuration
are resolved lazily when storage is actually accessed; metadata-only usage and
retention previews do not require a storage login. Public AWS commercial regions
are supported; arbitrary endpoints, MinIO compatibility, sovereign partitions
and KMS-specific encryption configuration are not qualified here. SDK endpoint
overrides are ignored, HTTPS remains enabled, and request retries/timeouts are
bounded. Do not provide a browser-accessible bucket or static output mount.

Before use, enable all four S3 public-access-block settings and bucket versioning.
CRIS checks these on readiness, before each publication, and before API download
delivery. Those checks are not an IAM-policy audit, Object Lock or protection
against an administrator changing configuration after a check. The runtime
needs `s3:GetBucketPublicAccessBlock`, `s3:GetBucketVersioning`, scoped
`s3:GetObject` and `s3:PutObject`. The
[example identity policy](../infra/aws/artifact-storage-policy.example.json)
contains placeholders; review it before applying anything. Bucket creation,
versioning, lifecycle, ownership, private-network policy and grants remain the
operator's responsibility. Restore operators additionally need prefix-scoped
`s3:ListBucketVersions` to verify an unused destination, including noncurrent
versions and delete markers.

```bash
python -m cris_sme.enterprise storage-check
```

Keys retain deployment/tenant/job/attempt namespaces. Objects use SSE-S3 AES256,
SHA-256 checksums and conditional `If-None-Match: *` publication, followed by
verified readback. Repeating a copy accepts only identical content; a different
existing object is never replaced. This follows the
[AWS conditional-write contract](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html).
Conditional writes apply to the current key: versioning/delete markers are not
immutability or legal holds. The supplied identity policy denies object deletion;
independently review other principals, bucket policy and lifecycle configuration.

The API first authorizes the tenant/artifact ID in PostgreSQL, then reads a
bounded body, validates its size/hash and sends an attachment. It never supplies
public or presigned URLs. A failed remote read does not fall back to a potentially
stale local file. Cloud errors remain sanitized. The 32 MiB per-file bound still
applies; uploads are single PUTs, not unbounded multipart transfers.

Workers still need private local staging and process isolation. Uploads precede
lease-fenced metadata publication. Failed/cancelled/stale attempts can leave
unreferenced local files and remote objects. Database commits and object PUTs
are not one atomic transaction. Reconcile before cleanup; do not attach an
independent bucket-expiration rule to registered objects and assume the API will
update its history automatically.

## Move Existing Reports

Stop admission and drain workers. Preserve a verified backup before changing
the live deployment configuration. Set the S3 destination settings only in a
separate private operator environment and keep `CRIS_ENTERPRISE_ARTIFACT_ROOT`
pointing to the original local source:

```bash
python -m cris_sme.enterprise storage-copy
python -m cris_sme.enterprise storage-copy --apply
```

The default is a local integrity preview; it does not access the S3 client.
The apply step validates all registered source files before copying, then checks
each copied object. It never deletes source files or changes PostgreSQL metadata.
Conflicting metadata writers/nonterminal jobs fail closed. Batches are bounded
to 10,000 files/512 MiB and exceeding a bound is an error, not truncation.
Partial successful remote copies can remain after a failure; retrying identical
content is idempotent. Once every registered artifact is verified, deliberately
configure matching API/worker settings and check readiness and authenticated
downloads. Do not switch an existing deployment to an empty destination first.
Automatic online migration and per-record mixed-backend routing are not supplied.

## Recovery And Retention

[Logical backups](enterprise-recovery.md) now read committed artifacts from the
configured transport. Offline backup checking does not need S3 credentials.
Restore requires the existing empty database/new local directory safeguards and,
for S3, an unused dedicated prefix. Restrict other writers to that prefix during
restore; a listing check alone is not a distributed exclusive lock. Restored
connections remain disabled. The bundle itself remains sensitive and unsigned;
S3 versioning does not replace encrypted off-host backup or PITR.

Owners/admins can obtain recorded usage through
`GET /api/v1/tenants/{tenant}/storage` or the CLI:

```bash
python -m cris_sme.enterprise storage-usage --tenant <uuid> --subject <oidc-subject>
python -m cris_sme.enterprise retention-plan --tenant <uuid> --subject <oidc-subject> \
  --retention-days 90 --exclude-job <assessment-uuid>
```

Usage counts committed artifact metadata only, not actual bucket billing,
noncurrent versions, local staging, orphaned uploads or backups. Retention is
**preview-only**: `--apply` is rejected. It reports eligible completed assessments,
registered file counts/bytes and a digest of the plan without changing data.
The newest completed assessment per provider/cloud scope is always preserved.
Explicit exclusions are respected. Imported history is protected unless
`--include-historical` is supplied, and its age starts at import time, not the
original report date. Native age uses recorded request time because a separate
completion timestamp is not yet persisted. Changed data/time can change a plan.

These exclusions are not durable legal holds. Every plan explicitly reports
`legal_hold_checked: false` and `deletion_executed: false`. It is not permission
to delete files or a persisted retention policy. Automated deletion, first-class
legal holds/approvals, quota admission, version-aware garbage collection and
storage lifecycle reconciliation remain future work. No existing reports are
deleted or moved merely by enabling inventory/planning.
