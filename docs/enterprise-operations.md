# Enterprise Operational Safeguards

This increment adds database-coordinated tenant storage admission and selected
action limits, worker filesystem guards, redacted operational snapshots and an
authenticated Operations view. These are private-pilot safeguards, not production
capacity certification, OS quotas, a DDoS firewall or a monitoring/alert service.

## Upgrade And Limits

Back up PostgreSQL/artifacts, stop API/workers, apply `python -m cris_sme.enterprise
migrate`, then restart matching versions. Schema v4 adds limits, bounded action
counters and ephemeral worker-health records. Existing records are not removed.
Fresh installs and v1/v2/v3 upgrades are supported. Update runtime grants for
the new tables before deployment; migration ownership is separate from runtime
access. No configuration is delivered through browser/Vite variables.

Default admission limits per tenant:

| Control | Default |
| --- | --- |
| Registered report bytes | 1 GiB, including expired/quarantined artifact metadata |
| Registered artifacts | 10,000 |
| Nonterminal jobs | Existing two-job limit |
| Reservation per nonterminal job | 128 MiB and five published files |
| Per-attempt staging | 256 MiB and 2,048 file/directory entries |
| Tenant local namespace | Report quota plus 256 MiB; artifact allowance plus 2,048 entries |
| Minimum free local disk | 256 MiB; starting a scan also requires staging headroom |

Admission atomically checks registered bytes/files plus existing reservations
under a tenant row lock. Quota is rechecked before upload and at final lease-fenced
publication. Imports must not consume scan reservations. A terminal job releases
its reservation, but committed evidence remains charged after logical expiry:
quarantine is not physical erasure. Idempotent retries reuse their existing job
without spending another reservation or rate allowance, even under disk pressure.
Reading history/downloading existing reports is not blocked merely by quota.

Only a privileged **operator CLI** can change storage policy. A browser owner
cannot raise their own quota. The CLI also checks an asserted tenant owner for
audit attribution; database/key holders remain trusted administrators.

```bash
python -m cris_sme.enterprise operations-limits \
  --tenant <uuid> --subject <verified-owner-subject> \
  --quota-bytes 1073741824 --max-artifacts 10000 --apply
```

Changes require draining nonterminal jobs first. Limits may be lowered below
existing committed usage without deleting evidence; new admissions stay blocked
until capacity/policy is resolved. Byte limits accept 128 MiB through 1 TiB and
file limits five through one million; raising them requires deployment testing.

Quotas measure registered publication and reservations, not S3 billing. Remote
orphan uploads and noncurrent versions are outside that accounting and require
separate reconciliation, lifecycle qualification and cost/capacity monitoring.

## Shared Action Budgets

Fixed windows use the PostgreSQL clock and one bounded counter per tenant/action,
shared across API processes rather than per-process memory or caller-supplied IPs:

| Action | Allowance |
| --- | --- |
| New scan admission | 24/hour |
| Cloud connection verification | Six/minute |
| Cloud connection creation | 20/hour |
| Retention proposal attempts | 12/hour |

Failed provider verification attempts are charged **before** provider calls in a
separate committed admission transaction, so failures cannot bypass the limit.
Unauthorized/foreign requests do not spend another organization's allowance.
Admission/database failure never falls back to unguarded verification. Repeated
proposal attempts count even if no report is eligible. Scan retries are charged
only once. Hold, cancellation, disconnect, withdrawal and ordinary report reads
remain available when these budgets are exhausted.

Denials return 429 with `Retry-After` where a retry hint is available. The hint is
not a guarantee that storage capacity will become available. Fixed-window boundary
bursts are possible; this is not a rolling-window or network-layer defense.
Reverse-proxy authentication/DDoS controls and declared deployment concurrency
remain required. API process concurrency is separately bounded by its server.

## Worker And Disk Guards

Workers check disk headroom and reserved publication capacity before starting a
collector. While it runs, filesystem budgets/free space are polled at up to
one-second intervals, independently of lease-renewal timing. Oversize output,
retained orphan pressure or low disk signals the managed process cancellation
path and prevents completed publication. Guard outcomes use fixed sanitized
codes: `storage_quota`, `staging_limit`, `disk_pressure`, or existing worker errors.
Cancellation/revocation fencing remains authoritative; partial local files or
remote uploads may still require reconciliation.

Namespace accounting includes staging and quarantine, deduplicating hard-linked
inodes. Symlinked namespace roots are rejected. It is sampled and assumes trusted
local writers: bursts can outrun polling, unregistered data is not globally billed,
and other applications can consume the same filesystem. Use filesystem/project
quotas, container memory/CPU/process/disk limits and independent capacity alerts
for hard isolation. These guards do not sandbox arbitrary customer commands.

## Monitoring

Owners/admins/auditors can use `GET /api/v1/tenants/{tenant}/operations` and the
console **Operations** view. It reports only their registered/reserved capacity,
status counts, oldest queue age, expired leases and selected action budgets.
Role downgrade hides cached operational data. Analysts/operators do not receive
administrative capacity data. No tenant names/IDs, cloud scopes, credentials,
object keys or raw errors are used as metric labels.

Privileged operators can inspect the cluster without exposing a public metrics
endpoint:

```bash
python -m cris_sme.enterprise operations-status
```

This returns aggregate fresh/busy/stale worker counts, queue/running/failed totals
and free-disk pressure. Worker IDs are ephemeral and omitted from output. A worker
is stale after 30 seconds without its database heartbeat; old records are pruned
after seven days. Clean shutdown removes its record best-effort. Availability is
not proof that cloud permissions or the entire pipeline are healthy.

`/health` remains liveness. `/ready` reports only a generic ready/not-ready result
for database/storage checks and minimum disk space, not global counters. Alert
externally on no fresh workers, increasing queue age, stale leases, failures and
disk/quota pressure. No automated paging, SLO, full tracing or Prometheus service
is claimed. Failures/counts are snapshots, not measured incident rates.

## Recovery And Qualification

Tenant limit policy is included in logical backups. Worker-health records and
rate counters are excluded and start fresh on restore; nonterminal jobs remain
disallowed in logical backups. V2/v3 bundles receive default limits on upgrade.
Restore still requires an empty isolated target and disabled cloud connections.

Tests include concurrent shared admission, provider denial, idempotent retries,
reservation release, import contention, injected admission failure, disk/output
pressure, upgrade/restore and a **fixture** workload of ten tenants/twenty scans.
Collectors/provider calls in that load test are synthetic. This is a bounded
functional stress test, not production throughput, soak testing or live AWS/Azure
qualification. Those gates and independent operational/security review remain open.
