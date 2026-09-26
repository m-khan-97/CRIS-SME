# Dependency License Inventory

CRIS-SME's root [license](../LICENSE) is MIT. Dependency declarations, fonts,
vendored assets, papers and customer artifacts may have separate terms. This
document and the inventory are not a legal compatibility opinion or permission
to redistribute those materials.

## Reproduce The Inventory

Install the locked Python development environment, then run from the repository:

```bash
python scripts/dependency_license_inventory.py --ecosystem python --lock requirements/dev.txt --output quality-artifacts/python-licenses.json
python scripts/dependency_license_inventory.py --ecosystem npm --lock frontend/console/package-lock.json --output quality-artifacts/npm-licenses.json
```

The tool is offline and uses structured package metadata. It never imports
dependency application code, runs package install scripts or queries a registry.
Generated inventories carry the input lock SHA-256 and deterministic sorted
package records. They are excluded from git and retained as CI artifacts.

| Inventory | Included | Not established |
| --- | --- | --- |
| Python | Distributions installed in the executing interpreter, declared SPDX expression, legacy license text and license classifiers | That the environment exactly matches the named lock; absent optional profiles such as MCP; transitive native/OS components |
| npm | Every package record in the v2/v3 lock, with declaration, version, location and dev/optional flags | Which optional/platform packages are actually installed; SPDX validity or compatibility; complete license text |

`needs_review` is a triage flag, not a pass/fail license judgment. Python records
without an explicit expression remain flagged even if legacy metadata exists.
Missing or unclear npm declarations are flagged; other declarations still require
human review. Invalid lock structures fail inventory generation rather than
silently becoming an empty approved list.

Local measurement on 26 September 2026: the locked Python development environment
contained 59 distributions, with 28 lacking explicit license expressions. The
console lock contained 363 package records, with no missing/unclear declarations
under this tool's triage rules. Neither count represents legal clearance.

## Before Distribution

1. Review the exact runtime/build/development dependency set for the artifact.
   Generate each Python extra/profile in a separate clean environment when used.
2. Resolve missing and ambiguous declarations against actual package license
   files and upstream source. Preserve notices required by those terms.
3. Review bundled fonts, native binaries, container/base-image packages, copied
   assets, documentation and research material separately. They are not fully
   inventoried by this tool.
4. Retain the reviewed inventory, source/version identity, notices and reviewer
   decision alongside release evidence. Do not equate metadata collection with
   completing that review.

P0-08 establishes inventory generation, not a complete SBOM, a license allowlist
or distribution approval. Release-specific notices and compatibility review
remain open in the [OpenSSF register](openssf-evidence.md).
