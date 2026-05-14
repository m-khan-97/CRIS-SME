#!/usr/bin/env python3
"""Generate Cyber Essentials paper SVG figures from CRIS-SME metrics artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape


DEFAULT_METRICS = Path(
    "outputs/reports/azure_controlled_lab/ce_review_final/"
    "cris_sme_ce_evaluation_metrics_imported.json"
)
DEFAULT_REPORT = Path("outputs/reports/azure_controlled_lab/cris_sme_report.json")
DEFAULT_OUT = Path("paper/cyber-essentials/figures")

PALETTE = ["#2563eb", "#0f766e", "#7c3aed", "#d97706", "#475569", "#dc2626"]
ANSWER_COLORS = {
    "No": "#dc2626",
    "Yes": "#0f766e",
    "Cannot determine": "#475569",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", default=str(DEFAULT_METRICS))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    args = parser.parse_args(argv)

    metrics_path = Path(args.metrics)
    report_path = Path(args.report)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))

    paths = [
        _write(
            out_dir / "ce-evidence-class-distribution.svg",
            _bar_chart(
                title="Cyber Essentials Evidence Class Distribution",
                subtitle="106 paraphrased preparation entries; cloud-supported = direct cloud + inferred cloud",
                footer="Figure 1. Evidence-class distribution. Only 28/106 entries are cloud-supported; remaining entries preserve explicit evidence gaps.",
                rows=_ordered_rows(
                    metrics["paper_tables"]["observability_by_evidence_class"],
                    ["direct_cloud", "inferred_cloud", "endpoint_required", "policy_required", "manual_required"],
                ),
                label_key="label",
                value_key="count",
                width=920,
                height=430,
                max_value=40,
                y_ticks=[0, 10, 20, 30, 40],
                colors=PALETTE,
            ),
        ),
        _write(
            out_dir / "ce-proposed-answer-distribution.svg",
            _bar_chart(
                title="Controlled Lab Proposed CE Answers",
                subtitle="Proposed answers are candidate review states, not certification outcomes",
                footer="Figure 2. Proposed answer distribution in the controlled Azure vulnerable lab. Yes means no mapped cloud-control-plane issue observed, not proof of full CE compliance.",
                rows=_ordered_rows(
                    metrics["paper_tables"]["proposed_answers"],
                    ["No", "Yes", "Cannot determine"],
                ),
                label_key="label",
                value_key="count",
                width=920,
                height=360,
                max_value=80,
                y_ticks=[0, 20, 40, 60, 80],
                colors=[ANSWER_COLORS["No"], ANSWER_COLORS["Yes"], ANSWER_COLORS["Cannot determine"]],
            ),
        ),
        _write(
            out_dir / "azure-category-score-comparison.svg",
            _bar_chart(
                title="Controlled Azure Lab Category Scores",
                subtitle=f"Overall CRIS-SME risk score: {report.get('overall_risk_score')}/100",
                footer="Figure 3. Category scores from the controlled Azure vulnerable lab. Network exposure dominates the intentionally weak lab posture.",
                rows=[
                    {"label": label, "score": score}
                    for label, score in report.get("category_scores", {}).items()
                ],
                label_key="label",
                value_key="score",
                width=960,
                height=430,
                max_value=100,
                y_ticks=[0, 25, 50, 75, 100],
                colors=["#2563eb", "#dc2626", "#7c3aed", "#0f766e", "#d97706", "#475569"],
                value_suffix="",
            ),
        ),
        _write(
            out_dir / "ce-workflow.svg",
            _workflow_svg(metrics),
        ),
    ]

    for path in paths:
        print(path)
    return 0


def _ordered_rows(rows: list[dict[str, Any]], order: list[str]) -> list[dict[str, Any]]:
    by_label = {str(row.get("label")): row for row in rows}
    return [by_label[label] for label in order if label in by_label]


def _bar_chart(
    *,
    title: str,
    subtitle: str,
    footer: str,
    rows: list[dict[str, Any]],
    label_key: str,
    value_key: str,
    width: int,
    height: int,
    max_value: float,
    y_ticks: list[float],
    colors: list[str],
    value_suffix: str = "",
) -> str:
    left = 190
    right = width - 60
    top = 112
    bottom = height - 88
    plot_height = bottom - top
    slot_width = (right - left) / max(len(rows), 1)
    bar_width = min(115, slot_width * 0.62)

    parts = [
        _svg_open(width, height, title, _chart_desc(title, rows, label_key, value_key)),
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        _text(40, 48, title, 24, "#172033", weight=700),
        _text(40, 76, subtitle, 14, "#617083"),
        f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#d8e2ec" stroke-width="1"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#d8e2ec" stroke-width="1"/>',
    ]
    for tick in y_ticks:
        y = bottom - (tick / max_value) * plot_height
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="#edf2f7" stroke-width="1"/>')
        parts.append(_text(left - 24, y + 4, _fmt(tick), 13, "#617083", anchor="end"))

    for index, row in enumerate(rows):
        value = float(row.get(value_key, 0))
        label = str(row.get(label_key, ""))
        bar_height = 0 if max_value == 0 else (value / max_value) * plot_height
        x = left + (slot_width * index) + ((slot_width - bar_width) / 2)
        y = bottom - bar_height
        color = colors[index % len(colors)]
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" fill="{color}"/>')
        parts.append(_text(x + bar_width / 2, y - 10, f"{_fmt(value)}{value_suffix}", 15, "#172033", weight=700, anchor="middle"))
        parts.append(_wrapped_label(x + bar_width / 2, bottom + 28, label.replace("_", " "), 13))
    parts.append(_text(40, height - 20, footer, 12, "#617083"))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _workflow_svg(metrics: dict[str, Any]) -> str:
    width = 960
    height = 360
    observability = metrics.get("observability_metrics", {})
    review = metrics.get("review_metrics", {})
    boxes = [
        ("Cloud evidence", "Azure collector + normalized CRIS profile"),
        ("Deterministic controls", "26 controls across 6 cloud risk domains"),
        ("CE answer pack", f"{observability.get('cloud_supported_count', 0)} cloud-supported entries"),
        ("Human review", f"{review.get('agreement_count', 0)}/{review.get('agreement_evaluable_count', 0)} accepted agreements"),
        ("Paper exports", "Tables, figures, ledger, and reproducibility artifacts"),
    ]
    parts = [
        _svg_open(width, height, "Cyber Essentials Evidence Workflow", "Workflow from cloud evidence through deterministic controls, answer pack, human review, and paper exports."),
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        _text(40, 48, "Cyber Essentials Evidence Workflow", 24, "#172033", weight=700),
        _text(40, 76, "Deterministic scoring stays upstream; human review never changes CRIS-SME risk scores", 14, "#617083"),
    ]
    x = 40
    y = 135
    box_w = 156
    gap = 28
    for index, (title, body) in enumerate(boxes):
        parts.append(f'<rect x="{x}" y="{y}" width="{box_w}" height="94" rx="8" fill="#f8fafc" stroke="#d8e2ec"/>')
        parts.append(_text(x + 14, y + 28, title, 14, "#172033", weight=700))
        parts.append(_text(x + 14, y + 54, body, 11, "#617083"))
        if index < len(boxes) - 1:
            ax = x + box_w + 6
            ay = y + 47
            parts.append(f'<line x1="{ax}" y1="{ay}" x2="{ax + gap - 12}" y2="{ay}" stroke="#2563eb" stroke-width="2"/>')
            parts.append(f'<path d="M {ax + gap - 12} {ay - 5} L {ax + gap - 2} {ay} L {ax + gap - 12} {ay + 5} Z" fill="#2563eb"/>')
        x += box_w + gap
    parts.append(_text(40, 320, "Figure 4. Evidence workflow. Review decisions are downstream artifacts and do not mutate deterministic findings or scores.", 12, "#617083"))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _svg_open(width: int, height: int, title: str, desc: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">\n'
        f'  <title id="title">{escape(title)}</title>\n'
        f'  <desc id="desc">{escape(desc)}</desc>'
    )


def _text(
    x: float,
    y: float,
    text: object,
    size: int,
    color: str,
    *,
    weight: int | None = None,
    anchor: str | None = None,
) -> str:
    attrs = [
        f'x="{x:.1f}"',
        f'y="{y:.1f}"',
        'font-family="Inter, Arial, sans-serif"',
        f'font-size="{size}"',
        f'fill="{color}"',
    ]
    if weight is not None:
        attrs.append(f'font-weight="{weight}"')
    if anchor is not None:
        attrs.append(f'text-anchor="{anchor}"')
    return f'<text {" ".join(attrs)}>{escape(str(text))}</text>'


def _wrapped_label(x: float, y: float, label: str, size: int) -> str:
    if len(label) <= 18:
        return _text(x, y, label, size, "#172033", anchor="middle")
    words = label.split()
    first: list[str] = []
    second: list[str] = []
    for word in words:
        target = first if len(" ".join(first + [word])) <= 18 else second
        target.append(word)
    return "\n".join(
        [
            _text(x, y, " ".join(first), size, "#172033", anchor="middle"),
            _text(x, y + 16, " ".join(second), size, "#172033", anchor="middle"),
        ]
    )


def _chart_desc(
    title: str,
    rows: list[dict[str, Any]],
    label_key: str,
    value_key: str,
) -> str:
    values = ", ".join(f"{row.get(label_key)} {row.get(value_key)}" for row in rows)
    return f"{title}: {values}."


def _fmt(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


if __name__ == "__main__":
    raise SystemExit(main())
