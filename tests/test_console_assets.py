# Tests for the React assurance console asset contract.
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONSOLE_SRC = ROOT / "frontend" / "console" / "src"


def _iter_source_files():
    for suffix in (".ts", ".tsx", ".css", ".html"):
        yield from CONSOLE_SRC.rglob(f"*{suffix}")
    yield ROOT / "frontend" / "console" / "index.html"


def test_console_source_does_not_depend_on_remote_assets() -> None:
    for path in _iter_source_files():
        text = path.read_text(encoding="utf-8")
        assert "https://" not in text, f"remote URL found in {path}"
        assert "http://" not in text, f"remote URL found in {path}"


def test_console_vite_config_uses_console_subpath_for_builds() -> None:
    vite_config = (ROOT / "frontend" / "console" / "vite.config.ts").read_text(encoding="utf-8")
    assert "/console/" in vite_config


def test_console_router_uses_base_url_for_basename() -> None:
    main = (ROOT / "frontend" / "console" / "src" / "main.tsx").read_text(encoding="utf-8")
    assert "import.meta.env.BASE_URL" in main


def test_console_client_resolves_outputs_relative_to_base_url() -> None:
    client = (ROOT / "frontend" / "console" / "src" / "api" / "client.ts").read_text(
        encoding="utf-8"
    )
    assert "import.meta.env.BASE_URL" in client
