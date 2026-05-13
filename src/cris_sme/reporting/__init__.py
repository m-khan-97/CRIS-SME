# Reporting components for JSON, HTML, and summary outputs.
from .benchmark_export import write_benchmark_outputs
from .assurance_portal import build_assurance_portal_html, write_assurance_portal_html
from .ce_questionnaire_report import (
    build_ce_self_assessment_html,
    write_ce_self_assessment_html,
)
from .ce_evaluation_report import (
    build_ce_evaluation_metrics_html,
    write_ce_evaluation_metrics_html,
)
from .ce_paper_export import (
    build_ce_chart_data,
    build_ce_paper_tables_markdown,
    write_ce_paper_exports,
)
from .ce_review_console import (
    build_ce_review_console_html,
    write_ce_review_console_html,
)
from .dashboard import (
    build_dashboard_html,
    build_dashboard_payload,
    write_dashboard_html,
    write_dashboard_payload,
)
from .executive_pack import build_executive_pack, write_executive_pack
from .evidence_room import build_evidence_room_html, write_evidence_room_html
from .action_plan_export import write_action_plan_outputs
from .appendix_export import write_appendix_tables
from .figure_export import write_history_figures, write_report_figures
from .history import (
    archive_report_snapshot,
    build_evaluation_mode_summary,
    build_history_comparison,
    build_risk_drift_analysis,
    load_report_history,
)
from .html_report import build_html_report, write_html_report
from .insurance_pack import (
    build_cyber_insurance_evidence_pack,
    write_cyber_insurance_evidence_pack,
)
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
    "build_assurance_portal_html",
    "build_ce_self_assessment_html",
    "build_ce_evaluation_metrics_html",
    "build_ce_chart_data",
    "build_ce_paper_tables_markdown",
    "build_ce_review_console_html",
    "build_evaluation_mode_summary",
    "build_history_comparison",
    "build_risk_drift_analysis",
    "build_dashboard_html",
    "build_dashboard_payload",
    "build_executive_pack",
    "build_evidence_room_html",
    "write_benchmark_outputs",
    "write_action_plan_outputs",
    "write_assurance_portal_html",
    "write_ce_self_assessment_html",
    "write_ce_evaluation_metrics_html",
    "write_ce_paper_exports",
    "write_ce_review_console_html",
    "load_report_history",
    "write_appendix_tables",
    "write_dashboard_html",
    "write_dashboard_payload",
    "write_history_figures",
    "write_report_figures",
    "write_executive_pack",
    "write_evidence_room_html",
    "build_html_report",
    "build_cyber_insurance_evidence_pack",
    "build_json_report",
    "NarratorSettings",
    "PlainLanguageNarrative",
    "build_summary_report",
    "maybe_generate_plain_language_narrative",
    "write_html_report",
    "write_cyber_insurance_evidence_pack",
    "write_json_report",
    "write_plain_language_reports",
    "write_summary_report",
]
