"""Validate local documentation links and static SVGs without network access."""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

from markdown_it import MarkdownIt


ENTRYPOINTS = (
    "README.md",
    "docs/architecture.md",
    "docs/methodology.md",
    "docs/ci-cd-and-vercel.md",
    "docs/roadmap.md",
    "docs/threat-model.md",
    "docs/deployment-security.md",
    "docs/quality-baseline.md",
    "docs/capability-evidence.md",
)


def validate_docs(root: Path, documents: tuple[str, ...] = ENTRYPOINTS) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    parser = MarkdownIt("commonmark")
    for name in documents:
        source = root / name
        if not source.is_file():
            errors.append(f"{name}: missing document")
            continue
        for token in parser.parse(source.read_text(encoding="utf-8")):
            for child in token.children or []:
                if child.type not in {"image", "link_open"}:
                    continue
                target = child.attrGet("src" if child.type == "image" else "href")
                if not target:
                    continue
                url = urlsplit(target)
                if url.scheme or url.netloc or not url.path:
                    continue
                decoded = unquote(url.path)
                resolved = (source.parent / decoded).resolve()
                if decoded.startswith("/") or not resolved.is_relative_to(root):
                    errors.append(f"{name}: non-portable local link: {target}")
                elif not resolved.exists():
                    errors.append(f"{name}: missing local target: {target}")
                elif resolved.suffix.lower() == ".svg":
                    try:
                        svg = ET.parse(resolved).getroot()
                        if svg.tag != "{http://www.w3.org/2000/svg}svg":
                            raise ValueError("root must be a namespaced SVG element")
                    except (ET.ParseError, ValueError, OSError) as exc:
                        errors.append(f"{name}: invalid SVG {target}: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors = validate_docs(args.root)
    if not (args.root / "vercel.json").is_file():
        errors.append("vercel.json: missing delivery configuration")
    for error in errors:
        print(error)
    if errors:
        return 1
    print(f"Documentation checks passed ({len(ENTRYPOINTS)} entry documents).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
