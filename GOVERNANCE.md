# Project Governance

CRIS-SME is currently a maintainer-led, pre-1.0 open-source project. Its shared
platform roadmap also covers CRIS-IoMT and proposed CRIS-PQC work. It is not
represented as an OWASP project or an OpenSSF-badged project.

## Maintainer And Decisions

The current project owner and release contact is Muhammad Ibrahim
([m-khan-97](https://github.com/m-khan-97)). This records the repository owner;
it does not imply an independently staffed security team. Other contributors
are not automatically maintainers or reviewers with release authority.

Propose changes through issues and pull requests. Keep technical decisions,
alternatives, test evidence and unresolved objections in the relevant issue/PR.
The maintainer decides merge and release readiness, considering review feedback
and the [roadmap gates](docs/roadmap.md). Disagreements may be escalated in the
same discussion with a concrete alternative; criticism of ideas is welcome,
personal attacks and disclosure of private information are not.

Security-sensitive changes should receive independent review where a qualified
reviewer is available. When none is available, record that limitation explicitly;
self-review is not independent approval. Changes to governance, evidence labels,
licensing or supported deployment scope require an explicit rationale.

## Access And Continuity

New maintainers require a public nomination, demonstrated sustained contribution,
explicit agreement to responsibilities, and approval by the existing maintainer.
Grant only the access needed, use account MFA, and remove access when responsibility
ends. These are operational requirements, not evidence that account settings
have been audited or that a backup maintainer already exists.

There is currently no documented succession arrangement or confirmed backup
release operator. Establishing one is an open P0-08 item. Do not publish credentials
or recovery codes in the repository. If maintenance pauses, update the support
policy and repository notice rather than leaving unsupported releases implied.

## Evidence And Releases

Do not relabel customer, lab or synthetic evidence to strengthen a claim. Follow
the [capability evidence admission process](docs/capability-evidence.md).
Funding, affiliation, testimonials and review independence must be stated
accurately and used with permission.

Release decisions must record version/source identity, tests, known limitations,
dependency review, and human-readable upgrade/security notes. Automated workflow
success alone is not release approval. Branch protections, signing and independent
release review remain distinct gates; no such guarantees arise from this policy.
The [release preflight](docs/releases/README.md) checks tag/source/version/notes
alignment, and the workflow creates drafts for explicit maintainer review.

See [contribution guidance](CONTRIBUTING.md), [security policy](SECURITY.md),
[support policy](SUPPORT.md) and [OpenSSF evidence register](docs/openssf-evidence.md).
