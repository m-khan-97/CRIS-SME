import hashlib
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.release_checksums import expected_assets, write_checksums


@pytest.fixture
def assets(tmp_path: Path) -> Path:
    for name in expected_assets("v0.1.0"):
        (tmp_path / name).write_bytes(f"Fixture {name}".encode())
    return tmp_path


def test_checksums_cover_exact_asset_set_and_are_repeatable(assets: Path) -> None:
    output = write_checksums(assets, "v0.1.0")
    initial = output.read_bytes()
    rows = output.read_text().splitlines()
    assert len(rows) == 7
    for row in rows:
        digest, name = row.split("  ")
        assert digest == hashlib.sha256((assets / name).read_bytes()).hexdigest()
    assert write_checksums(assets, "v0.1.0").read_bytes() == initial


@pytest.mark.parametrize("mutation", ["missing", "extra", "empty", "directory", "symlink", "output_symlink"])
def test_incomplete_or_unsafe_assets_fail(assets: Path, mutation: str) -> None:
    target = assets / "release-notes.md"
    if mutation == "missing":
        target.unlink()
    elif mutation == "extra":
        (assets / "customer-report.json").write_text("Must not be published")
    elif mutation == "empty":
        target.write_bytes(b"")
    elif mutation == "output_symlink":
        (assets / "SHA256SUMS").symlink_to(target)
    else:
        target.unlink()
        if mutation == "directory":
            target.mkdir()
        else:
            target.symlink_to(assets / "build-metadata.json")
    with pytest.raises(ValueError):
        write_checksums(assets, "v0.1.0")


@pytest.mark.parametrize("tag", ["../v0.1.0", "v01.0.0", "v0.1.0\n"])
def test_invalid_tag_fails(assets: Path, tag: str) -> None:
    with pytest.raises(ValueError):
        write_checksums(assets, tag)


def test_changed_asset_changes_digest(assets: Path) -> None:
    initial = write_checksums(assets, "v0.1.0").read_bytes()
    (assets / "release-notes.md").write_text("Changed content")
    assert write_checksums(assets, "v0.1.0").read_bytes() != initial


def test_cli_fails_without_assets(tmp_path: Path) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts/release_checksums.py"
    result = subprocess.run([sys.executable, str(script), "--directory", str(tmp_path),
                             "--tag", "v0.1.0"], capture_output=True, text=True)
    assert result.returncode == 1
    assert not (tmp_path / "SHA256SUMS").exists()
