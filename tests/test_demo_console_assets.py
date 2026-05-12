# Tests for the static CRIS-SME demo console asset contract.
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "frontend" / "demo-console"


def test_demo_console_assets_exist_and_use_generated_data() -> None:
    index = (DEMO_DIR / "index.html").read_text(encoding="utf-8")
    styles = (DEMO_DIR / "styles.css").read_text(encoding="utf-8")
    app = (DEMO_DIR / "app.js").read_text(encoding="utf-8")

    assert "CRIS-SME Demo Console" in index
    assert "cris_sme_dashboard_payload.json" in app
    assert "cris_sme_report.json" in app
    assert "cris_sme_selective_disclosure.json" in app
    assert "view-workbench" in index
    assert "view-provenance" in index
    assert "view-disclosure" in index
    assert "view-ce-review-workbench" in index
    assert "Proposed Yes means" in index
    assert "radial-gradient" not in styles
    assert "CE_REVIEW_STORAGE_KEY" in app
    assert "cris_sme_ce_human_review_ledger.csv" in app
    assert "cris_sme_ce_human_review_ledger.json" in app


def test_demo_console_does_not_depend_on_remote_assets() -> None:
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (DEMO_DIR / "index.html", DEMO_DIR / "styles.css", DEMO_DIR / "app.js")
    )

    assert "https://" not in combined
    assert "http://" not in combined
