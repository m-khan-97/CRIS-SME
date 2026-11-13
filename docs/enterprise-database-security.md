# Enterprise Database Isolation

This opt-in P1 deployment increment separates migration/operator, API and worker
database credentials. It adds PostgreSQL row-level security (RLS) as defense in
depth for missing tenant filters. It is not an independent security assessment
or authorization to expose a shared-hosted deployment.

## Boundary

The API validates OIDC tokens and checks current organization membership/role as
before. Each database transaction sets the selected tenant, issuer and subject
with parameterized `set_config(..., true)`. The context is transaction-local;
commit, rollback and connection-pool reuse do not retain another request's scope.
There is no browser-supplied SQL, JWT decoding in PostgreSQL, `SECURITY DEFINER`
helper or connection-wide tenant setting.

With a restricted API login, ordinary tenant-table reads and writes require the
selected tenant. Unfiltered queries without context see no tenant records.
Membership/organization discovery additionally permits the current subject's own
memberships, so the organization selector can work before choosing a tenant.
Membership-list and role-changing authorization still belongs to the API.
Both `USING` and `WITH CHECK` policies prevent an accidental row update from
moving a job into another organization.

**The service supplies this context; PostgreSQL does not authenticate it.** An
attacker who can execute arbitrary SQL as the API login can forge these settings.
The policies mitigate omitted filters in trusted application code, not SQL
injection or service-credential compromise. Workers intentionally require access
across tenants to claim and publish jobs. Maintain the API checks, parameterized
queries, secret controls, network isolation and independent tenant-boundary review.

PostgreSQL owners/superusers and `BYPASSRLS` identities need special handling;
referential-integrity checks can also expose constraint side channels. See the
[PostgreSQL RLS documentation](https://www.postgresql.org/docs/16/ddl-rowsecurity.html).
Runtime profiles reject privileged identities and table/database/schema owners,
require enabled/forced RLS, and disallow runtime role memberships. The migration
owner has an explicit all-row operator policy for bootstrap/recovery under forced
RLS. Do not give runtime logins membership in that role.

## Credential Separation

Use a **dedicated database/schema**, not an unrelated shared application schema.
The existing reference Compose file and local Keycloak helper remain development
topologies with shared operator credentials; they are not silently upgraded.
The Keycloak helper explicitly selects the `development` database profile.

Provision two distinct PostgreSQL logins using an administrator's secure console:

```sql
CREATE ROLE cris_api LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE cris_worker LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
```

Set distinct SCRAM passwords interactively (`\password cris_api` and
`\password cris_worker` in psql), or provision approved database workload
authentication. Do not put passwords into SQL history, source files or chat.
Provision the separate migration owner with the required DDL privileges; runtime
roles must own neither database, schema nor tables and have no other role grants.
Use TLS (`sslmode=verify-full` with the deployment's CA), restricted network access
and secret-manager delivery outside the loopback-only test environment.

Back up metadata/artifacts and drain API/workers before applying grants. With the
migration/operator database URL, connection-encryption key and
`CRIS_ENTERPRISE_DATABASE_PROFILE=development` in a private environment:

```bash
python -m cris_sme.enterprise migrate
python -m cris_sme.enterprise database-harden --api-role cris_api --worker-role cris_worker
python -m cris_sme.enterprise database-harden --api-role cris_api --worker-role cris_worker --apply
```

The first hardening command previews/validates without changing grants or data.
Application is one transaction, uses the migration advisory lock, and can be
rerun. It refuses unexpected policies, privileged/missing/shared runtime roles
and an incomplete table manifest. It does not create users or passwords.
It revokes PUBLIC and selected-role table/column grants, removes PUBLIC/selected
roles' schema CREATE, installs the required grants and policies, and enables and
forces RLS on all 15 tenant/worker tables. The schema-version table is read-only
for both services. Existing tenant/report rows are not rewritten or deleted.
This deliberately changes PUBLIC schema access; never apply to a shared schema
without reviewing the effect on its other users.

| Credential | Allowed work | Not granted |
| --- | --- | --- |
| Migration/operator | Schema changes, tenant bootstrap, archive import, backup/restore, quota changes, approved retention execution | Never distribute to API/worker containers |
| API | Tenant-scoped membership, connection and scan workflows; report metadata reads; audit/hold/proposal creation | DDL, tenant bootstrap, report deletion/insertion, quota changes, cleanup execution, worker-health reads |
| Worker | Cross-tenant job claims/heartbeats/fenced completion, artifact insertion, audit append, worker-health maintenance | Membership/credential changes, quota changes, report deletion, schema changes |

`SELECT FOR UPDATE` needs limited UPDATE privileges: both logins receive UPDATE
on `tenants.id`, and workers also on `connections.id`. This permits row locking,
not connection-secret/status updates. Audit rows have INSERT, not UPDATE/DELETE.
These are SQL grants, not application business-role permissions.

## Enable And Verify

Use **separate private environment files** for the two services. Each includes
the existing OIDC/encryption/storage settings and its own database URL:

```text
# API service only
CRIS_ENTERPRISE_DATABASE_PROFILE=api
CRIS_ENTERPRISE_DATABASE_URL=<private URL for cris_api>

# Worker service only, in a different environment file
CRIS_ENTERPRISE_DATABASE_PROFILE=worker
CRIS_ENTERPRISE_DATABASE_URL=<private URL for cris_worker>
```

Before starting each service, with its own credentials:

```bash
python -m cris_sme.enterprise database-check --database-profile api
# Run separately with the worker credentials:
python -m cris_sme.enterprise database-check --database-profile worker
```

Start `serve` with the API file and `worker` with the worker file. API construction
and worker startup check the declared profile; the API also rechecks it during
readiness. A mismatch, privileged role, unexpected effective table/column grant,
role membership, missing/extra applicable policy or disabled/unforced RLS fails
closed. Readiness returns a generic 503, not SQL details. Operator CLI commands
refuse a declared runtime profile. `development` remains the explicit backward-
compatible default, not a production-safety switch. Do not use it to bypass a
failed runtime check. Database administrators can change policy expressions;
the checker is a configuration guard, not attestation of a trusted administrator.

Schema upgrades and logical recovery remain separate operator actions. Logical
bundles do not contain roles, grants, policies or passwords. After restoring into
an isolated empty target, migrate and reapply hardening, then run both profile
checks before enabling services. The restored connections remain disabled.
New tables require the explicit security manifest to be extended; runtime checks
reject missing coverage. Review the [recovery](enterprise-recovery.md) and
[deployment](enterprise-foundation.md) prerequisites as well.

For rollback, stop services and retain the backup. Repair/reapply the grants as
the migration operator; do not disable RLS or grant superuser access to make a
runtime health check green. Do not drop/recreate runtime roles while services
are using them. There is no automatic role deletion or production conversion.

## Qualification Scope

Tests connect as real, separate, non-superuser PostgreSQL logins, not a mocked
database or privileged session using `SET ROLE`. They cover missing filters,
cross-tenant writes/reads, commit/rollback/pool reuse, concurrent organizations,
connection/membership routes, worker claims/heartbeats/publication, artifact hashes
and downloads, holds, cancellation, grant drift and forbidden DDL/evidence erasure.
Collection/token verification uses fixtures; this is not live AWS/Azure or a
deployed IdP qualification. Migration and runtime roles are exercised locally and
in the existing PostgreSQL CI matrix; a hosted result is only claimed after its
run completes. Independent review, production TLS/network/secret qualification,
load testing and recovery objectives remain release gates.
