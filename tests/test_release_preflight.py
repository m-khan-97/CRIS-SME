from pathlib import Path
import subprocess

import pytest

from scripts.check_release import SECTIONS, validate_release


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.fixture
def release(tmp_path: Path) -> Path:
    git(tmp_path, "init")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    git(tmp_path, "config", "user.name", "Release fixture")
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.1.0"\n')
    notes = tmp_path / "docs/releases/v0.1.0.md"
    notes.parent.mkdir(parents=True)
    notes.write_text("# v0.1.0\n\n" + "\n\n".join(
        f"## {section}\n\nReviewed fixture content." for section in SECTIONS))
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "Fixture")
    git(tmp_path, "tag", "v0.1.0")
    return tmp_path


def retag(root: Path) -> None:
    git(root, "add", ".")
    git(root, "commit", "-m", "Updated fixture")
    git(root, "tag", "-f", "v0.1.0")


def test_matching_release_passes(release: Path) -> None:
    assert validate_release(release, "v0.1.0").name == "v0.1.0.md"


@pytest.mark.parametrize("tag", ["", "v01.0.0", "v0.1", "v0.1.0-rc1", "../v0.1.0", 'v0.1.0"; echo unsafe'])
def test_invalid_tag_is_rejected_before_git(release: Path, tag: str) -> None:
    with pytest.raises(ValueError, match="stable"):
        validate_release(release, tag)


def test_missing_tag_fails(release: Path) -> None:
    with pytest.raises(subprocess.CalledProcessError):
        validate_release(release, "v0.2.0")


def test_different_checkout_fails(release: Path) -> None:
    git(release, "commit", "--allow-empty", "-m", "Later commit")
    with pytest.raises(ValueError, match="checked-out"):
        validate_release(release, "v0.1.0")


def test_dirty_checkout_fails(release: Path) -> None:
    (release / "unreviewed.txt").write_text("extra file")
    with pytest.raises(ValueError, match="clean"):
        validate_release(release, "v0.1.0")


def test_version_mismatch_fails(release: Path) -> None:
    (release / "pyproject.toml").write_text('[project]\nversion = "0.2.0"\n')
    retag(release)
    with pytest.raises(ValueError, match="package version"):
        validate_release(release, "v0.1.0")


@pytest.mark.parametrize("section", SECTIONS)
def test_placeholder_notes_fail(release: Path, section: str) -> None:
    notes = release / "docs/releases/v0.1.0.md"
    notes.write_text(notes.read_text().replace(f"## {section}\n\nReviewed fixture content.",
                                              f"## {section}\n\nTODO"))
    retag(release)
    with pytest.raises(ValueError, match="authored"):
        validate_release(release, "v0.1.0")


def test_missing_notes_fail(release: Path) -> None:
    (release / "docs/releases/v0.1.0.md").unlink()
    retag(release)
    with pytest.raises(subprocess.CalledProcessError):
        validate_release(release, "v0.1.0")


@pytest.mark.parametrize("change", ["title", "duplicate", "empty", "comment_only"])
def test_notes_structure_is_checked(release: Path, change: str) -> None:
    notes = release / "docs/releases/v0.1.0.md"
    content = notes.read_text()
    if change == "title":
        content = content.replace("# v0.1.0", "# v0.2.0")
    elif change == "duplicate":
        content += "\n\n## Changes\n\nAnother section."
    else:
        body = "" if change == "empty" else "<!-- add content later -->"
        content = content.replace("## Changes\n\nReviewed fixture content.", f"## Changes\n\n{body}")
    notes.write_text(content)
    retag(release)
    with pytest.raises(ValueError):
        validate_release(release, "v0.1.0")


def test_annotated_tag_passes(release: Path) -> None:
    git(release, "tag", "-f", "-a", "v0.1.0", "-m", "Annotated fixture")
    assert validate_release(release, "v0.1.0").is_file()
