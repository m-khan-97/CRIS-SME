#!/usr/bin/env python3
"""Build AI-assisted pilot review artifacts for Cyber Essentials evaluation."""
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
from cris_sme.engine.ce_review_draft import (
    DEFAULT_DRAFT_REVIEWER,
    build_ce_review_decision_draft,
    write_ce_review_decision_draft,
)
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
            "Create a clearly labelled AI-assisted pilot CE review ledger from "
            "an existing CRIS-SME CE self-assessment pack."
        )
    )
    parser.add_argument(
        "--answer-pack",
        default="outputs/reports/cris_sme_ce_self_assessment.json",
        help="Path to cris_sme_ce_self_assessment.json.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/reports/ce_review_draft",
        help="Directory for draft review artifacts.",
    )
    parser.add_argument(
        "--reviewer",
        default=DEFAULT_DRAFT_REVIEWER,
        help="Reviewer label to write into the draft ledger.",
    )
    args = parser.parse_args()

    answer_pack_path = Path(args.answer_pack)
    output_dir = Path(args.output_dir)
    answer_pack = json.loads(answer_pack_path.read_text(encoding="utf-8"))

    draft = build_ce_review_decision_draft(
        answer_pack,
        reviewer=str(args.reviewer),
    )
    console = build_ce_review_console(
        answer_pack,
        review_decisions=draft["review_decisions"],
        generated_at=str(draft["generated_at"]),
    )
    metrics = build_ce_evaluation_metrics(answer_pack, console)

    draft_path = write_ce_review_decision_draft(
        draft,
        output_dir / "cris_sme_ce_review_decision_draft.json",
    )
    console_path = write_ce_review_console(
        console,
        output_dir / "cris_sme_ce_review_console_reviewed_draft.json",
    )
    console_html_path = write_ce_review_console_html(
        build_ce_review_console_html(console),
        output_dir / "cris_sme_ce_review_console_reviewed_draft.html",
    )
    metrics_path = write_ce_evaluation_metrics(
        metrics,
        output_dir / "cris_sme_ce_evaluation_metrics_reviewed_draft.json",
    )
    metrics_html_path = write_ce_evaluation_metrics_html(
        build_ce_evaluation_metrics_html(metrics),
        output_dir / "cris_sme_ce_evaluation_metrics_reviewed_draft.html",
    )
    paper_exports = write_ce_paper_exports(metrics, output_dir)

    print("AI-assisted pilot CE review artifacts written:")
    for path in [
        draft_path,
        console_path,
        console_html_path,
        metrics_path,
        metrics_html_path,
        *paper_exports.values(),
    ]:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
