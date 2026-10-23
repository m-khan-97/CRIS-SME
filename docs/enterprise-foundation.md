# Enterprise Backend Foundation

This is an **opt-in backend**, separate from the unauthenticated local runner.
Do not expose the legacy runner or connect the existing local console to a shared
enterprise deployment. The current console has not been migrated to enterprise
sign-in and tenant APIs. The versioned OpenAPI interface provides the initial
browser/API integration surface. This is not a production-readiness certification.

## Implemented Boundary

- FastAPI `/api/v1` request/response contracts and an authorization-code/PKCE
  Swagger interface. Connection response models exclude credential fields.
- RS256 access-token validation against an operator-configured HTTPS issuer,
  audience and JWKS URL. Required claims, expiry, issued-at and one-hour maximum
  lifetime are enforced. Tokens require `cris.api` scope (`scope` or Entra `scp`); ID tokens without that
  API scope are rejected. Bearer headers only; no authentication cookies or local
  password store. Issuer and subject together identify membership.
- PostgreSQL memberships: owner, admin, operator, analyst and auditor. Roles in
  token claims confer no permissions. Membership is checked on each request.
  Only owners grant/revoke ownership; the last owner cannot be removed. Bootstrap
  is an explicit operator command, not a public tenant-creation endpoint.
  Removing an operator or demoting them to a read-only role also cancels their
  queued jobs and requests cancellation of their active jobs.
- Tenant-scoped connections, jobs, artifact IDs and audit events. Object lookups
  cannot switch tenant from a display name, cloud account or caller-supplied path.
  Unknown and foreign objects return 404; insufficient member roles return 403.
- Fernet-encrypted cloud connection secrets. Encryption keys stay outside the
  database and source tree. Secrets are not returned in connection listings or
  validation errors. AWS onboarding exposes the external ID only to administrators.
- PostgreSQL queue claims using `FOR UPDATE SKIP LOCKED`; per-attempt random leases,
  heartbeats, expiry/reclaim and at most three attempts after worker loss. Expired
  leases cannot complete or publish. Per-tenant admission allows two nonterminal
  jobs. An idempotency key reuses the same job for the same connection and conflicts
  if reused for another connection. This is not exactly-once cloud execution.
- Cancellation/disconnection prevents queued work and causes active workers to
  stop at the next heartbeat. Publication rechecks the lease and connection; a
  cancelled/disconnected job cannot publish success. Old attempts retain private
  files but cannot register them as completed artifacts.
- Outputs live under `<root>/<tenant-id>/<job-id>/<lease-token>/reports`. Only a
  fixed export allowlist is indexed. Downloads require tenant membership and a
  completed job, use no-follow bounded reads, and verify stored size/SHA-256.
  HTML is downloaded as an attachment, never served inline. Local shared volumes
  are implemented; managed object-storage backends are not yet implemented.

## Install And Configure

```bash
python -m pip install --require-hashes -r requirements/enterprise.txt
python -m pip install --no-deps .
```

Provide these variables through a private secret manager or protected environment
file, not CLI arguments or committed `.env` files:

| Variable | Value |
| --- | --- |
| `CRIS_ENTERPRISE_DATABASE_URL` | `postgresql+psycopg://...` for a dedicated database |
| `CRIS_ENTERPRISE_ENCRYPTION_KEY` | Fernet key, generated once and backed up privately |
| `CRIS_ENTERPRISE_OIDC_ISSUER` | Exact trusted HTTPS issuer, including trailing slash if used |
| `CRIS_ENTERPRISE_OIDC_AUDIENCE` | API resource audience, not an unrelated ID-token client |
| `CRIS_ENTERPRISE_JWKS_URL` | Explicit HTTPS signing-key endpoint; never taken from a token |
| `CRIS_ENTERPRISE_OIDC_CLIENT_ID` | Public browser client registered for authorization code + PKCE |
| `CRIS_ENTERPRISE_AUTHORIZE_URL` | Trusted HTTPS authorization endpoint |
| `CRIS_ENTERPRISE_TOKEN_URL` | Trusted HTTPS token endpoint |
| `CRIS_ENTERPRISE_ARTIFACT_ROOT` | Private volume shared by API and worker |
| `CRIS_ENTERPRISE_ALLOWED_HOSTS` | Exact comma-separated hostnames, no wildcard |
| `CRIS_ENTERPRISE_AWS_PRINCIPAL_ARN` | Service-owned backend IAM role allowed to assume customer roles |

Generate a Fernet key with `python -c "from cryptography.fernet import Fernet;
print(Fernet.generate_key().decode())"` in a private terminal. Key loss makes stored
credentials unreadable. Key rotation requires a controlled re-encryption process;
automated key rotation is not supplied. Back up both the database and encryption
key separately, and back up the artifact volume consistently.

The OIDC client must request an **API access token** with audience configured
above and `cris.api` scope. Register the actual HTTPS Swagger callback:
`https://<api-host>/docs/oauth2-redirect`. Configure provider consent, logout and
browser CORS there. The API does not invent an identity provider or customer
consent. JWKS responses are HTTPS-only, nonredirecting, proxy-independent and
bounded to 256 KiB/32 keys; cached keys refresh after 60 seconds. Overlap old/new
keys during rotation. Failed key retrieval has a five-second retry backoff.
Unknown keys fail closed, rather than triggering an
unbounded refresh per attacker-controlled `kid`.

## Migrate, Bootstrap And Run

```bash
python -m cris_sme.enterprise migrate
python -m cris_sme.enterprise bootstrap --name "Example Organization" --subject "<verified-oidc-subject>"
python -m cris_sme.enterprise serve --host 127.0.0.1 --port 8788
```

In a separate process with the same private configuration:

```bash
python -m cris_sme.enterprise worker
```

Migration version 1 is explicit and transactionally serialized with a PostgreSQL
advisory lock. Unsupported schema versions fail closed. No legacy/customer outputs
are imported or reassigned automatically. Review future versioned migrations
before applying them; this initial migration does not provide historical-import
or downgrade tooling.

Open `/api/v1/docs`, authorize using PKCE, then list `/api/v1/tenants`. Bootstrap
prints the new tenant UUID. An owner can add other verified subjects from the
same issuer using the membership API. Authentication success alone grants no
tenant membership. OpenAPI lists the full request/response surface; service errors
are sanitized and carry server-generated request IDs. Request bodies are capped
at 64 KiB with a ten-second receive budget; Uvicorn admits at most 32 connections.
Production TLS, trusted proxy configuration and endpoint rate limits remain
operator responsibilities. No credentialed wildcard CORS is configured.

## AWS Connection

1. An administrator creates an AWS connection with an account ID and matching
   target role ARN. No access keys are accepted in this API.
2. Retrieve its onboarding document. It contains an account-specific external ID
   and a trust policy allowing only the configured backend IAM role.
3. The customer installs the role/trust and documented read permissions. The
   backend's service identity needs permission to assume the target role.
4. Call `verify`: CRIS assumes the role, rejects trusts accepting an absent/wrong
   external ID, and checks the resulting STS account ID. Transient cloud errors
   are not treated as evidence that the negative trust checks were denied.
5. Submit an authorized assessment with `Idempotency-Key`. The worker independently
   assumes the connection's role using its server-side identity.

An account ID alone grants no access. Identity verification is not validation of
all collector permissions or control coverage. Connection verification lasts one
hour for new submissions; repeat verification when required. No live AWS calls
are made automatically by setup or tests.
The initial connector accepts the public AWS partition only; GovCloud/China
collector qualification and Azure sovereign-cloud endpoints are not supplied.

These negative trust checks follow [AWS's third-party access guidance](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_common-scenarios_third-party.html).
AWS external IDs are scope-binding identifiers, not AWS access credentials.

## Azure Connection

An administrator supplies the target tenant, subscription and application UUIDs
and an application secret over TLS. The encrypted credential is used explicitly
by the worker; no machine-level `az login` is required. Verification reads the
subscription using that application and checks the returned scope. Grant only
the documented read permissions; Microsoft Graph access is separate. This is an
application-credential onboarding implementation, **not** a customer consent
wizard or Azure Lighthouse/workload-federation implementation. Secret expiry and
rotation must be managed externally. Those alternatives remain roadmap work.

Disconnection is irreversible for that connection ID. Create and verify a new
connection to reconnect. Disconnection stops new jobs and cancels pending/active
jobs; it does not delete historical reports or revoke credentials inside AWS or
Azure. Remove those cloud-side grants separately when offboarding.

## Worker And Storage Limits

Workers use 30-second leases and heartbeats every ten seconds. Lease extension
requires the current token, unexpired lease and enabled connection. Cancellation
latency is normally one heartbeat plus subprocess cleanup, not instantaneous.
Assessment processes use the existing 900-second timeout, bounded captured output
and POSIX process-group cleanup. Never run arbitrary customer commands in workers.

Leases fence publication, not physical cloud execution: a dead worker's orphan
process may overlap a reclaimed attempt. Use container/cgroup supervision and
stop all old processes during crash recovery. Stale attempt files require a
retention/garbage-collection policy. The service does not provide storage quotas,
object-store immutability, transactional database-plus-filesystem writes, automated
restore verification, distributed rate limits or independent security review.

Use `GET /health` for liveness and `/ready` for schema/write readiness. Readiness
does not establish cloud permissions or identity-provider availability. Audit
events record successful administrative/job actions, not a complete SIEM-grade
authentication/denial log. Protect PostgreSQL, the volume and service identities
from hostile local users; API tenant checks are not OS/container isolation.

## Compose And Verification

`compose.enterprise.yml` defines PostgreSQL, an explicit migration init job, API
and worker. It requires `CRIS_ENTERPRISE_POSTGRES_PASSWORD` plus the path in
`CRIS_ENTERPRISE_ENV_FILE`. That file's database URL must address the Compose
service `postgres` using the same database/user/password. API access remains bound
to loopback port 8788; PostgreSQL is not published. Supply real identity-provider
configuration before `docker compose -f compose.enterprise.yml up --build`.
Docker execution must be verified in an environment with daemon access.

Enterprise tests use real signed fixture tokens and disposable schemas in a
dedicated PostgreSQL test database:

```bash
CRIS_TEST_DATABASE_URL=postgresql+psycopg://... python -m pytest tests/enterprise -q
```

The variable must never point at a customer database. Tests create/drop only
random `test_<uuid>` schemas. CI supplies a dedicated PostgreSQL service on both
Python versions. Tests cover identity/role failures, cross-tenant references,
immediate membership revocation, secret redaction/encryption, idempotency,
connection cancellation, concurrent claims, expired leases and artifact integrity.
Cloud provider calls are fixtures, not live provider qualification. Real OIDC
browser sign-in, customer authorization, cloud verification and deployment review
are required before any production use. The existing console remains local-only
until its enterprise session, connection and tenant context migration is completed.

The Compose definition is a development/reference topology, not hardened production
configuration. Use separate migration and runtime database roles in production:
migrations need DDL ownership; API/worker roles need only schema access, reads of
the version table, and the required CRUD grants on service tables. Do not run the
application with the PostgreSQL image's bootstrap superuser. Supply TLS for
database connections, secret-manager delivery, tested backups and network egress
policies before shared hosting. The initial SQL migration does not create or grant
these operator-owned database roles automatically.
