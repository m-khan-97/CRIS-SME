"""Check capability claims against repository-local evidence without changing it."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path, PurePosixPath

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "data/capabilities/schema.json"


def validate_manifest(root: Path, manifest: object) -> list[str]:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = [f"{list(error.absolute_path)}: {error.message}"
              for error in validator.iter_errors(manifest)]
    if errors:
        return errors
    root = root.resolve()
    seen: set[str] = set()

    def local_file(name: str, label: str) -> Path | None:
        path = (root / name).resolve()
        if (PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts
                or "\\" in name or not path.is_relative_to(root)):
            errors.append(f"{label}: evidence must remain inside the repository")
        elif not path.is_file():
            errors.append(f"{label}: missing evidence file: {name}")
        else:
            return path
        return None

    for capability in manifest["capabilities"]:
        identifier = capability["id"]
        if identifier in seen:
            errors.append(f"{identifier}: duplicate capability ID")
        seen.add(identifier)
        for kind in ("implementation", "fixture_tests"):
            for name in capability[kind]:
                local_file(name, f"{identifier}.{kind}")
        for kind in ("live_observations", "independent_reviews"):
            record_paths: set[str] = set()
            for record in capability[kind]:
                label = f"{identifier}.{kind}"
                if record["path"] in record_paths:
                    errors.append(f"{label}: duplicate evidence record")
                record_paths.add(record["path"])
                path = local_file(record["path"], label)
                if path and hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
                    errors.append(f"{label}: evidence digest mismatch: {record['path']}")
                if date.fromisoformat(record["observed_on"]) > date.fromisoformat(manifest["reviewed_on"]):
                    errors.append(f"{label}: observation is later than manifest review")
                if kind == "independent_reviews" and record["independence"] != "independent":
                    errors.append(f"{label}: internal review cannot claim independence")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path, default=Path("data/capabilities/manifest.json"))
    args = parser.parse_args()
    try:
        manifest = json.loads((args.root / args.manifest).read_text(encoding="utf-8"))
        errors = validate_manifest(args.root, manifest)
    except (OSError, ValueError) as exc:
        print(f"Capability validation failed: {exc}")
        return 1
    for error in errors:
        print(error)
    if errors:
        return 1
    print(f"Capability register validated ({len(manifest['capabilities'])} entries). "
          "References checked; evidence truth and test execution require separate review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
