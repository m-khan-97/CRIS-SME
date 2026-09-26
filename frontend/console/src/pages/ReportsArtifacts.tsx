import { Download } from "lucide-react";
import { artifactUrl } from "../api/client";
import { useAssessmentReport } from "../context/AssessmentContext";
import { Card, EmptyState, Spinner } from "../components/ui";

interface ArtifactEntry {
  label: string;
  path: string;
}

interface ArtifactGroup {
  title: string;
  entries: ArtifactEntry[];
}

const GROUP_TITLES: Record<string, string> = {
  json_report: "Core report",
  evidence_snapshot: "Core report",
  html_report: "Core report",
  sarif_report: "Core report",
  ocsf_findings: "Core report",
  summary_report: "Core report",
  history_snapshot: "Core report",
  appendix_tables: "Appendix tables",
  cyber_insurance_pack: "Cyber insurance",
  action_plan_30_day: "30-day action plan",
  csv_exports: "CSV exports",
  benchmark_outputs: "Benchmark comparison",
  executive_pack: "Executive pack",
  dashboard: "Dashboard",
  cyber_essentials_self_assessment: "Cyber Essentials",
  cyber_essentials_review_console: "Cyber Essentials",
  cyber_essentials_evaluation_metrics: "Cyber Essentials",
  cyber_essentials_paper_exports: "Cyber Essentials paper exports",
  decision_provenance_graph: "Trust & assurance",
  claim_verification_pack: "Trust & assurance",
  assurance_case: "Trust & assurance",
  claim_bound_narrative: "Trust & assurance",
  assurance_portal: "Trust & assurance",
  selective_disclosure: "Selective disclosure",
  assessment_summary: "Trust & assurance",
  risk_bill_of_materials: "Trust & assurance",
};

const LABELS: Record<string, string> = {
  json_report: "Full JSON report",
  evidence_snapshot: "Evidence snapshot",
  html_report: "HTML technical report",
  sarif_report: "SARIF report",
  ocsf_findings: "OCSF findings",
  summary_report: "Summary (text)",
  history_snapshot: "History snapshot",
  results_appendix_markdown: "Results appendix (Markdown)",
  prioritized_risks_csv: "Prioritized risks (CSV)",
  cyber_insurance_markdown: "Cyber insurance evidence (Markdown)",
  cyber_insurance_json: "Cyber insurance evidence (JSON)",
  action_plan_markdown: "30-day action plan (Markdown)",
  action_plan_json: "30-day action plan (JSON)",
  findings_csv: "Findings (CSV)",
  assets_csv: "Assets (CSV)",
  evidence_csv: "Evidence (CSV)",
  actions_csv: "Actions (CSV)",
  benchmark_observation_json: "Benchmark observation (JSON)",
  benchmark_comparison_markdown: "Benchmark comparison (Markdown)",
  executive_pack_markdown: "Executive pack (Markdown)",
  executive_pack_json: "Executive pack (JSON)",
  dashboard_payload_json: "Dashboard payload (JSON)",
  dashboard_html: "Dashboard (HTML)",
  json: "Console (JSON)",
  html: "Console (HTML)",
  ce_paper_tables_markdown: "CE paper tables (Markdown)",
  ce_paper_tables_csv: "CE paper tables (CSV)",
  ce_observability_summary_csv: "CE observability summary (CSV)",
  ce_gap_taxonomy_csv: "CE gap taxonomy (CSV)",
  ce_section_coverage_csv: "CE section coverage (CSV)",
  ce_chart_data_json: "CE chart data (JSON)",
  decision_provenance_graph: "Decision provenance graph (JSON)",
  claim_verification_pack: "Claim verification pack (JSON)",
  assurance_case: "Assurance case (JSON)",
  claim_bound_narrative_json: "Claim-bound narrative (JSON)",
  claim_bound_narrative_markdown: "Claim-bound narrative (Markdown)",
  assurance_portal: "Assurance portal (HTML)",
  selective_disclosure_json: "Selective disclosure package (JSON)",
  evidence_room_html: "Evidence room (HTML)",
  assessment_summary: "Assessment summary (JSON)",
  risk_bill_of_materials: "Risk Bill of Materials (JSON)",
};

const SKIP_KEYS = new Set(["figures", "history_figures", "plain_language_outputs"]);

const SUB_LABEL_FOR_PARENT: Record<string, Record<string, string>> = {
  cyber_essentials_self_assessment: { json: "CE self-assessment (JSON)", html: "CE self-assessment (HTML)" },
  cyber_essentials_review_console: { json: "CE review console (JSON)", html: "CE review console (HTML)" },
  cyber_essentials_evaluation_metrics: { json: "CE evaluation metrics (JSON)", html: "CE evaluation metrics (HTML)" },
};

function flattenArtifacts(reportArtifacts: Record<string, unknown>): ArtifactGroup[] {
  const groups = new Map<string, ArtifactEntry[]>();

  for (const [key, value] of Object.entries(reportArtifacts)) {
    if (SKIP_KEYS.has(key)) continue;
    const groupTitle = GROUP_TITLES[key] ?? key.replaceAll("_", " ");

    if (typeof value === "string") {
      const entries = groups.get(groupTitle) ?? [];
      entries.push({ label: LABELS[key] ?? key.replaceAll("_", " "), path: value });
      groups.set(groupTitle, entries);
    } else if (value && typeof value === "object") {
      const entries = groups.get(groupTitle) ?? [];
      for (const [subKey, subValue] of Object.entries(value)) {
        if (typeof subValue !== "string") continue;
        const label = SUB_LABEL_FOR_PARENT[key]?.[subKey] ?? LABELS[subKey] ?? subKey.replaceAll("_", " ");
        entries.push({ label, path: subValue });
      }
      if (entries.length > 0) {
        groups.set(groupTitle, entries);
      }
    }
  }

  return [...groups.entries()].map(([title, entries]) => ({ title, entries }));
}

export function ReportsArtifacts() {
  const { data: report, isLoading, error } = useAssessmentReport();

  const reportArtifacts = report?.report_artifacts;

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-8 text-text-muted">
        <Spinner /> Loading report artifacts…
      </div>
    );
  }

  if (error) {
    return <div className="p-8"><EmptyState message={`Failed to load report: ${(error as Error).message}`} /></div>;
  }

  if (!report || !reportArtifacts) {
    return <div className="p-8"><EmptyState message="No report artifacts found for this assessment." /></div>;
  }

  const groups = flattenArtifacts(reportArtifacts);

  return (
    <div className="flex flex-col gap-6 p-[24px_26px_28px]">
      <div>
        <h1 className="text-2xl font-semibold text-text-strong">Reports &amp; Artifacts</h1>
        <p className="mt-1 text-sm text-text-muted">
          Generated evidence, executive reports, and machine-readable exports for the selected
          organization and assessment run.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {groups.map((group) => (
          <Card key={group.title} title={group.title}>
            <div className="flex flex-col gap-2">
              {group.entries.map((entry) => {
                return (
                  <div
                    key={entry.path}
                    className="flex items-center justify-between gap-3 rounded-md border border-border-card px-3 py-2 text-sm"
                  >
                    <div className="min-w-0">
                      <div className="text-text-strong">{entry.label}</div>
                      <div className="truncate text-xs text-text-muted">{entry.path}</div>
                    </div>
                    <a
                      href={artifactUrl(entry.path)}
                      target="_blank"
                      rel="noreferrer"
                      className="flex shrink-0 items-center gap-1 rounded-md border border-border-strong bg-surface-subtle px-2 py-1 text-xs text-text-strong hover:border-violet-500 hover:text-text-strong"
                    >
                      <Download className="h-3 w-3" /> Open
                    </a>
                  </div>
                );
              })}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
