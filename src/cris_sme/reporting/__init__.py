# Reporting components for JSON, HTML, and summary outputs.
from .appendix_export import write_appendix_tables
from .figure_export import write_history_figures, write_report_figures
from .history import archive_report_snapshot, build_history_comparison, load_report_history
from .html_report import build_html_report, write_html_report
from .json_report import build_json_report, write_json_report
from .narrator import (
    NarratorSettings,
    PlainLanguageNarrative,
    maybe_generate_plain_language_narrative,
    write_plain_language_reports,
)
from .summary_report import build_summary_report, write_summary_report

__all__ = [
    "archive_report_snapshot",
    "build_history_comparison",
    "load_report_history",
    "write_appendix_tables",
    "write_history_figures",
    "write_report_figures",
    "build_html_report",
    "build_json_report",
    "NarratorSettings",
    "PlainLanguageNarrative",
    "build_summary_report",
    "maybe_generate_plain_language_narrative",
    "write_html_report",
    "write_json_report",
    "write_plain_language_reports",
    "write_summary_report",
]
