from pathlib import Path

from scripts import validate_paper_package


def test_cyber_essentials_paper_package_validates() -> None:
    assert validate_paper_package.main([]) == 0


def test_forbidden_phrase_check_catches_stale_wording(tmp_path: Path) -> None:
    root = tmp_path / "paper"
    root.mkdir()
    (root / "main.md").write_text("Pending external human cross-check", encoding="utf-8")

    errors = validate_paper_package._validate_claim_language(root)

    assert errors
    assert "pending external human cross-check" in errors[0].lower()
