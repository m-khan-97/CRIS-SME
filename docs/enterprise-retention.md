# Controlled Local Retention

Durable assessment holds, reviewed proposals, separate-owner approval, logical
report expiry and recoverable local quarantine are implemented. **This does not
permanently erase evidence, clean S3 versions, expire backups or certify legal
compliance.** No scheduler or automatic deletion is enabled.

## Upgrade And Defaults

Back up PostgreSQL and private artifacts. Stop API/workers, run
`python -m cris_sme.enterprise migrate`, then restart matching versions. Schema
v3 adds retention tables without changing existing jobs, memberships or artifact
rows. Fresh installs and v1/v2 upgrades are supported. Existing v2 logical backups
remain readable; downgrade tooling is not supplied.

`CRIS_ENTERPRISE_RETENTION_ENABLED` defaults to disabled. Only the exact value
`true` enables proposals, approval and operator expiry/quarantine commands. The
local Keycloak pilot forces `false`, even if inherited from the shell. Holds,
hold release, proposal withdrawal and read-only inventory remain available so
stopping execution never prevents preserving evidence. Do not enable execution
on customer workspaces merely as part of an upgrade.

## Workflow

1. An owner/admin places an assessment hold with a reason. Only an owner can
   release it, also with a reason. Each change is retained in an append-oriented
   hold-event table and the audit log; earlier reasons are not discarded.
2. Preview checks registered holds and expired assessments, preserves the latest
   completed assessment per provider/cloud scope and protects imports by default.
   Import age starts at admission; native age currently uses request time.
3. An owner/admin freezes a reason, policy preview and exact artifact IDs, paths,
   hashes and sizes. Proposals are bounded to 1,000 artifacts/2 MiB, have a SHA-256
   digest and expire after seven days. Empty proposals are rejected.
4. A different owner identity confirms the exact digest. Self-approval, a changed
   digest/snapshot or expired/withdrawn proposal is rejected. Approval starts a
   **24-hour cooling period**. Owners can withdraw before expiry execution.
5. A separate operator command rechecks proposer/admin and approver/owner
   membership, holds, current eligibility, terminal state and artifact inventory.
   Expiry, pending cleanup and the audit event commit transactionally. There is
   no public HTTP endpoint executing expiry or filesystem cleanup.
6. Another operator command quarantines up to 20 files per call (library maximum
   100). It checks holds again. Held jobs cannot starve eligible later batches.
   Verified files receive a no-overwrite hard link in private quarantine; file
   and directory durability precede unlinking the published filename. This
   requires one local filesystem; cross-device links fail closed.

Distinct identities are application authorization, not proof of independent
humans. API calls require signed OIDC tokens. CLI subjects are trusted operator
assertions: administrators with database/key access can bypass application policy
and need governance outside the application.

## API And Commands

Routes below are relative to `/api/v1/tenants/{tenant}`:

| Route | Access |
| --- | --- |
| `GET /retention` | Owner/admin; latest 100 plan summaries, up to 1,000 current holds |
| `GET /retention/plans/{plan}` | Owner/admin; one bounded full proposal |
| `PUT /assessments/{assessment}/hold` | Owner/admin set; owner release; `{active, reason}` |
| `POST /retention/plans` | Enabled owner/admin; `{days, reason, exclude, include_historical}` |
| `POST /retention/plans/{plan}/approve` | Enabled different owner; `{sha256, confirmed: true}` |
| `POST /retention/plans/{plan}/withdraw` | Owner; `{sha256, confirmed: true}` |

Listings omit snapshots; fetch one proposal before reviewing its digest.
Presentation limits do not remove older records. Paths in proposals are never
download authority. Operator mutations require explicit tenant, subject and
`--apply`. These placeholders do not authorize changes to customer reports:

```bash
python -m cris_sme.enterprise retention-hold --tenant <uuid> --subject <subject> \
  --assessment <job-uuid> --reason "Preserve evidence for review" --apply

python -m cris_sme.enterprise retention-propose --tenant <uuid> --subject <proposer> \
  --retention-days 90 --reason "Reviewed retention scope" --apply

python -m cris_sme.enterprise retention-approve --tenant <uuid> --subject <different-owner> \
  --plan <plan-uuid> --plan-sha256 <reviewed-digest> --apply

python -m cris_sme.enterprise retention-expire --tenant <uuid> --subject <owner> \
  --plan <plan-uuid> --plan-sha256 <reviewed-digest> --apply

python -m cris_sme.enterprise retention-cleanup --tenant <uuid> --subject <owner> \
  --plan <plan-uuid> --apply
```

Use `retention-withdraw` with the plan/digest to stop an unexecuted proposal;
`retention-hold --release` requires a release reason. Never change cooling times
manually in an operational database; tests advance fixture time only.

## Access And Recovery

Expiry preserves assessment IDs, dates, provenance and completion status; report
availability is separate. Authorized artifact requests receive **410 Gone**;
foreign/nonmember requests remain 404. Metadata stays, but expired downloads do
not appear in job responses. The console keeps history selectable, marks expiry
and removes cached report views/exports on refresh. Already read/downloaded bytes
and requests authorized before expiry cannot be recalled.

Quarantine is `<artifact-root>/retention_quarantine/<tenant>/<plan>/<artifact-id>`.
Only registered exports in the snapshot are processed, not scratch directories,
unregistered exports or backups. Errors are sanitized, audited and retryable.
After a filesystem change but failed database commit, retry verifies quarantine
bytes before reporting success. Symlinks, conflicts, corrupt/missing files and
filesystem errors retain an error state, never false cleanup success. Local
writers/OS administrators remain trusted. There is no Object Lock or disk-space
reclamation guarantee.

A late hold stops remaining actions and preserves quarantined bytes; it does not
republish an expired report. Silent reimport of an expired historical run is
rejected. Unexpiry, republishing and permanent purge need a future reviewed workflow.

Logical backups preserve **available and quarantined bytes**, including held
expired evidence. Restore preserves holds/events/expiry, returns expired bytes
only to quarantine and invalidates pending approvals. Cloud connections remain
disabled. S3 restore/migration of local-quarantine history is refused until its
lifecycle is qualified. Never discard source storage after a failed migration.

S3 version cleanup, permanent erasure, backup expiry, legal-case integration,
scheduling, quota admission and independent security/recovery review remain open.
This closes a local retention increment, not the overall P1 hosting gate.
