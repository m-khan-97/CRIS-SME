#!/usr/bin/env python3
"""Build a GitHub Pages-ready static site bundle from CRIS-SME outputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <3.11 fallback
    import tomli as tomllib  # type: ignore[no-redef]


REQUIRED_REPORT_FILES = [
    "cris_sme_dashboard.html",
    "cris_sme_report.html",
    "cris_sme_dashboard_payload.json",
    "cris_sme_report.json",
    "cris_sme_summary.txt",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assemble CRIS-SME reports into a clean static Pages site bundle.",
    )
    parser.add_argument(
        "--reports-dir",
        default="outputs/reports",
        help="Directory containing generated report artifacts.",
    )
    parser.add_argument(
        "--figures-dir",
        default="outputs/figures",
        help="Directory containing generated figure assets.",
    )
    parser.add_argument(
        "--dist-dir",
        default="dist",
        help="Destination distribution directory.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    reports_dir = (repo_root / args.reports_dir).resolve()
    figures_dir = (repo_root / args.figures_dir).resolve()
    dist_dir = (repo_root / args.dist_dir).resolve()
    site_dir = dist_dir / "site"
    manifest_dir = dist_dir / "manifests"
    site_data_dir = site_dir / "data"
    site_assets_figures_dir = site_dir / "assets" / "figures"

    _prepare_directories(dist_dir, site_dir, manifest_dir, site_data_dir, site_assets_figures_dir)
    _assert_required_reports_exist(reports_dir)

    _copy_file(reports_dir / "cris_sme_dashboard.html", site_dir / "dashboard.html")
    _copy_file(reports_dir / "cris_sme_report.html", site_dir / "report.html")
    _copy_file(
        reports_dir / "cris_sme_dashboard_payload.json",
        site_data_dir / "cris_sme_dashboard_payload.json",
    )
    _copy_file(reports_dir / "cris_sme_report.json", site_data_dir / "cris_sme_report.json")
    _copy_file(reports_dir / "cris_sme_summary.txt", site_data_dir / "cris_sme_summary.txt")

    for figure in sorted(figures_dir.glob("*")):
        if figure.is_file() and figure.suffix.lower() in {".svg", ".png"}:
            _copy_file(figure, site_assets_figures_dir / figure.name)

    manifest = _build_manifest(repo_root=repo_root, site_dir=site_dir)
    manifest_path = manifest_dir / "build-metadata.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (site_data_dir / "build-metadata.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    (site_dir / "index.html").write_text(_build_index_html(manifest), encoding="utf-8")
    print(json.dumps({"site_dir": str(site_dir), "manifest": str(manifest_path)}, indent=2))


def _prepare_directories(
    dist_dir: Path,
    site_dir: Path,
    manifest_dir: Path,
    site_data_dir: Path,
    site_assets_figures_dir: Path,
) -> None:
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    site_assets_figures_dir.mkdir(parents=True, exist_ok=True)
    site_data_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    site_dir.mkdir(parents=True, exist_ok=True)


def _assert_required_reports_exist(reports_dir: Path) -> None:
    missing = [name for name in REQUIRED_REPORT_FILES if not (reports_dir / name).exists()]
    if missing:
        joined = ", ".join(missing)
        raise FileNotFoundError(
            f"Missing required report artifacts in {reports_dir}: {joined}. "
            "Run the assessment pipeline before building the Pages site."
        )


def _copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _build_manifest(*, repo_root: Path, site_dir: Path) -> dict[str, object]:
    python_version = ".".join(str(part) for part in sys.version_info[:3])
    project_version = _read_project_version(repo_root / "pyproject.toml")
    generated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    sha = os.getenv("GITHUB_SHA", "local-dev")
    ref = os.getenv("GITHUB_REF", "local")
    run_id = os.getenv("GITHUB_RUN_ID", "local")
    run_number = os.getenv("GITHUB_RUN_NUMBER", "local")
    actor = os.getenv("GITHUB_ACTOR", "local-user")

    checksums = {}
    for relative_path in [
        Path("dashboard.html"),
        Path("report.html"),
        Path("data/cris_sme_dashboard_payload.json"),
        Path("data/cris_sme_report.json"),
        Path("data/cris_sme_summary.txt"),
    ]:
        absolute = site_dir / relative_path
        if absolute.exists():
            checksums[str(relative_path)] = _sha256(absolute)

    return {
        "schema_version": "1.0.0",
        "project": "cris-sme",
        "project_version": project_version,
        "generated_at": generated_at,
        "build": {
            "commit_sha": sha,
            "ref": ref,
            "run_id": run_id,
            "run_number": run_number,
            "actor": actor,
            "python_version": python_version,
        },
        "artifacts": {
            "site_entrypoint": "index.html",
            "dashboard": "dashboard.html",
            "technical_report": "report.html",
            "data_bundle": [
                "data/cris_sme_dashboard_payload.json",
                "data/cris_sme_report.json",
                "data/cris_sme_summary.txt",
                "data/build-metadata.json",
            ],
            "figure_asset_dir": "assets/figures",
            "checksums_sha256": checksums,
        },
    }


def _read_project_version(pyproject_path: Path) -> str:
    if not pyproject_path.exists():
        return "unknown"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    if isinstance(project, dict):
        version = project.get("version")
        if isinstance(version, str):
            return version
    return "unknown"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while True:
            chunk = file.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _build_index_html(manifest: dict[str, object]) -> str:
    generated_at = (
        str(manifest.get("generated_at", "unknown"))
        .replace("T", " ")
        .replace("Z", " UTC")
    )
    build = manifest.get("build", {})
    if not isinstance(build, dict):
        build = {}
    project_version = str(manifest.get("project_version", "unknown"))
    commit_sha = str(build.get("commit_sha", "unknown"))
    short_sha = commit_sha[:12] if commit_sha != "unknown" else "unknown"
    ref = str(build.get("ref", "unknown"))
    run_number = str(build.get("run_number", "unknown"))

    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>CRIS-SME | Cloud Risk Decision Console</title>
    <style>
      :root {{
        --bg: #07101b;
        --panel: #0f1d2d;
        --line: rgba(149, 171, 193, 0.22);
        --ink: #e9f1fb;
        --muted: #9db2c8;
        --accent: #1dc9b7;
        --accent2: #5da3ff;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
        color: var(--ink);
        background:
          radial-gradient(circle at 12% 12%, rgba(29, 201, 183, 0.18), transparent 30%),
          radial-gradient(circle at 84% 18%, rgba(93, 163, 255, 0.16), transparent 32%),
          var(--bg);
      }}
      .wrap {{ max-width: 1100px; margin: 0 auto; padding: 28px 18px 42px; }}
      .hero {{
        background: linear-gradient(140deg, rgba(15, 29, 45, 0.95), rgba(10, 21, 34, 0.95));
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 24px;
      }}
      h1 {{ margin: 0; letter-spacing: -0.02em; font-size: clamp(1.8rem, 3vw, 2.6rem); }}
      .sub {{ color: var(--muted); margin: 10px 0 0; max-width: 80ch; line-height: 1.55; }}
      .grid {{
        margin-top: 18px;
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 14px;
      }}
      .card {{
        background: linear-gradient(180deg, rgba(17, 33, 51, 0.9), rgba(10, 20, 33, 0.96));
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 14px;
      }}
      .card h2 {{ margin: 0 0 8px; font-size: 1.04rem; }}
      .card p {{ margin: 0 0 12px; color: var(--muted); font-size: 0.95rem; line-height: 1.5; }}
      a.link {{
        display: inline-block;
        text-decoration: none;
        color: #03131f;
        background: linear-gradient(120deg, var(--accent), var(--accent2));
        padding: 8px 12px;
        border-radius: 10px;
        font-weight: 700;
      }}
      .meta {{
        margin-top: 18px;
        font-size: 0.92rem;
        color: var(--muted);
        background: rgba(8, 16, 26, 0.75);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 12px;
      }}
      code {{
        padding: 2px 5px;
        border-radius: 6px;
        background: rgba(93, 163, 255, 0.16);
        color: #cbe2ff;
      }}
    </style>
  </head>
  <body>
    <main class="wrap">
      <section class="hero">
        <h1>CRIS-SME Decision Engine</h1>
        <p class="sub">
          Evidence-driven cloud risk intelligence for SMEs with deterministic controls, traceable findings,
          lifecycle-aware governance, and graph-context prioritization.
        </p>
        <div class="grid">
          <article class="card">
            <h2>Interactive Dashboard</h2>
            <p>Executive and technical console with filtering, trend signals, confidence cues, and graph context.</p>
            <a class="link" href="./dashboard.html">Open Dashboard</a>
          </article>
          <article class="card">
            <h2>Technical HTML Report</h2>
            <p>Deterministic control outcomes, evidence-backed findings, and compliance mapping details.</p>
            <a class="link" href="./report.html">Open Report</a>
          </article>
          <article class="card">
            <h2>Machine-Readable Data</h2>
            <p>Structured JSON payloads for automation, audits, and downstream analytics workflows.</p>
            <a class="link" href="./data/cris_sme_dashboard_payload.json">Open Payload</a>
          </article>
        </div>
      </section>

      <section class="meta">
        <div><strong>Build Time:</strong> {generated_at}</div>
        <div><strong>Project Version:</strong> {project_version}</div>
        <div><strong>Git Ref:</strong> <code>{ref}</code></div>
        <div><strong>Commit:</strong> <code>{short_sha}</code></div>
        <div><strong>Run Number:</strong> <code>{run_number}</code></div>
      </section>
    </main>
  </body>
</html>
"""


if __name__ == "__main__":
    main()
