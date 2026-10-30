# Local Keycloak Identity Pilot

This Linux-only development setup connects real Keycloak sign-in to the
enterprise API and dedicated PostgreSQL. It needs no Azure app registration or
cloud credits. It is not a public deployment or production security approval.

## Local Services

| Component | Endpoint / Storage |
| --- | --- |
| Console | `http://localhost:5174` |
| Keycloak 26.8.1 | `https://localhost:8443`, realm `cris` |
| Enterprise API | `http://127.0.0.1:8788` |
| CRIS PostgreSQL 16 | Loopback port 55433, dedicated private cluster |
| Keycloak database | Private H2 file database, not production storage |
| Worker | Local idle worker; no cloud identity is provisioned |

Keycloak uses `start --db=dev-file --cache=local` with HTTP disabled. Its startup
profile is named `prod`, but this single-node/private-CA/H2 topology is still a
development pilot. Listener inspection confirmed no HTTP port 8080. The console
and API are loopback-only HTTP services, not publicly exposed applications.

The public `cris-console` client requires code flow and PKCE S256. Its exact
redirect URI is `http://localhost:5174/auth/callback`, and its web origin is
`http://localhost:5174`. Password grants, implicit flow and service-account login
are disabled for that client. The `cris.api` scope adds one audience, `cris-api`,
and an explicit subject mapper. Access tokens last five minutes. Keycloak's
subject mapper is important: removing its default `basic` scope without replacing
the `sub` mapper produces tokens CRIS correctly rejects.

Generated owner, analyst and outsider identities exercise two local workspaces,
`CRIS Local Workspace` and `CRIS Isolation Workspace`. They are not customer
identities. Historical scans are not imported or relabelled into them.

## Private State And Browser

Generated credentials, encryption key, TLS material, database, logs and raw test
results live under ignored `.local/keycloak/`, with private file/directory
permissions. The generated realm import contains credentials and remains inside
the ignored Keycloak runtime installation. Neither directory belongs in Git.

Open `.local/keycloak/login.txt` locally for the owner and administrator login
details. Never put those values in chat, public screenshots or `VITE_*` settings.
The bootstrap administrator is for this private pilot, not a production account
lifecycle design.

The setup generates a private CA and a 365-day localhost server certificate. The
API adds the CA using `CRIS_ENTERPRISE_OIDC_CA_FILE`, retaining hostname and
certificate verification. The CA issuing private key is not retained. Startup
renews certificates within 30 days of expiry, archives the old material privately,
and refreshes recorded browser trust. If services are already running, use
`restart` to renew safely. A continuously running pilot must still be restarted
before its certificate expires; this is not a production certificate manager.

For normal Chrome/Chromium on Linux, install `libnss3-tools` and trust the exact
localhost server certificate once (no administrator rights needed for the trust
operation):

```bash
.venv/bin/python scripts/keycloak_local.py trust-browser
.venv/bin/python scripts/keycloak_local.py browser
```

The trust command adds **only the exact non-CA localhost TLS peer** (`P,,`) to
your user NSS certificate database, not the CA or a system-wide trust store.
It follows Chromium's legacy `~/.pki/nssdb` precedence, otherwise uses
`~/.local/share/pki/nssdb`. It backs up the public certificate database without
copying private keys. The tool uses system `certutil`, or an operator-provided
copy extracted from the official Ubuntu `libnss3-tools` package under
`.venv/nss-tools/usr/bin/certutil`. It never downloads executables itself.
See [Chromium's Linux certificate documentation](https://chromium.googlesource.com/chromium/src/+/main/docs/linux/cert_management.md).

The launcher opens your **normal browser**, without TLS bypass flags. If Chrome
was already running when trust was first installed, fully quit and reopen it
once if it still caches the certificate error. Use `http://localhost:5174`, not
`127.0.0.1:5174`, to match the registered origin. Firefox uses a different trust
store and is not configured by this helper. The launcher removes IDE-injected
GTK/schema overrides and checks early browser crashes; errors remain private in
`.local/keycloak/browser.log`.

To undo, run `.venv/bin/python scripts/keycloak_local.py untrust-browser`.
Removal checks the recorded fingerprint and leaves unrelated certificates alone.
Do not restore the whole NSS backup over later user changes. Browser trust is
local development setup, not production identity qualification.

To exercise the real PKCE flow without certificate bypass flags, run from
`frontend/console` (Node 22.12+):

```bash
CRIS_KEYCLOAK_SYSTEM_TRUST=true node scripts/qualify-keycloak.mjs
```

The default qualification mode still uses an isolated, exact-SPKI-pinned browser
for CI environments where changing host trust is inappropriate. Its results
identify the TLS mode explicitly.

## Lifecycle And Reproduction

Prerequisites: enterprise Python dependencies, Node 22.12+ in PATH, PostgreSQL 16
binaries, Keycloak 26.8.1, and the documented Java runtime. OpenJDK 25 was used.
Docker is not required. The one-time preparation on this machine was:

```bash
PYTHONPATH=src .venv/bin/python scripts/keycloak_local.py prepare \
  --keycloak-home .venv/keycloak-26.8.1 \
  --java-home .venv/jdk-25.0.5+8-jre \
  --pg-bin .venv/pg-root/usr/lib/postgresql/16/bin
```

For an existing pilot, with Node 22.12+ in PATH:

```bash
PYTHONPATH=src .venv/bin/python scripts/keycloak_local.py start
.venv/bin/python scripts/keycloak_local.py status
PYTHONPATH=src .venv/bin/python scripts/keycloak_local.py restart
.venv/bin/python scripts/keycloak_local.py stop
```

Preparation refuses to overwrite existing state. Startup migrates the dedicated
database and bootstraps memberships only when absent. Restart retains identities
and data. Stop signals recorded process groups only when their Linux process-start
identity matches, then stops this pilot's PostgreSQL cluster. It leaves unrelated
applications and your browser alone. The private state/process records must be
trusted; this is not an OS sandbox or production service manager.

`sync-realm` adds missing CRIS mappers through the local admin API without
replacing realms or users. This operator-only operation uses the built-in master
`admin-cli`; it does not enable password grants on the CRIS browser client.
Existing mapper settings are not silently overwritten.

Download runtimes from [Keycloak](https://www.keycloak.org/downloads) and
[Eclipse Adoptium](https://adoptium.net/). Executed archive SHA-256 checks were:

| Archive | SHA-256 |
| --- | --- |
| Keycloak 26.8.1 tar.gz | `4e2740b181faa2ea623a1c2ecf00855935311e546046e2f857615a47ed24cbe8` |
| Temurin 25.0.5+8 Linux x64 JRE tar.gz | `6fac98f0c8202efc3135a9e9e42aa61963ec42d1c5cbb40caf231e7b14a24ef6` |

These compare upstream release metadata over HTTPS, not independent supply-chain
attestations. The manual `keycloak-qualification.yml` workflow reproduces the real
identity test with a checksum-verified Keycloak archive and isolated services.
It has not been run remotely for this unpushed batch. Uploads contain only
sanitized outcomes and screenshots, never credentials, database state or logs.

## Qualification Boundaries

With the services running:

```bash
cd frontend/console
npm run qualify:keycloak
```

This exercises real browser login, signed tokens, the API and PostgreSQL. No IdP
or API interception supplies responses, and no cloud request occurs. It temporarily
revokes and restores the generated analyst, then signs the owner out. Only run it
against this dedicated pilot. Private results are in
`.local/keycloak/qualification/`; diagnostic failure text stays private.

The [internal qualification record](qualification/keycloak-local-2026-10-27.md)
documents eight executed checks and their limits. Public TLS, production storage,
MFA, administrator lifecycle, certificate/secret rotation, backups and independent
security review remain separate gates. Local sign-out does not end the IdP's SSO
session or revoke a copied access token.

Cloud qualification is also separate: it needs an explicitly authorized account
and scope, a working AWS backend identity/target role or Azure application/RBAC
grant, actual collection and scoped artifact checks, and revocation tests on the
agreed target. No cloud assessment or infrastructure creation was performed here.
