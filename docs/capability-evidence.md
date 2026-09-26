# Capability Evidence Register

The [machine-readable register](../data/capabilities/manifest.json) records the
scope and limits of product capabilities. Its [schema](../data/capabilities/schema.json)
separates implementation from fixture tests, live observations and independent
review. These are separate dimensions, not a maturity score or certification.

## Meaning Of Each Field

| Field | Meaning |
| --- | --- |
| `delivery` | `implemented` has code references; `planned` makes no implementation claim. |
| `implementation` | Repository files implementing the stated scope, not proof of correctness. |
| `fixture_tests` | Tests supporting the scope; execution results are recorded separately in CI. |
| `live_observations` | Admitted records of actual execution, limited to their recorded environment and scope. |
| `independent_reviews` | Admitted reviews by someone independent of implementation, with identity or a stable reviewer reference. |
| `limitations` | Explicit restrictions that must accompany capability claims. |

The initial register contains 13 entries. Live-observation and independent-review
lists are deliberately empty **pending evidence admission**, not a statement that
no live assessment or practitioner engagement has ever occurred. In particular,
historical SIGI engagements and reported practitioner feedback are not erased or
reclassified. Review their original scope, authorization, execution provenance
and permitted disclosure before adding records. Positive walkthrough feedback
alone is not independent adjudication of all controls.

## Admitting Evidence

1. Identify the precise capability and tested scope. A successful run does not
   validate every control, provider, customer account or deployment mode.
2. Preserve original source records. Where disclosure requires redaction, create
   a separate reviewed evidence note describing redactions and the source
   reference; do not overwrite the original or relabel synthetic/lab evidence.
3. Add a repository-local evidence note and its SHA-256 digest, observation date,
   environment, observer and independence classification. Do not publish cloud
   credentials, customer identifiers or private reports without authorization.
4. Obtain maintainer review of the content and run the validator and associated
   tests. Independent review additionally requires a documented relationship
   establishing independence; the schema cannot verify that relationship.
5. Update the register review date. Preserve prior observation records when
   adding newer results; a digest change needs an explicit explanation in review.

```bash
python scripts/validate_capabilities.py
python -m pytest -q tests/test_capabilities.py
```

The check rejects malformed claims, duplicate IDs, missing or escaping local
paths, changed evidence digests, internal reviews labelled as independent, and
observations later than the register review date. PR CI runs it and includes its
actual outcome in the quality summary. It does not run referenced tests, verify
evidence truth, automatically attest authorship, or detect a coordinated rewrite
of a record and its digest. Git review and protected branches remain necessary.

## Boundaries

Provider status remains governed by the control metadata and
[provider capability matrix](provider-capability-matrix.md). This register does
not promote AWS research-preview controls to active or activate GCP. PQC discovery
and hosted tenant isolation are explicitly planned. It is a repository assurance
register, not yet a runtime API or an embedded signed release attestation.

See the [quality baseline](quality-baseline.md),
[deployment restrictions](deployment-security.md) and [roadmap](roadmap.md).
