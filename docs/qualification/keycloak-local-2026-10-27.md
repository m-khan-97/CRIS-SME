# Local Identity Qualification: 27 October 2026

## Scope And Provenance

This is an **internal controlled local identity integration**, not a customer
cloud assessment, practitioner review, public deployment or independent security
audit. Actual Keycloak 26.8.1, the enterprise API and dedicated PostgreSQL 16.15
served Chromium's real code-flow/PKCE sign-in. No intercepted IdP/API responses
or static JWT signing fixtures supplied this observation.

Implementation milestone: `ceeef92` (tested worktree captured in that commit).

The recorded successful execution ran from 17:34:22 to 17:34:35 UTC on
27 October 2026. Reruns exercise the same eight checks. The launcher created three
generated identities and two local workspaces. No pre-existing customer data was
assigned to them. The API verified a private localhost CA; isolated Chromium
pinned the server public key. Keycloak listened on loopback HTTPS only; the
console/API used loopback HTTP.

## Executed Checks

| Check | Observed Result |
| --- | --- |
| Anonymous access / legacy isolation | Protected identity route returned 401; legacy assessment-history route returned 404. |
| Real browser sign-in and membership | Actual signed API token identified the generated owner; PostgreSQL returned its owner membership. |
| ID token as API credential | Rejected with 401. |
| Modified API-token signature | Rejected with 401. |
| Separate identity / foreign organization | Only its own workspace listed; foreign assessment/connection routes returned 404. |
| Analyst permissions | Own assessments readable; connection creation denied with 403, without a cloud call. |
| Existing-token revocation | Owner removed the generated analyst; its current token received 404 for that workspace and its browser removed the workspace. Membership was restored afterward. |
| Console sign-out | Browser session storage cleared; sign-in screen returned without local report fallback. |

All eight checks passed, with no browser page errors observed. Raw results and
screenshots remain in ignored private local state. No passwords, tokens,
encryption keys, private certificates or user identifiers appear in this summary.

## Limits

This supports the tested identity/membership integration, not public PKI,
production hosting, MFA, IdP-wide logout, key/certificate rotation, high
availability, recovery, a BFF design, cloud scanner correctness, worker crash
recovery, evidence sufficiency, or artifact publication/download from a completed
live cloud assessment. Keycloak storage is local H2; app storage is dedicated
PostgreSQL. Services are private, single-node and operator-managed.

No cloud scan ran and no cloud resources were created. The next cloud gate needs
an explicitly authorized target and a working connector identity. This internal
record must not be presented as independent review or an SME outcome study.

## Reproduction

Follow [the pilot guide](../keycloak-local-pilot.md), then run
`npm run qualify:keycloak` from `frontend/console/`. The runner is
`frontend/console/scripts/qualify-keycloak.mjs`; private setup/lifecycle operations
are in `scripts/keycloak_local.py`. The guide records runtime digests and trust
boundaries. Reproduction requires the actual services, not fixture interception.
