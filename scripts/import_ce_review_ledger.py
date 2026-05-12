#!/usr/bin/env python3
"""Import a completed Cyber Essentials review ledger and rebuild metrics."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cris_sme.engine.ce_evaluation import (
    build_ce_evaluation_metrics,
    write_ce_evaluation_metrics,
)
from cris_sme.engine.ce_review import (
    build_ce_review_console,
    write_ce_review_console,
)
from cris_sme.engine.ce_review_import import load_ce_review_decisions
from cris_sme.reporting.ce_evaluation_report import (
    build_ce_evaluation_metrics_html,
    write_ce_evaluation_metrics_html,
)
from cris_sme.reporting.ce_paper_export import write_ce_paper_exports
from cris_sme.reporting.ce_review_console import (
    build_ce_review_console_html,
    write_ce_review_console_html,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Import a human-reviewed Cyber Essentials ledger and rebuild the "
            "review console, metrics, and paper tables."
        )
    )
    parser.add_argument(
        "--answer-pack",
        default="outputs/reports/cris_sme_ce_self_assessment.json",
        help="Path to cris_sme_ce_self_assessment.json.",
    )
    parser.add_argument(
        "--ledger",
        required=True,
        help="Path to a completed CSV or JSON review ledger.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/reports/ce_review_import",
        help="Directory for imported review artifacts.",
    )
    parser.add_argument(
        "--generated-at",
        default=None,
        help="Optional ISO timestamp for generated console artifacts.",
    )
    args = parser.parse_args()

    answer_pack_path = Path(args.answer_pack)
    output_dir = Path(args.output_dir)
    answer_pack = json.loads(answer_pack_path.read_text(encoding="utf-8"))
    decisions = load_ce_review_decisions(args.ledger, answer_pack=answer_pack)
    console = build_ce_review_console(
        answer_pack,
        review_decisions=decisions,
        generated_at=args.generated_at,
    )
    metrics = build_ce_evaluation_metrics(answer_pack, console)

    console_json_path = write_ce_review_console(
        console,
        output_dir / "cris_sme_ce_review_console_imported.json",
    )
    console_html_path = write_ce_review_console_html(
        build_ce_review_console_html(console),
        output_dir / "cris_sme_ce_review_console_imported.html",
    )
    metrics_json_path = write_ce_evaluation_metrics(
        metrics,
        output_dir / "cris_sme_ce_evaluation_metrics_imported.json",
    )
    metrics_html_path = write_ce_evaluation_metrics_html(
        build_ce_evaluation_metrics_html(metrics),
        output_dir / "cris_sme_ce_evaluation_metrics_imported.html",
    )
    paper_exports = write_ce_paper_exports(metrics, output_dir)

    print("Imported CE review artifacts written:")
    for path in [
        console_json_path,
        console_html_path,
        metrics_json_path,
        metrics_html_path,
        *paper_exports.values(),
    ]:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
