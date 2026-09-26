import { useMemo } from "react";
import { useAssessmentReport } from "../context/AssessmentContext";
import { EmptyState, Spinner } from "../components/ui";
import {
  KpiCard,
  Meter,
  Panel,
  ScoreRing,
} from "../components/clarion";
import { normalizeSeverity } from "../components/severity";
import type { PrioritizedRisk } from "../api/types";

const RISK_BAND_TONE: Record<string, { bg: string; border: string; dot: string; text: string }> = {
  low: { bg: "bg-status-good-bg", border: "border-status-good-border", dot: "bg-status-good", text: "text-status-good-text" },
  moderate: { bg: "bg-sev-medium-bg", border: "border-sev-medium-border", dot: "bg-sev-medium", text: "text-sev-medium-text" },
  medium: { bg: "bg-sev-medium-bg", border: "border-sev-medium-border", dot: "bg-sev-medium", text: "text-sev-medium-text" },
  elevated: { bg: "bg-sev-high-bg", border: "border-sev-high-border", dot: "bg-sev-high", text: "text-sev-high-text" },
  high: { bg: "bg-sev-high-bg", border: "border-sev-high-border", dot: "bg-sev-high", text: "text-sev-high-text" },
  critical: { bg: "bg-sev-critical-bg", border: "border-sev-critical-border", dot: "bg-sev-critical", text: "text-sev-critical-text" },
};

const DIRECTION_NARRATIVE: Record<string, string> = {
  improving: "Cloud risk is trending down",
  rapidly_improving: "Cloud risk is trending down",
  stable: "Cloud risk is holding steady",
  worsening: "Cloud risk is trending up",
  rapidly_worsening: "Cloud risk is trending up sharply",
};

const CATEGORY_SHORT_LABEL: Record<string, string> = {
  "Monitoring/Logging": "Monitoring",
  "Compute/Workloads": "Compute",
  "Cost/Governance Hygiene": "Governance",
  "Healthcare IoT": "IoT",
};

function pillarMeterColor(score: number): string {
  if (score >= 85) return "var(--color-status-good)";
  if (score >= 60) return "var(--color-primary)";
  return "var(--color-sev-medium)";
}

function formatRelativeTime(isoTimestamp: string | undefined): string | undefined {
  if (!isoTimestamp) return undefined;
  const then = new Date(isoTimestamp).getTime();
  if (Number.isNaN(then)) return undefined;
  const diffMs = Date.now() - then;
  const hours = diffMs / 3_600_000;
  if (hours < 1) return `${Math.max(1, Math.round(diffMs / 60_000))}m ago`;
  if (hours < 48) return `${Math.round(hours)}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function Overview() {
  const { data: report, isLoading, error } = useAssessmentReport();

  const assessmentSummary = report?.assessment_summary;
  const drift = report?.risk_drift_analysis;
  const historyComparison = report?.history_comparison;
  const ceReadiness = report?.cyber_essentials_readiness;
  const runMetadata = report?.run_metadata;
  const trustBadge = report?.report_trust_badge;

  const topRisks = useMemo(() => {
    if (!report) return [] as PrioritizedRisk[];
    return report.prioritized_risks.slice().sort((a, b) => b.score - a.score).slice(0, 5);
  }, [report]);

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-8 text-text-muted">
        <Spinner /> Loading latest assessment report…
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <EmptyState message={`Failed to load report: ${(error as Error).message}`} />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="p-8">
        <EmptyState message="No assessment report found yet. Run a new assessment to generate one." />
      </div>
    );
  }

  const riskBand = String(assessmentSummary?.risk_band ?? "").toLowerCase();
  const bandTone = RISK_BAND_TONE[riskBand] ?? RISK_BAND_TONE.moderate;
  const overallDrift = drift?.overall_risk;
  const direction = overallDrift?.direction as string | undefined;
  const narrative =
    (direction && DIRECTION_NARRATIVE[direction]) ?? "Cloud risk overview";
  const changeTotal = overallDrift?.change_total as number | undefined;
  const findingsDelta = historyComparison?.non_compliant_findings_delta as number | undefined;

  const severityCounts: Record<string, number> = (assessmentSummary?.finding_summary?.severity_counts as
    | Record<string, number>
    | undefined) ?? {};
  const criticalCount = severityCounts.Critical ?? severityCounts.critical ?? 0;
  const assuranceScore = assessmentSummary?.assurance_summary?.assessment_assurance_score as
    | number
    | undefined;
  const evidenceSufficiency = report.assessment_runner?.evidence_sufficiency;
  const domainCount = Object.keys(report.category_scores).length;
  const controlsTotal = runMetadata?.policy_pack?.controls_total as number | undefined;
  const replayVerified = trustBadge?.replay_verified as boolean | undefined;
  const lastRunAgo = formatRelativeTime(runMetadata?.generated_at ?? report.generated_at);
  const shortRunId = runMetadata?.run_id ? String(runMetadata.run_id).replace("run_", "").slice(0, 8) : undefined;

  return (
    <div className="flex flex-col">
      {/* Run status strip */}
      <div className="flex flex-wrap items-center gap-3.5 border-b border-border-card bg-surface-card px-[26px] py-[9px] text-[11.5px] font-medium text-text-muted">
        {lastRunAgo && (
          <span className="flex items-center gap-1.5">
            <span className="h-[7px] w-[7px] rounded-full bg-emerald-500" />
            <span className="font-semibold text-text-body">Last run {lastRunAgo}</span>
          </span>
        )}
        <span className="h-[13px] w-px bg-border-card" />
        <span>
          Collector <b className="text-text-body">{report.collector_mode}</b>
        </span>
        {typeof controlsTotal === "number" && (
          <>
            <span className="h-[13px] w-px bg-border-card" />
            <span>
              {controlsTotal} controls · {domainCount} domains
            </span>
          </>
        )}
        {typeof replayVerified === "boolean" && (
          <>
            <span className="h-[13px] w-px bg-border-card" />
            <span>
              Evidence integrity{" "}
              <b className={replayVerified ? "text-status-good-text" : "text-sev-medium-text"}>
                {replayVerified ? "verified" : "unverified"}
              </b>
            </span>
          </>
        )}
        {shortRunId && (
          <span className="ml-auto font-mono text-[11px] text-text-faint">run_id {shortRunId}</span>
        )}
      </div>

      <div className="flex flex-col gap-[18px] p-[24px_26px_28px]">
      {/* Hero */}
      <div className="grid grid-cols-1 gap-7 rounded-3xl border border-border-card bg-surface-card p-[26px_28px] shadow-card lg:grid-cols-[minmax(0,1fr)_280px]">
        <div className="flex flex-col justify-center">
          <div className="mb-2 text-[11px] font-bold uppercase tracking-[.12em] text-primary">
            Assessment overview
          </div>
          <h2 className="m-0 mb-2.5 text-[26px] font-extrabold tracking-[-.02em] text-text-strong">
            {narrative}
          </h2>
          <p className="m-0 mb-4 max-w-[54ch] text-[13.5px] font-medium leading-[1.6] text-text-body">
            {overallDrift?.direction_note ??
              "This assessment evaluates the connected environment against CRIS-SME's deterministic control set; collection runs and historical trend data will populate this narrative as they accumulate."}
          </p>
          <div className="flex flex-wrap gap-2.5">
            <span
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[12px] font-bold capitalize ${bandTone.bg} ${bandTone.border} ${bandTone.text}`}
            >
              <span className={`h-[7px] w-[7px] rounded-full ${bandTone.dot}`} />
              {riskBand || "unrated"} risk band
            </span>
            {typeof changeTotal === "number" && changeTotal !== 0 && (
              <span
                className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[12px] font-bold ${
                  changeTotal < 0
                    ? "border-status-good-border bg-status-good-bg text-status-good-text"
                    : "border-sev-critical-border bg-sev-critical-bg text-sev-critical-text"
                }`}
              >
                {changeTotal < 0 ? "▼" : "▲"} {Math.abs(changeTotal).toFixed(0)} pts {changeTotal < 0 ? "improved" : "worse"}
              </span>
            )}
          </div>
        </div>
        <div className="flex flex-col items-center justify-center gap-3 border-l border-border-divider pl-2 lg:border-l">
          <ScoreRing value={report.overall_risk_score} />
          <div className="text-center text-[11.5px] font-semibold text-text-muted">
            Lower is better · band thresholds at 25 / 50 / 75
          </div>
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-3.5 lg:grid-cols-4">
        <KpiCard
          label="Open findings"
          value={report.prioritized_risks.length}
          delta={
            typeof findingsDelta === "number"
              ? `${findingsDelta <= 0 ? "▼" : "▲"} ${Math.abs(findingsDelta)} since last run`
              : undefined
          }
          deltaTone={typeof findingsDelta === "number" && findingsDelta <= 0 ? "good" : "warning"}
        />
        <KpiCard
          label="Critical"
          value={criticalCount}
          delta={criticalCount > 0 ? "Gating risk band" : "None open"}
          deltaTone={criticalCount > 0 ? "warning" : "good"}
          accent={criticalCount > 0 ? "critical" : undefined}
        />
        <KpiCard
          label="Evidence sufficient"
          value={
            evidenceSufficiency ? `${Math.round(evidenceSufficiency.sufficient_ratio * 100)}%` : "—"
          }
          delta="Share of findings with sufficient evidence"
          deltaTone="neutral"
        />
        <KpiCard
          label="Assurance score"
          value={typeof assuranceScore === "number" ? Math.round(assuranceScore) : "—"}
          delta={assessmentSummary?.assurance_summary?.assessment_assurance_level ?? undefined}
          deltaTone="good"
        />
      </div>

      {/* Domain posture + top risks */}
      <div className="grid grid-cols-1 gap-[18px] lg:grid-cols-2">
        <Panel title="Domain posture" meta="Risk by category">
          <div className="flex flex-col gap-3">
            {Object.entries(report.category_scores).map(([category, score]) => (
              <div key={category} className="grid grid-cols-[110px_1fr_34px] items-center gap-3">
                <span
                  className="truncate text-[12.5px] font-semibold text-text-body"
                  title={category}
                >
                  {CATEGORY_SHORT_LABEL[category] ?? category}
                </span>
                <Meter value={score} />
                <span className="text-right text-[12.5px] font-bold text-text-strong">
                  {score.toFixed(0)}
                </span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel title="Top risks" meta="Highest severity">
          <div className="flex flex-col gap-2">
            {topRisks.map((risk) => {
              const level = normalizeSeverity(risk.severity);
              const railColor =
                level === "critical" || level === "high"
                  ? `var(--color-sev-${level})`
                  : "transparent";
              return (
                <div
                  key={risk.finding_id}
                  className="grid grid-cols-[auto_1fr_auto] items-center gap-3 rounded-md border border-border-row bg-surface-subtle px-3 py-[11px]"
                  style={{ borderLeft: `3px solid ${railColor}` }}
                >
                  <span className="font-mono text-[11px] font-semibold text-text-muted">
                    {risk.control_id}
                  </span>
                  <span className="min-w-0">
                    <span className="block truncate text-[12.5px] font-semibold text-text-strong">
                      {risk.title}
                    </span>
                    <span className="block truncate text-[11px] font-medium text-text-muted">
                      {risk.resource_scope}
                    </span>
                  </span>
                  <span className="text-[16px] font-extrabold text-text-strong">
                    {risk.score.toFixed(0)}
                  </span>
                </div>
              );
            })}
            {topRisks.length === 0 && (
              <EmptyState message="No prioritized risks in the latest report." />
            )}
          </div>
        </Panel>
      </div>

      {/* CE readiness strip */}
      {(ceReadiness?.pillars?.length ?? 0) > 0 && (
        <Panel title="Cyber Essentials readiness" meta="By control pillar">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
            {(ceReadiness?.pillars ?? []).map((pillar) => (
              <div key={pillar.pillar_id}>
                <div className="mb-2 truncate text-[11.5px] font-semibold text-text-body">
                  {pillar.pillar_name}
                </div>
                <div className="mb-[7px]">
                  <Meter value={pillar.readiness_score} color={pillarMeterColor(pillar.readiness_score)} height={6} />
                </div>
                <div className="text-[17px] font-extrabold text-text-strong">
                  {Math.round(pillar.readiness_score)}
                  <span className="text-[11px] font-semibold text-text-muted">%</span>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      )}

      {report.executive_summary && (
        <Panel title="Executive summary">
          <p className="text-[13px] font-medium leading-[1.6] text-text-body">
            {report.executive_summary}
          </p>
        </Panel>
      )}
      </div>
    </div>
  );
}
