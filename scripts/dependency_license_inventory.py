"""Inventory declared dependency licenses; never infer legal compatibility."""

from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import platform


def python_inventory(distributions=None) -> list[dict]:
    packages = []
    for dist in metadata.distributions() if distributions is None else distributions:
        info = dist.metadata
        expression = info.get("License-Expression", "").strip()
        classifiers = [value for value in info.get_all("Classifier", [])
                       if value.startswith("License ::")]
        legacy = info.get("License", "").strip()
        packages.append({
            "name": info["Name"], "version": dist.version,
            "license_expression": expression or None,
            "license_classifiers": classifiers,
            "legacy_license": legacy or None,
            "needs_review": not expression,
        })
    return sorted(packages, key=lambda item: (item["name"].lower(), item["version"]))


def npm_inventory(lock: dict) -> list[dict]:
    if lock.get("lockfileVersion") not in (2, 3) or not isinstance(lock.get("packages"), dict):
        raise ValueError("Expected npm lockfile v2/v3 with a packages map")
    packages = []
    for location, info in lock["packages"].items():
        if location == "":
            continue
        if not isinstance(info, dict) or "node_modules/" not in location:
            raise ValueError(f"Unsupported package record: {location}")
        license_value = info.get("license")
        if license_value is not None and not isinstance(license_value, str):
            raise ValueError(f"Non-string license declaration: {location}")
        if not isinstance(info.get("version"), str):
            raise ValueError(f"Missing version (workspace/link requires review): {location}")
        packages.append({
            "name": info.get("name") or location.rsplit("node_modules/", 1)[1],
            "version": info["version"], "location": location,
            "license_declaration": license_value,
            "development": bool(info.get("dev", False)),
            "optional": bool(info.get("optional", False)),
            "needs_review": not license_value or license_value.upper() in {"UNKNOWN", "UNLICENSED"}
                or license_value.upper().startswith("SEE LICENSE"),
        })
    return sorted(packages, key=lambda item: item["location"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ecosystem", choices=("python", "npm"), required=True)
    parser.add_argument("--lock", type=Path,
                        help="npm lockfile, or the lock used to install the current Python environment")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        lock_bytes = args.lock.read_bytes() if args.lock else None
        if args.ecosystem == "npm":
            if lock_bytes is None:
                raise ValueError("--lock is required for npm")
            packages = npm_inventory(json.loads(lock_bytes))
            scope = "All lockfile package records, including uninstalled platform/optional packages"
        else:
            packages = python_inventory()
            scope = "Installed distributions in this interpreter; not a lockfile completeness check"
        result = {
            "schema_version": "1.0", "ecosystem": args.ecosystem,
            "scope": scope, "generator_python": platform.python_version(),
            "lock_sha256": hashlib.sha256(lock_bytes).hexdigest() if lock_bytes else None,
            "package_count": len(packages),
            "needs_review_count": sum(item["needs_review"] for item in packages),
            "notice": "Declared metadata only. No compatibility, attribution-completeness or legal approval claim.",
            "packages": packages,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print(f"License inventory failed: {exc}")
        return 1
    print(f"{args.ecosystem}: {len(packages)} declarations, "
          f"{result['needs_review_count']} requiring metadata review; wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
