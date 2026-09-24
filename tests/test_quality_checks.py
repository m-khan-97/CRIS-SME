from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.check_docs import validate_docs
from scripts.quality_summary import CHECKS, render_summary


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "architecture.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><text>Architecture</text></svg>',
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "![Architecture](docs/architecture.svg)\n", encoding="utf-8"
    )
    return tmp_path


def test_static_diagram_does_not_require_mermaid(docs: Path) -> None:
    assert validate_docs(docs, ("README.md",)) == []


@pytest.mark.parametrize("target", ["missing.md", "docs/missing.svg"])
def test_missing_links_fail(docs: Path, target: str) -> None:
    (docs / "README.md").write_text(f"[Missing]({target})", encoding="utf-8")
    assert "missing local target" in validate_docs(docs, ("README.md",))[0]


@pytest.mark.parametrize("content", ["<svg", "<html/>", "<svg/>"])
def test_invalid_svg_fails(docs: Path, content: str) -> None:
    (docs / "docs" / "architecture.svg").write_text(content, encoding="utf-8")
    assert "invalid SVG" in validate_docs(docs, ("README.md",))[0]


def test_markdown_references_encoded_paths_and_code(docs: Path) -> None:
    (docs / "docs" / "with spaces.md").write_text("# Title", encoding="utf-8")
    (docs / "README.md").write_text(
        "[reference][page]\n\n[page]: docs/with%20spaces.md#title\n\n"
        "`[example](not-a-file.md)`\n\n```md\n[example](missing.md)\n```\n"
        "[remote](https://example.invalid/not-fetched) [anchor](#title)\n",
        encoding="utf-8",
    )
    assert validate_docs(docs, ("README.md",)) == []


@pytest.mark.parametrize("target", ["../outside.md", "/home/user/private.md", "%2e%2e/outside.md"])
def test_nonportable_local_links_fail(docs: Path, target: str) -> None:
    (docs / "README.md").write_text(f"[Outside]({target})", encoding="utf-8")
    assert "non-portable local link" in validate_docs(docs, ("README.md",))[0]


def test_missing_entry_document_fails(docs: Path) -> None:
    assert validate_docs(docs, ("missing.md",)) == ["missing.md: missing document"]


def successful_steps() -> dict:
    return {key: {"outcome": "success"} for key, _ in CHECKS}


def test_summary_success_requires_all_checks() -> None:
    summary = render_summary(successful_steps(), run_pipeline=True, upload_artifacts=True)
    assert "**success**" in summary


@pytest.mark.parametrize(
    ("outcome", "overall"),
    [("failure", "failure"), ("cancelled", "cancelled"), ("skipped", "incomplete")],
)
def test_summary_never_masks_unsuccessful_check(outcome: str, overall: str) -> None:
    steps = successful_steps()
    steps["tests"] = {"outcome": outcome, "conclusion": "success"}
    summary = render_summary(steps, run_pipeline=True, upload_artifacts=True)
    assert f"**{overall}**" in summary
    assert "**success**" not in summary
    assert f"| Tests | {outcome} |" in summary


def test_missing_outcome_is_not_success() -> None:
    steps = successful_steps()
    del steps["lint"]
    assert "**incomplete**" in render_summary(steps, run_pipeline=True, upload_artifacts=True)


def test_caller_disabled_steps_are_explicit() -> None:
    steps = successful_steps()
    for key in ("pipeline", "outputs", "replay", "upload"):
        steps[key] = {"outcome": "skipped"}
    summary = render_summary(steps, run_pipeline=False, upload_artifacts=False)
    assert "**success**" in summary
    assert summary.count("skipped (disabled by caller)") == 4


def test_failed_optional_step_is_not_hidden() -> None:
    steps = successful_steps()
    steps["upload"] = {"outcome": "failure"}
    assert "**failure**" in render_summary(steps, run_pipeline=False, upload_artifacts=False)


def test_summary_cli_appends_real_outcomes(tmp_path: Path) -> None:
    output = tmp_path / "summary.md"
    output.write_text("Previous summary\n", encoding="utf-8")
    steps = successful_steps()
    steps["docs"] = {"outcome": "failure"}
    script = Path(__file__).resolve().parents[1] / "scripts" / "quality_summary.py"
    subprocess.run(
        [sys.executable, str(script)], check=True,
        env={**os.environ, "QUALITY_STEPS": json.dumps(steps),
             "RUN_MOCK_PIPELINE": "true", "UPLOAD_GENERATED_ARTIFACTS": "true",
             "GITHUB_STEP_SUMMARY": str(output)},
    )
    summary = output.read_text(encoding="utf-8")
    assert summary.startswith("Previous summary\n")
    assert "**failure**" in summary
    assert "| Documentation | failure |" in summary
