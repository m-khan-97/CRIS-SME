"""Generate checksums for the exact expected release asset set, without signing it."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re


def expected_assets(tag: str) -> set[str]:
    if not re.fullmatch(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", tag):
        raise ValueError("Expected a stable vMAJOR.MINOR.PATCH tag")
    return {
        f"cris-sme-site-{tag}.tar.gz", f"cris-sme-site-{tag}.zip",
        f"cris-sme-reports-{tag}.tar.gz", "release-notes.md",
        "build-metadata.json", "python-licenses.json", "npm-licenses.json",
    }


def write_checksums(directory: Path, tag: str) -> Path:
    expected = expected_assets(tag)
    if directory.is_symlink():
        raise ValueError("Release directory must not be a symlink")
    actual = {path.name for path in directory.iterdir()} - {"SHA256SUMS"}
    if actual != expected:
        raise ValueError(f"Release asset mismatch: missing={sorted(expected - actual)}, "
                         f"unexpected={sorted(actual - expected)}")
    destination = directory / "SHA256SUMS"
    if destination.is_symlink():
        raise ValueError("Checksum output must not be a symlink")
    rows = []
    for name in sorted(expected):
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"Release asset must be a nonempty regular file: {name}")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        rows.append(f"{digest}  {name}\n")
    destination.write_text("".join(rows), encoding="ascii")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path("dist/release"))
    parser.add_argument("--tag", default=os.environ.get("RELEASE_TAG", ""))
    args = parser.parse_args()
    try:
        output = write_checksums(args.directory, args.tag)
    except (OSError, ValueError) as exc:
        print(f"Release checksum generation failed: {exc}")
        return 1
    print(f"Wrote {output}; integrity checksums only, not signed provenance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
