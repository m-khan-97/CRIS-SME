# Public Exposure Mode

Public Exposure Mode adds a scoped, user-authorised endpoint assessment to CRIS-SME.

It is deliberately separate from the Azure live collector. Azure assessment answers governance questions from authenticated cloud-control-plane evidence. Public Exposure Mode answers a narrower question:

> What can be observed from the public internet for targets the user is authorised to assess?

## What It Checks

For each supplied target, CRIS-SME records:

- DNS A/AAAA resolution
- passive DNS policy records where observable through the local resolver tooling:
  - SPF TXT
  - DMARC TXT
  - MTA-STS TXT
  - TLS-RPT TXT
  - CAA
- DKIM discovery boundary, without guessing selectors
- HTTP reachability
- HTTPS reachability
- HTTP-to-HTTPS redirect behaviour
- TLS certificate metadata
- TLS protocol-version observation: the negotiated default handshake, plus explicit probes for deprecated TLS 1.0/1.1 support (distinguishing "server rejected it" from "this runtime's OpenSSL build cannot even attempt it," so a probe-unavailable version is never reported as absent)
- common HTTPS security-header presence
- `/.well-known/security.txt` presence
- optionally, when `scan_common_ports` is explicitly enabled: whether a fixed list of common administrative/database ports (21/22/23/25/445/3306/3389/5432/6379/9200/27017 — FTP/SSH/Telnet/SMTP/SMB/MySQL/RDP/PostgreSQL/Redis/Elasticsearch/MongoDB) accepts a TCP connection. This is connect-or-fail only: no banner is read and no payload is sent.

The implementation generates public exposure findings:

- `PE-000`: private or local target excluded
- `PE-001`: target did not resolve
- `PE-002`: HTTP reachable but HTTPS unavailable
- `PE-003`: security headers missing on HTTPS response
- `PE-004`: TLS certificate expires within 30 days
- `PE-005`: HTTP does not redirect to HTTPS
- `PE-006`: DMARC record not observed
- `PE-007`: SPF record not observed
- `PE-008`: CAA record not observed
- `PE-009`: `security.txt` not observed
- `PE-010`: a common administrative/database port accepted a connection from the internet (only generated when `scan_common_ports` is enabled)
- `PE-011`: the server accepted a TLS handshake using a deprecated protocol version (TLS 1.0/1.1)

## What It Does Not Do

Public Exposure Mode does not:

- exploit vulnerabilities
- brute-force authentication
- crawl applications
- submit forms
- fuzz parameters
- guess DKIM selectors
- enumerate subdomains
- sweep arbitrary TCP ports — it scans a fixed list of common administrative/database ports only, and only when explicitly enabled via `scan_common_ports` (off by default)
- run internet-wide scans
- test targets that the user has not explicitly authorised

This keeps the feature aligned with CRIS-SME's evidence and trust model.

## Local API

The local runner exposes:

`POST /api/public-exposure`

Example request:

```json
{
  "targets": "example.com\nhttps://app.example.com",
  "authorization_confirmed": true,
  "scan_common_ports": false
}
```

`scan_common_ports` is optional and defaults to `false`.

The API writes:

- `outputs/reports/cris_sme_public_exposure.json`
- `outputs/reports/cris_sme_public_exposure.md`

## Frontend Workflow

In the Assurance Console:

1. Open **Public Exposure**.
2. Enter one authorised target per line.
3. Confirm authorisation.
4. Optionally enable the common-port scan checkbox.
5. Run the check.
6. Review DNS, HTTP, HTTPS, TLS, and finding output.

DNS policy checks are passive and best-effort. If local DNS tooling cannot retrieve TXT or CAA records, CRIS-SME records the evidence gap instead of treating the absence as proof.

## Research Value

For the paper and product roadmap, this feature gives CRIS-SME a second evidence modality:

- authenticated cloud governance evidence
- unauthenticated public endpoint evidence

The important novelty is not the endpoint checks alone. The stronger contribution is that CRIS-SME keeps these evidence classes separated, labelled, and bounded, instead of blending them into an opaque scan score.
