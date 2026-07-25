import { CheckCircle2, GitCompare, ShieldCheck, XCircle } from "lucide-react";
import { useAssessmentReport } from "../context/AssessmentContext";
import { Card, EmptyState, Spinner, StatCard } from "../components/ui";

const STATUS_COLORS: Record<string, string> = {
  agreement: "bg-status-good-bg text-status-good-text border-status-good-border",
  cris_only: "bg-violet-500/20 text-primary-on-tint border-violet-500/40",
  native_only: "bg-sev-medium-bg text-sev-medium-text border-sev-medium-border",
  divergent: "bg-sev-critical-bg text-sev-critical-text border-sev-critical-border",
};

function ActiveFlag({ value }: { value: boolean }) {
  return value ? (
    <CheckCircle2 className="h-4 w-4 text-status-good-text" />
  ) : (
    <XCircle className="h-4 w-4 text-text-faint" />
  );
}

export function NativeValidation() {
  const { data: report, isLoading, error } = useAssessmentReport();

  const data = (report ?? {}) as Record<string, any>;
  const validation = data.native_validation as Record<string, any> | undefined;
  const comparisons: Record<string, any>[] = validation?.control_comparisons ?? [];

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-8 text-text-muted">
        <Spinner /> Loading native validation data…
      </div>
    );
  }

  if (error) {
    return <div className="p-8"><EmptyState message={`Failed to load report: ${(error as Error).message}`} /></div>;
  }

  if (!report || !validation) {
    return (
      <div className="p-8"><EmptyState message="No native validation comparison found in the latest report. This view requires a cloud provider's native security recommendations (e.g. Microsoft Defender for Cloud)." /></div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-[24px_26px_28px]">
      <div>
        <h1 className="text-2xl font-semibold text-text-strong">Native Validation</h1>
        <p className="mt-1 text-sm text-text-muted">
          How CRIS-SME's findings compare with {validation.framework}'s native recommendations.
          This is a calibration and divergence view, not a claim of equivalence.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-5">
        <StatCard
          label="Controls mapped"
          value={validation.controls_mapped ?? 0}
          icon={GitCompare}
          accent="text-primary bg-primary-tint"
        />
        <StatCard
          label="Agreement"
          value={validation.agreement_count ?? 0}
          icon={ShieldCheck}
          accent="text-status-good-text bg-status-good-bg"
        />
        <StatCard
          label="CRIS-SME only"
          value={validation.cris_only_count ?? 0}
          accent="text-sev-low-text bg-sev-low-bg"
        />
        <StatCard
          label="Native only"
          value={validation.native_only_count ?? 0}
          accent="text-sev-medium-text bg-sev-medium-bg"
        />
        <StatCard
          label="Native unhealthy recommendations"
          value={validation.native_unhealthy_recommendation_count ?? 0}
          accent="text-text-body bg-surface-rail"
        />
      </div>

      {validation.coverage_note && (
        <Card>
          <p className="text-sm text-text-body">{validation.coverage_note}</p>
        </Card>
      )}

      <Card title={`Control comparisons (${comparisons.length})`}>
        <div className="overflow-hidden rounded-lg border border-border-card">
          <table className="w-full text-left text-sm">
            <thead className="bg-surface-subtle text-xs uppercase tracking-wide text-text-muted">
              <tr>
                <th className="px-4 py-2">Control</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2 text-center">CRIS active</th>
                <th className="px-4 py-2 text-right">CRIS score</th>
                <th className="px-4 py-2 text-center">Native active</th>
                <th className="px-4 py-2 text-right">Native recs</th>
                <th className="px-4 py-2">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-row">
              {comparisons.map((entry) => {
                const classes =
                  STATUS_COLORS[entry.comparison_status] ??
                  "bg-surface-rail text-text-body border-border-strong";
                return (
                  <tr key={entry.control_id}>
                    <td className="px-4 py-2 font-mono text-xs text-text-muted">
                      {entry.control_id}
                    </td>
                    <td className="px-4 py-2">
                      <span className={`rounded-full border px-2 py-0.5 text-xs capitalize ${classes}`}>
                        {String(entry.comparison_status).replaceAll("_", " ")}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-center">
                      <ActiveFlag value={!!entry.cris_active} />
                    </td>
                    <td className="px-4 py-2 text-right text-text-body">{entry.cris_score}</td>
                    <td className="px-4 py-2 text-center">
                      <ActiveFlag value={!!entry.native_active} />
                    </td>
                    <td className="px-4 py-2 text-right text-text-muted">
                      {entry.native_recommendation_count ?? 0}
                    </td>
                    <td className="px-4 py-2 text-xs text-text-muted">{entry.notes}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
