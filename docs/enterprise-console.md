# Enterprise Console

The opt-in enterprise console connects the browser to the versioned
[enterprise backend](enterprise-foundation.md). The existing local and demo
consoles remain separate deployment modes. This is an implemented, fixture-tested
workflow, not approval for public multi-tenant hosting.

## Identity Setup

Register a **public SPA client**, using authorization code flow with PKCE S256.
Do not create or embed a browser client secret. Register the exact callback:

- Development: `http://localhost:5174/auth/callback` (or the exact loopback origin
  approved by your provider).
- Production: `https://<console-host>/auth/callback`.

Configure a cloud-independent OIDC provider that issues the backend's supported
RS256 API access tokens: exact issuer, single API audience, `cris.api` scope,
numeric issue/expiry times, and a lifetime of at most one hour. The SPA ID token
audience is the public client; the **API access token** audience must match
`CRIS_ENTERPRISE_OIDC_AUDIENCE`. The API does not treat ID tokens, browser role
claims or successful IdP sign-in as organization membership. Bootstrap the owner
with the operator CLI before expecting an organization in the browser.

Supply these **public build-time settings** in the console build environment or
an ignored `.env.enterprise.local` file in `frontend/console/`:

```dotenv
VITE_OIDC_AUTHORITY=https://identity.example.com/tenant
VITE_OIDC_CLIENT_ID=public-spa-client-id
VITE_OIDC_SCOPE=openid cris.api
```

For Entra, request the exposed API scope, for example
`openid api://<api-application-id>/cris.api`. An issuer that uses an OAuth
`resource` parameter can set `VITE_OIDC_RESOURCE`; providers requiring an
authorization-request `audience` parameter can set `VITE_OIDC_AUDIENCE`.
These are provider-specific options, not automatic provider qualification.
Ensure discovery and token endpoints permit the exact SPA origin under their
own CORS policy. The backend still validates its independently configured issuer,
JWKS URL and audience. No live provider compatibility is claimed from fixtures.

Never put an Azure application secret, AWS key, database URL, encryption key,
password or OIDC client secret in any `VITE_*` variable: Vite embeds those values
in public JavaScript. Do not configure `VITE_API_BASE_URL` or demo mode for the
enterprise console; incompatible settings produce a locked sign-in screen.

## Run And Deploy

With the enterprise API configured on loopback port 8788:

```bash
cd frontend/console
npm ci
npm run dev:enterprise -- --host 127.0.0.1 --port 5174 --strictPort
```

Open the exact registered loopback origin. The enterprise Vite proxy targets
8788, never the local runner on 8787. Do not expose Vite publicly.

For deployment, run `npm run build:enterprise`. Serve `dist/enterprise/` at the
root of a dedicated HTTPS origin. Reverse-proxy `/api/v1/` to the enterprise API,
and reserve `/health` and `/ready` for your monitoring policy. Configure an SPA
fallback to `index.html` for browser routes, including `/auth/callback`, **not**
for API routes. Keep the backend on a private network and configure its exact
allowed hosts to match your proxy's Host handling. Do not mount the local API,
`outputs/`, customer archives or an artifact volume as public static content.

The build check permits only application assets, the favicon and `index.html`;
it rejects copied sample reports or other public files. Deploy the exact checked
directory. `vite preview` does not supply a production API reverse proxy.
The existing `Dockerfile.enterprise` and Compose topology run the backend, not a
production console/TLS gateway. Review your real gateway, CSP, framing policy,
request limits, IdP origins and access logs before shared hosting.

## Organization And Run Boundaries

- Organizations come from the authenticated membership list, not cloud tags or
  a display-name field. Every workspace page keeps the organization visible,
  alongside the selected cloud scope, actual evidence mode and reported coverage.
- Organization switching aborts outstanding requests and clears the query cache.
  Query keys include organization/run/artifact identifiers; late responses are
  fenced after a scope change. There is no local report or demo fallback.
- Completed-run selection is kept in tab-local session storage under the
  organization ID. A missing/foreign saved selection stays unavailable until
  explicitly changed; it does not silently substitute another organization's run.
- Run lists include queued, running, cancelling, cancelled, failed and completed
  states. Start requires explicit authorization and a recently verified enabled
  connection. Retries after an uncertain response retain the idempotency key.
- Owner/admin/operator roles can submit and cancel. Owners/admins administer
  connections and members; audit access is restricted to owner/admin/auditor.
  Backend authorization remains authoritative for every request.
- Connection disconnection and member removal require explicit confirmation.
  Removing the last owner and unauthorized ownership changes are rejected by
  the backend, not merely hidden in the UI.
- All report-derived views use the selected report context, including budget
  planning, Cyber Essentials, IoMT, evidence and findings. Public exposure remains
  outside this enterprise workflow until its own scoped backend is implemented.

The API currently lists at most 100 jobs and 100 audit events, with no pagination
UI. Older reports must not be interpreted as deleted merely because they are
outside that window. Historical local-runner reports are not auto-imported.
The selected-run date in the selector is its **request time**; the report retains
its own generated timestamp. Backend artifact publication remains allowlisted;
not every legacy export format is available in enterprise mode.

## Session And Export Handling

`oidc-client-ts` handles code flow, state and PKCE. Session tokens and pending
OAuth state use **sessionStorage**, not persistent localStorage. Token expiry,
local sign-out and API 401 clear visible reports and query state. Automatic silent
renew, offline scopes and application-managed passwords are not enabled. Local
sign-out does not log out the identity provider or revoke a copied access token;
the provider session may allow the next sign-in without another password prompt.
As with any token-bearing SPA, XSS can read session storage. A separately reviewed
BFF/HttpOnly-cookie deployment is not supplied by this batch.

Membership is refreshed every 15 seconds and on focus; failures hide the workspace.
Backend checks reject revoked access immediately on the next request. The browser
cannot retract information already read or downloaded before revocation.

Exports are fetched with bearer headers through organization-scoped opaque
artifact IDs. Embedded filesystem paths are stripped from report views and never
become download authority. The browser bounds streamed bytes to the declared
size (maximum 32 MiB), checks SHA-256, then downloads an octet-stream Blob with a
sanitized filename. Tokens are never placed in links or query parameters. HTML
exports are attachments, not injected into the console. Digest checking detects
inconsistent delivery; it is not independent evidence signing or protection from
a compromised backend that can replace both metadata and content.

Azure secrets are password inputs sent once to the authenticated backend and
cleared after submission. They are not placed in browser storage, report state
or React Query mutation variables. This does not make browser memory a secure
vault or remove the need for TLS and backend secret rotation. AWS connection
onboarding displays the backend-generated external ID and trust policy only to
administrators; customer-side role/grant creation is still required.

## Verification And Remaining Gates

```bash
npm run lint
npm run test:coverage
npm run build:enterprise
npm run test:e2e
npm run test:e2e:enterprise
```

Enterprise Chromium tests use an intercepted fixture identity provider and API.
They exercise the actual OIDC library's code-verifier/challenge roundtrip, but
are **not** a live IdP, PostgreSQL-to-browser or customer-cloud acceptance test.
Backend tests separately exercise signed token verification and disposable real
PostgreSQL schemas. No real cloud assessment is launched by browser tests.

Before a shared pilot, qualify the exact IdP, TLS proxy, database grants, worker
identity, AWS/Azure customer authorization and collection permissions together.
Retain independent review, backup/restore, storage/retention, secret rotation,
rate limiting and incident-response gates from the roadmap. Implementing this
console does not close those gates or the overall P1 phase.
