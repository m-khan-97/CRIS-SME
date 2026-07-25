import { Activity, History, TrendingDown, TrendingUp } from "lucide-react";
import { useAssessmentReport } from "../context/AssessmentContext";
import { Card, EmptyState, Spinner, StatCard } from "../components/ui";

const DIRECTION_COLORS: Record<string, string> = {
  improving: "bg-status-good-bg text-status-good-text border-status-good-border",
  stable: "bg-surface-rail text-text-body border-border-strong",
  worsening: "bg-sev-medium-bg text-sev-medium-text border-sev-medium-border",
  rapidly_worsening: "bg-sev-critical-bg text-sev-critical-text border-sev-critical-border",
  rapidly_improving: "bg-status-good-bg text-status-good-text border-status-good-border",
};

function DirectionBadge({ value }: { value: string }) {
  const classes = DIRECTION_COLORS[value] ?? "bg-surface-rail text-text-body border-border-strong";
  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium capitalize ${classes}`}>
      {value.replaceAll("_", " ")}
    </span>
  );
}

function DeltaValue({ value }: { value: number }) {
  const rounded = Math.round(value * 100) / 100;
  if (rounded === 0) {
    return <span className="text-text-muted">0</span>;
  }
  const positive = rounded > 0;
  return (
    <span className={positive ? "text-sev-critical-text" : "text-status-good-text"}>
      {positive ? "+" : ""}
      {rounded}
    </span>
  );
}

export function TrendHistory() {
  const { data: report, isLoading, error } = useAssessmentReport();

  const data = (report ?? {}) as Record<string, any>;
  const drift = data.risk_drift_analysis as Record<string, any> | undefined;
  const history = data.history_comparison as Record<string, any> | undefined;

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-8 text-text-muted">
        <Spinner /> Loading trend and history data…
      </div>
    );
  }

  if (error) {
    return <div className="p-8"><EmptyState message={`Failed to load report: ${(error as Error).message}`} /></div>;
  }

  if (!report || (!drift && !history)) {
    return <div className="p-8"><EmptyState message="No trend or history data found in the latest report." /></div>;
  }

  const overall = drift?.overall_risk;
  const categoryDrift: Record<string, Record<string, any>> = drift?.category_drift ?? {};
  const controlDeltas: Record<string, any>[] = history?.control_score_deltas ?? [];
  const changedControls = controlDeltas.filter((entry) => (entry.delta ?? 0) !== 0);

  return (
    <div className="flex flex-col gap-6 p-[24px_26px_28px]">
      <div>
        <h1 className="text-2xl font-semibold text-text-strong">Trend &amp; History</h1>
        <p className="mt-1 text-sm text-text-muted">
          How CRIS-SME's risk picture has changed across assessment runs.
        </p>
      </div>

      {drift && (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Assessment runs"
              value={drift.run_count ?? 0}
              hint={`Since ${drift.first_run_at ? new Date(drift.first_run_at).toLocaleDateString() : "—"}`}
              icon={History}
              accent="text-primary bg-primary-tint"
            />
            <StatCard
              label="Overall risk score"
              value={overall?.latest_score ?? "—"}
              hint={`Started at ${overall?.first_score ?? "—"}`}
              icon={Activity}
              accent="text-sev-low-text bg-sev-low-bg"
            />
            <StatCard
              label="Change over time"
              value={overall ? <DeltaValue value={overall.change_total ?? 0} /> : "—"}
              hint={`Velocity ${overall?.velocity_per_week ?? 0} pts/week`}
              icon={overall && (overall.change_total ?? 0) > 0 ? TrendingUp : TrendingDown}
              accent="text-sev-medium-text bg-sev-medium-bg"
            />
            <Card>
              <div className="text-xs font-semibold uppercase tracking-wide text-text-muted">
                Direction
              </div>
              <div className="mt-2">
                <DirectionBadge value={overall?.direction ?? "stable"} />
              </div>
              {overall?.direction_note && (
                <p className="mt-2 text-xs text-text-muted">{overall.direction_note}</p>
              )}
            </Card>
          </div>

          <Card title="Category drift">
            <div className="overflow-hidden rounded-lg border border-border-card">
              <table className="w-full text-left text-sm">
                <thead className="bg-surface-subtle text-xs uppercase tracking-wide text-text-muted">
                  <tr>
                    <th className="px-4 py-2">Category</th>
                    <th className="px-4 py-2 text-right">First score</th>
                    <th className="px-4 py-2 text-right">Latest score</th>
                    <th className="px-4 py-2 text-right">Change</th>
                    <th className="px-4 py-2 text-right">Velocity (pts/wk)</th>
                    <th className="px-4 py-2">Direction</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-row">
                  {Object.entries(categoryDrift).map(([category, entry]) => (
                    <tr key={category}>
                      <td className="px-4 py-2 text-text-strong">{category}</td>
                      <td className="px-4 py-2 text-right text-text-muted">{entry.first_score}</td>
                      <td className="px-4 py-2 text-right text-text-body">{entry.latest_score}</td>
                      <td className="px-4 py-2 text-right">
                        <DeltaValue value={entry.change_total ?? 0} />
                      </td>
                      <td className="px-4 py-2 text-right text-text-muted">
                        {entry.velocity_per_week}
                      </td>
                      <td className="px-4 py-2">
                        <DirectionBadge value={entry.direction ?? "stable"} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      {history && (
        <Card title="Versus previous run">
          <div className="mb-3 grid grid-cols-1 gap-3 text-sm text-text-body md:grid-cols-3">
            <div>
              Overall risk delta: <DeltaValue value={history.overall_risk_delta ?? 0} />
            </div>
            <div>
              Non-compliant findings delta:{" "}
              <DeltaValue value={history.non_compliant_findings_delta ?? 0} />
            </div>
            <div className="text-text-muted">
              Previous run: {history.previous_generated_at
                ? new Date(history.previous_generated_at).toLocaleString()
                : "—"}{" "}
              ({history.previous_collector_mode})
            </div>
          </div>

          {changedControls.length === 0 ? (
            <p className="text-xs text-text-muted">
              No control score changes since the previous run.
            </p>
          ) : (
            <div className="overflow-hidden rounded-lg border border-border-card">
              <table className="w-full text-left text-sm">
                <thead className="bg-surface-subtle text-xs uppercase tracking-wide text-text-muted">
                  <tr>
                    <th className="px-4 py-2">Control</th>
                    <th className="px-4 py-2 text-right">Previous</th>
                    <th className="px-4 py-2 text-right">Current</th>
                    <th className="px-4 py-2 text-right">Delta</th>
                    <th className="px-4 py-2">Priority change</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-row">
                  {changedControls.map((entry) => (
                    <tr key={entry.control_id}>
                      <td className="px-4 py-2 text-text-strong">
                        <div className="font-mono text-xs text-text-muted">{entry.control_id}</div>
                        <div>{entry.title}</div>
                      </td>
                      <td className="px-4 py-2 text-right text-text-muted">
                        {entry.previous_score}
                      </td>
                      <td className="px-4 py-2 text-right text-text-body">
                        {entry.current_score}
                      </td>
                      <td className="px-4 py-2 text-right">
                        <DeltaValue value={entry.delta ?? 0} />
                      </td>
                      <td className="px-4 py-2 text-xs text-text-muted">
                        {entry.previous_priority} → {entry.current_priority}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
