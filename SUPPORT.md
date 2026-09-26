# Support Policy

CRIS-SME is a pre-1.0 project. The current development line receives best-effort
maintenance; there are no guaranteed support hours, response times, LTS releases
or backports. Pin a reviewed commit and retain its dependency locks and evidence
when evaluating it. A moving `main` branch is not a stable production release.

| Area | Current boundary |
| --- | --- |
| Python | 3.11 and 3.12 local/CI test matrix; other versions not qualified. |
| Console build | Node 22; desktop Chromium fixture workflow coverage. |
| Deployment | Isolated, single trusted operator; no shared-hosting assurance. |
| Azure | Implemented collector; actual coverage depends on permissions and scope. |
| AWS | Implemented research-preview collector; per-control limits still apply. |
| GCP / PQC | Planned active capability; no released assurance claim. |
| Compliance | Draft evidence and decision support, not certification. |

See the [quality baseline](docs/quality-baseline.md),
[capability register](docs/capability-evidence.md) and
[deployment restrictions](docs/deployment-security.md) for precise limits.

Report non-sensitive bugs or enhancements through
[GitHub issues](https://github.com/m-khan-97/CRIS-SME/issues). Include the commit,
runtime versions, reproduction using synthetic data, expected/actual behavior,
and sanitized logs. For security issues follow [SECURITY.md](SECURITY.md).
Do not attach complete customer reports or credential caches.

Breaking changes and support changes should be called out in release notes and
this policy. Existing reports may require migration; preserve the original rather
than overwriting it. Review release notes and rerun tests before upgrading a
deployment holding evidence. Support and product endorsement must not be inferred
from an academic acceptance, community listing or a future badge application.
