# Control Metadata

## Coverage

Metadata revision `2.1.0` registers all 36 existing catalog controls: IAM (5),
network (4), data (4), monitoring (4), compute (5), governance (4) and IoMT (10).
This completes roadmap P0-04's catalog migration from five registered controls.
It adds metadata for existing detections, not 31 new detection rules, and does
not change evaluator or scoring logic.

The canonical [catalog](../data/control_catalog.json) owns titles, domains and
remediation summaries/cost tiers. The [registry](../data/control_metadata_v2.json)
adds evidence requirements, risk descriptions, remediation guidance, ownership,
provider status, mapping references and evaluator provenance. Provider statuses
must agree with the policy control specs. AWS and IoMT retain research-preview
labels; GCP remains planned.

## Meaning And Limits

- Registry severity is nominal metadata. Actual finding severity remains the
  evaluator's decision. Newly registered entries record the maximum evaluator
  branch severity and identify that basis explicitly.
- Compliance references are inherited catalog mappings, marked
  `inherited_unvalidated`; schema validation is not assessor validation.
- Freshness windows are provisional metadata review guidance, not a promise
  that the runtime enforces those windows.
- Assurance claim IDs identify review objectives, not automatic attestations.
- New entries supply manual remediation guidance without inventing executable
  remediation snippets. Empty dependencies mean no prerequisite is declared.

This metadata revision does not bump the scoring policy-pack version. Existing
assessment provenance and historical outputs remain unchanged by this migration.

## Validation

After installing the locked development dependencies, run:

```bash
PYTHONPATH=src python scripts/validate_control_metadata.py
python -m pytest -q tests/test_control_metadata_v2_registry.py tests/test_control_pack_validation.py
```

CI validates the published JSON schema, typed fields, exact catalog/registry ID
parity, catalog/spec agreement and declared evaluator locations. The evaluator
inventory inspects literal `control_id` call arguments in control modules; it
does not establish detection correctness or live-provider coverage.

Default registry loading also checks catalog/spec parity. Custom registry paths
can contain partial packs, but relationship references must resolve inside the
pack. Dependencies must be acyclic; related-control links may be cyclic.
Blank guidance, duplicate IDs, normalized provider collisions and duplicate
framework/reference pairs are rejected.

## Adding A Control

1. Implement the evaluator and add the stable ID to the catalog and control specs.
2. Add registry metadata with its evaluator module/function, evidence limits,
   owner, provider status and explicit mapping/severity/freshness provenance.
3. Add positive and negative evaluator fixtures and metadata validation tests.
4. Run the validator, full test suite and installed-package smoke test. Review
   compliance mappings separately before claiming independent validation.

See the [roadmap](roadmap.md) for subsequent detection-quality and assurance gates.
