# Lightweight SVG figure export for CRIS-SME research and demo artifacts.
from __future__ import annotations

from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


def write_report_figures(
    report: dict[str, Any],
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write research-facing SVG charts derived from a JSON report."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    category_path = target_dir / "live_category_scores.svg"
    priority_path = target_dir / "live_priority_distribution.svg"
    trend_path = target_dir / "risk_trend.svg"
    comparison_path = target_dir / "run_comparison.svg"
    category_png_path = target_dir / "live_category_scores.png"
    priority_png_path = target_dir / "live_priority_distribution.png"
    trend_png_path = target_dir / "risk_trend.png"
    comparison_png_path = target_dir / "run_comparison.png"

    category_path.write_text(
        build_category_scores_svg(report),
        encoding="utf-8",
    )
    priority_path.write_text(
        build_priority_distribution_svg(report),
        encoding="utf-8",
    )
    trend_path.write_text(
        build_risk_trend_svg([report]),
        encoding="utf-8",
    )
    comparison_path.write_text(
        build_run_comparison_svg([report]),
        encoding="utf-8",
    )
    _write_category_scores_png(report, category_png_path)
    _write_priority_distribution_png(report, priority_png_path)
    _write_risk_trend_png([report], trend_png_path)
    _write_run_comparison_png([report], comparison_png_path)

    return {
        "category_scores": category_path,
        "priority_distribution": priority_path,
        "risk_trend": trend_path,
        "run_comparison": comparison_path,
        "category_scores_png": category_png_path,
        "priority_distribution_png": priority_png_path,
        "risk_trend_png": trend_png_path,
        "run_comparison_png": comparison_png_path,
    }


def write_history_figures(
    reports: list[dict[str, Any]],
    output_dir: str | Path,
) -> dict[str, Path]:
    """Write SVG figures that compare multiple CRIS-SME report snapshots."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    trend_path = target_dir / "risk_trend.svg"
    comparison_path = target_dir / "run_comparison.svg"
    trend_png_path = target_dir / "risk_trend.png"
    comparison_png_path = target_dir / "run_comparison.png"

    trend_path.write_text(build_risk_trend_svg(reports), encoding="utf-8")
    comparison_path.write_text(build_run_comparison_svg(reports), encoding="utf-8")
    _write_risk_trend_png(reports, trend_png_path)
    _write_run_comparison_png(reports, comparison_png_path)

    return {
        "risk_trend": trend_path,
        "run_comparison": comparison_path,
        "risk_trend_png": trend_png_path,
        "run_comparison_png": comparison_png_path,
    }


def build_category_scores_svg(report: dict[str, Any]) -> str:
    """Build an SVG horizontal bar chart for category scores."""
    category_scores = report.get("category_scores", {})
    if not isinstance(category_scores, dict):
        category_scores = {}

    items = list(category_scores.items())
    height = 90 + max(len(items), 1) * 58
    width = 860
    left = 240
    bar_width = 480
    top = 70

    rows = []
    for index, (label, value) in enumerate(items):
        score = _safe_float(value)
        y = top + index * 58
        fill_width = round((score / 100.0) * bar_width, 2)
        rows.extend(
            [
                (
                    f'<text x="24" y="{y + 20}" font-size="18" fill="#17324d">'
                    f'{escape(str(label))}</text>'
                ),
                (
                    f'<rect x="{left}" y="{y}" width="{bar_width}" height="26" '
                    'rx="8" fill="#d9e6f2" />'
                ),
                (
                    f'<rect x="{left}" y="{y}" width="{fill_width}" height="26" '
                    'rx="8" fill="#1f6aa5" />'
                ),
                (
                    f'<text x="{left + bar_width + 18}" y="{y + 20}" font-size="18" '
                    f'fill="#17324d">{score:.2f}</text>'
                ),
            ]
        )

    return _wrap_svg(
        width=width,
        height=height,
        title="CRIS-SME Category Risk Scores",
        subtitle="Live Azure-backed category scores from the current CRIS-SME assessment",
        body="\n".join(rows),
    )


def build_priority_distribution_svg(report: dict[str, Any]) -> str:
    """Build an SVG bar chart for the prioritized risk distribution."""
    risks = report.get("prioritized_risks", [])
    counter = Counter()
    if isinstance(risks, list):
        for risk in risks:
            if isinstance(risk, dict):
                counter[str(risk.get("priority", "Unknown"))] += 1

    labels = ["High", "Monitor", "Planned"]
    width = 760
    height = 420
    baseline_y = 320
    left = 90
    gap = 170
    max_count = max(counter.values(), default=1)

    bars = []
    for index, label in enumerate(labels):
        count = counter.get(label, 0)
        bar_height = round((count / max_count) * 180, 2) if max_count else 0
        x = left + index * gap
        y = baseline_y - bar_height
        color = {
            "High": "#c23b22",
            "Monitor": "#c58b00",
            "Planned": "#2a7f62",
        }.get(label, "#1f6aa5")

        bars.extend(
            [
                (
                    f'<rect x="{x}" y="{y}" width="92" height="{bar_height}" '
                    f'rx="10" fill="{color}" />'
                ),
                (
                    f'<text x="{x + 46}" y="{y - 12}" text-anchor="middle" '
                    f'font-size="22" fill="#17324d">{count}</text>'
                ),
                (
                    f'<text x="{x + 46}" y="{baseline_y + 34}" text-anchor="middle" '
                    f'font-size="18" fill="#17324d">{escape(label)}</text>'
                ),
            ]
        )

    return _wrap_svg(
        width=width,
        height=height,
        title="CRIS-SME Priority Distribution",
        subtitle="Distribution of prioritized non-compliant risks in the current live run",
        body="\n".join(
            [
                '<line x1="70" y1="320" x2="640" y2="320" stroke="#7f97ad" stroke-width="2" />',
                *bars,
            ]
        ),
    )


def build_risk_trend_svg(reports: list[dict[str, Any]]) -> str:
    """Build an SVG line chart of overall risk across archived report snapshots."""
    points = _extract_run_points(reports)
    width = 860
    height = 420
    left = 90
    top = 90
    chart_width = 680
    chart_height = 220

    if not points:
        points = [("No data", 0.0)]

    max_score = max(score for _, score in points) or 1.0
    max_score = max(max_score, 10.0)
    step_x = chart_width / max(len(points) - 1, 1)

    line_points = []
    labels = []
    for index, (label, score) in enumerate(points):
        x = left + index * step_x
        y = top + chart_height - ((score / max_score) * chart_height)
        line_points.append(f"{x:.2f},{y:.2f}")
        labels.append(
            f'<text x="{x:.2f}" y="{top + chart_height + 28}" text-anchor="middle" '
            f'font-size="14" fill="#17324d">{escape(label)}</text>'
        )
        labels.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5.5" fill="#1f6aa5" />'
        )
        labels.append(
            f'<text x="{x:.2f}" y="{y - 12:.2f}" text-anchor="middle" '
            f'font-size="16" fill="#17324d">{score:.2f}</text>'
        )

    body = "\n".join(
        [
            f'<line x1="{left}" y1="{top + chart_height}" x2="{left + chart_width}" '
            f'y2="{top + chart_height}" stroke="#7f97ad" stroke-width="2" />',
            f'<polyline points="{" ".join(line_points)}" fill="none" stroke="#1f6aa5" stroke-width="4" />',
            *labels,
        ]
    )

    return _wrap_svg(
        width=width,
        height=height,
        title="CRIS-SME Overall Risk Trend",
        subtitle="Overall risk score across archived CRIS-SME assessment snapshots",
        body=body,
    )


def build_run_comparison_svg(reports: list[dict[str, Any]]) -> str:
    """Build an SVG comparison chart for the latest archived report snapshots."""
    points = _extract_run_points(reports)[-4:]
    width = 920
    height = 460
    left = 110
    baseline_y = 330
    bar_width = 110
    gap = 170
    max_score = max((score for _, score in points), default=10.0)
    max_score = max(max_score, 10.0)

    bars = []
    for index, (label, score) in enumerate(points):
        x = left + index * gap
        bar_height = round((score / max_score) * 210, 2)
        y = baseline_y - bar_height
        bars.extend(
            [
                (
                    f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" '
                    'rx="10" fill="#1f6aa5" />'
                ),
                (
                    f'<text x="{x + bar_width / 2}" y="{y - 12}" text-anchor="middle" '
                    f'font-size="18" fill="#17324d">{score:.2f}</text>'
                ),
                (
                    f'<text x="{x + bar_width / 2}" y="{baseline_y + 32}" text-anchor="middle" '
                    f'font-size="14" fill="#17324d">{escape(label)}</text>'
                ),
            ]
        )

    if not points:
        bars.append(
            '<text x="120" y="200" font-size="18" fill="#17324d">No archived runs available yet.</text>'
        )

    return _wrap_svg(
        width=width,
        height=height,
        title="CRIS-SME Run Comparison",
        subtitle="Overall risk comparison across the most recent archived assessment runs",
        body="\n".join(
            [
                f'<line x1="90" y1="{baseline_y}" x2="820" y2="{baseline_y}" stroke="#7f97ad" stroke-width="2" />',
                *bars,
            ]
        ),
    )


def _safe_float(value: Any) -> float:
    """Return a float-like value or zero when conversion fails."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _extract_run_points(reports: list[dict[str, Any]]) -> list[tuple[str, float]]:
    """Return compact labels and scores for report-history charting."""
    points: list[tuple[str, float]] = []
    for index, report in enumerate(reports, start=1):
        generated_at = report.get("generated_at")
        collector_mode = str(report.get("collector_mode", "")).strip().lower()
        label = f"Run {index}"
        if isinstance(generated_at, str):
            try:
                parsed = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
                label = parsed.strftime("%d %b")
            except ValueError:
                label = generated_at[:10]
        if collector_mode:
            label = f"{label} {collector_mode}"
        score = _safe_float(report.get("overall_risk_score"))
        points.append((label, score))
    return points


def _wrap_svg(*, width: int, height: int, title: str, subtitle: str, body: str) -> str:
    """Wrap a chart body in a simple CRIS-SME SVG frame."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
  <title id="title">{escape(title)}</title>
  <desc id="desc">{escape(subtitle)}</desc>
  <rect width="{width}" height="{height}" fill="#f6fbff" rx="18" />
  <text x="24" y="34" font-size="26" font-weight="700" fill="#12314b">{escape(title)}</text>
  <text x="24" y="58" font-size="15" fill="#547089">{escape(subtitle)}</text>
  {body}
</svg>
"""


def _write_category_scores_png(report: dict[str, Any], output_path: Path) -> None:
    """Write a PNG horizontal bar chart for category scores."""
    category_scores = report.get("category_scores", {})
    items = list(category_scores.items()) if isinstance(category_scores, dict) else []
    width = 980
    height = 120 + max(len(items), 1) * 64
    image, draw = _new_canvas(width, height)
    title_font, body_font, small_font = _load_fonts()

    draw.text((32, 24), "CRIS-SME Category Risk Scores", fill="#12314b", font=title_font)
    draw.text(
        (32, 58),
        "Live Azure-backed category scores from the current CRIS-SME assessment",
        fill="#547089",
        font=small_font,
    )

    left = 290
    bar_width = 520
    top = 100
    for index, (label, value) in enumerate(items):
        y = top + index * 64
        score = _safe_float(value)
        fill_width = (score / 100.0) * bar_width
        draw.text((32, y + 2), str(label), fill="#17324d", font=body_font)
        draw.rounded_rectangle((left, y, left + bar_width, y + 28), radius=8, fill="#d9e6f2")
        draw.rounded_rectangle((left, y, left + fill_width, y + 28), radius=8, fill="#1f6aa5")
        draw.text((left + bar_width + 18, y + 2), f"{score:.2f}", fill="#17324d", font=body_font)

    image.save(output_path)


def _write_priority_distribution_png(report: dict[str, Any], output_path: Path) -> None:
    """Write a PNG bar chart for priority distribution."""
    risks = report.get("prioritized_risks", [])
    counter = Counter()
    if isinstance(risks, list):
        for risk in risks:
            if isinstance(risk, dict):
                counter[str(risk.get("priority", "Unknown"))] += 1

    labels = ["High", "Monitor", "Planned"]
    width = 900
    height = 480
    image, draw = _new_canvas(width, height)
    title_font, body_font, small_font = _load_fonts()
    draw.text((32, 24), "CRIS-SME Priority Distribution", fill="#12314b", font=title_font)
    draw.text(
        (32, 58),
        "Distribution of prioritized non-compliant risks in the current live run",
        fill="#547089",
        font=small_font,
    )

    baseline_y = 360
    left = 140
    gap = 210
    max_count = max(counter.values(), default=1)
    draw.line((110, baseline_y, 760, baseline_y), fill="#7f97ad", width=3)

    colors = {"High": "#c23b22", "Monitor": "#c58b00", "Planned": "#2a7f62"}
    for index, label in enumerate(labels):
        count = counter.get(label, 0)
        x = left + index * gap
        bar_height = int((count / max_count) * 200) if max_count else 0
        y = baseline_y - bar_height
        draw.rounded_rectangle((x, y, x + 110, baseline_y), radius=12, fill=colors[label])
        draw.text((x + 35, y - 32), str(count), fill="#17324d", font=body_font)
        draw.text((x + 18, baseline_y + 18), label, fill="#17324d", font=body_font)

    image.save(output_path)


def _write_risk_trend_png(reports: list[dict[str, Any]], output_path: Path) -> None:
    """Write a PNG line chart for overall risk trend."""
    points = _extract_run_points(reports)
    width = 980
    height = 500
    image, draw = _new_canvas(width, height)
    title_font, body_font, small_font = _load_fonts()
    draw.text((32, 24), "CRIS-SME Overall Risk Trend", fill="#12314b", font=title_font)
    draw.text(
        (32, 58),
        "Overall risk score across archived CRIS-SME assessment snapshots",
        fill="#547089",
        font=small_font,
    )

    if not points:
        points = [("No data", 0.0)]

    left = 110
    top = 110
    chart_width = 760
    chart_height = 240
    max_score = max(max(score for _, score in points), 10.0)
    step_x = chart_width / max(len(points) - 1, 1)
    draw.line((left, top + chart_height, left + chart_width, top + chart_height), fill="#7f97ad", width=3)

    coords = []
    for index, (label, score) in enumerate(points):
        x = left + index * step_x
        y = top + chart_height - ((score / max_score) * chart_height)
        coords.append((x, y))
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill="#1f6aa5")
        draw.text((x - 18, y - 32), f"{score:.2f}", fill="#17324d", font=small_font)
        draw.text((x - 28, top + chart_height + 18), label, fill="#17324d", font=small_font)
    if len(coords) > 1:
        draw.line(coords, fill="#1f6aa5", width=4)

    image.save(output_path)


def _write_run_comparison_png(reports: list[dict[str, Any]], output_path: Path) -> None:
    """Write a PNG comparison chart for the most recent runs."""
    points = _extract_run_points(reports)[-4:]
    width = 1020
    height = 520
    image, draw = _new_canvas(width, height)
    title_font, body_font, small_font = _load_fonts()
    draw.text((32, 24), "CRIS-SME Run Comparison", fill="#12314b", font=title_font)
    draw.text(
        (32, 58),
        "Overall risk comparison across the most recent archived assessment runs",
        fill="#547089",
        font=small_font,
    )

    baseline_y = 390
    left = 140
    gap = 185
    bar_width = 120
    max_score = max((score for _, score in points), default=10.0)
    max_score = max(max_score, 10.0)
    draw.line((110, baseline_y, 880, baseline_y), fill="#7f97ad", width=3)

    if not points:
        draw.text((130, 210), "No archived runs available yet.", fill="#17324d", font=body_font)
    for index, (label, score) in enumerate(points):
        x = left + index * gap
        bar_height = int((score / max_score) * 230)
        y = baseline_y - bar_height
        draw.rounded_rectangle((x, y, x + bar_width, baseline_y), radius=12, fill="#1f6aa5")
        draw.text((x + 20, y - 30), f"{score:.2f}", fill="#17324d", font=body_font)
        draw.text((x, baseline_y + 18), label, fill="#17324d", font=small_font)

    image.save(output_path)


def _new_canvas(width: int, height: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    """Create a CRIS-SME styled PNG canvas."""
    image = Image.new("RGB", (width, height), "#f6fbff")
    draw = ImageDraw.Draw(image)
    return image, draw


def _load_fonts() -> tuple[ImageFont.ImageFont, ImageFont.ImageFont, ImageFont.ImageFont]:
    """Load fonts for PNG chart rendering with graceful fallback."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]
    body_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]

    title_font = _load_font_from_candidates(candidates, 30)
    body_font = _load_font_from_candidates(body_candidates, 20)
    small_font = _load_font_from_candidates(body_candidates, 16)
    return title_font, body_font, small_font


def _load_font_from_candidates(candidates: list[str], size: int) -> ImageFont.ImageFont:
    """Load the first available TrueType font, or fall back to default."""
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    return ImageFont.load_default()
