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

The setup generates a 30-day private CA and localhost server certificate. The
API adds the CA using `CRIS_ENTERPRISE_OIDC_CA_FILE`, retaining hostname and
certificate verification. No global trust store is changed. The CA issuing
private key is not retained; automatic certificate renewal is not implemented.

Open a separate interactive Chrome/Chromium profile with:

```bash
.venv/bin/python scripts/keycloak_local.py browser
```

The launcher accepts **only this server's public-key pin** for its private
certificate. It does not use a blanket certificate-error bypass or alter your
normal browser profile. Alternatively, trust the public `ca.pem` explicitly in
a suitable local profile. Use `localhost:5174`, not `127.0.0.1:5174`, to match
the registered origin. Development browser flags are not a production solution.

An ordinary browser profile that does not trust this CA will show a generic
sign-in failure when fetching Keycloak discovery. Use the isolated launcher
above. It removes IDE-injected GTK/schema overrides from the child environment
and checks for early browser crashes; startup errors remain in private
`.local/keycloak/browser.log`. Your desktop environment is not modified.

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
