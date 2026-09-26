"""Fail closed unless a release tag, checkout, version and authored notes agree."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import tomllib

from markdown_it import MarkdownIt


SECTIONS = ("Changes", "Upgrade Notes", "Security", "Known Limitations", "Verification")


def validate_release(root: Path, tag: str) -> Path:
    # Only stable versions are currently supported by the release workflow.
    if not re.fullmatch(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", tag):
        raise ValueError("Release tag must be a stable vMAJOR.MINOR.PATCH version")

    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=root, check=True,
                              capture_output=True, text=True).stdout.strip()

    commit = git("rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}")
    if commit != git("rev-parse", "HEAD"):
        raise ValueError("Release tag does not identify the checked-out commit")
    if git("status", "--porcelain", "--untracked-files=normal"):
        raise ValueError("Release checkout must be clean before building")
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    if project["project"]["version"] != tag[1:]:
        raise ValueError("Release tag and Python package version differ")
    notes = root / "docs" / "releases" / f"{tag}.md"
    if notes.is_symlink() or not notes.resolve().is_relative_to(root.resolve()):
        raise ValueError("Release notes must be a regular repository-local file")
    git("ls-files", "--error-unmatch", notes.relative_to(root).as_posix())
    tokens = MarkdownIt("commonmark").parse(notes.read_text(encoding="utf-8"))
    sections: dict[str, list[str]] = {}
    current = None
    title = None
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            heading = tokens[index + 1].content
            if token.tag == "h1":
                title = heading
            if token.tag == "h2":
                if heading in sections:
                    raise ValueError(f"Duplicate release-note section: {heading}")
                current = heading
                sections[current] = []
        elif token.type == "inline" and current and tokens[index - 1].type != "heading_open":
            sections[current].append(token.content)
    if title != tag:
        raise ValueError("Release notes must have the release tag as their H1")
    for section in SECTIONS:
        body = " ".join(sections.get(section, [])).strip()
        if not body or re.search(r"\b(TODO|TBD|PLACEHOLDER)\b", body, re.IGNORECASE):
            raise ValueError(f"Release notes need authored content in {section}")
    return notes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--tag", default=os.environ.get("RELEASE_TAG", ""))
    args = parser.parse_args()
    try:
        notes = validate_release(args.root.resolve(), args.tag)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f"Release preflight failed: {exc}")
        return 1
    print(f"Release preflight passed: {args.tag}; notes: {notes.relative_to(args.root.resolve())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
