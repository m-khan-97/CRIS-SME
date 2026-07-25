import { useMemo, useState } from "react";
import { CheckCircle2, FileClock, History, ShieldOff, Sparkles } from "lucide-react";
import { useAssessmentReport } from "../context/AssessmentContext";
import type { PrioritizedRisk } from "../api/types";
import { Card, EmptyState, SeverityBadge, Spinner, StatCard } from "../components/ui";

const STATUS_COLORS: Record<string, string> = {
  open: "bg-sev-medium-bg text-sev-medium-text border-sev-medium-border",
  resolved: "bg-status-good-bg text-status-good-text border-status-good-border",
  exception: "bg-sev-low-bg text-sev-low-text border-sev-low-border",
};

export function Governance() {
  const { data: report, isLoading, error } = useAssessmentReport();

  const [statusFilter, setStatusFilter] = useState("all");

  const data = (report ?? {}) as Record<string, any>;
  const lifecycleSummary = data.finding_lifecycle_summary as Record<string, any> | undefined;
  const risks: PrioritizedRisk[] = data.prioritized_risks ?? [];

  const lifecycleEntries = useMemo(
    () =>
      risks
        .map((risk) => ({ risk, lifecycle: (risk as Record<string, any>).lifecycle }))
        .filter((entry) => !!entry.lifecycle),
    [risks]
  );

  const statuses = useMemo(
    () => [...new Set(lifecycleEntries.map((entry) => String(entry.lifecycle.status)))].sort(),
    [lifecycleEntries]
  );

  const filteredEntries = useMemo(
    () =>
      lifecycleEntries.filter((entry) =>
        statusFilter === "all" ? true : entry.lifecycle.status === statusFilter
      ),
    [lifecycleEntries, statusFilter]
  );

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-8 text-text-muted">
        <Spinner /> Loading exceptions and governance data…
      </div>
    );
  }

  if (error) {
    return <div className="p-8"><EmptyState message={`Failed to load report: ${(error as Error).message}`} /></div>;
  }

  if (!report || !lifecycleSummary) {
    return <div className="p-8"><EmptyState message="No finding lifecycle data found in the latest report." /></div>;
  }

  return (
    <div className="flex flex-col gap-6 p-[24px_26px_28px]">
      <div>
        <h1 className="text-2xl font-semibold text-text-strong">Exceptions &amp; Governance</h1>
        <p className="mt-1 text-sm text-text-muted">
          Finding lifecycle status, recurrence, and the exception register. Lifecycle status and
          exceptions never change a finding's deterministic score or priority.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="New findings (this run)"
          value={lifecycleSummary.new_findings ?? 0}
          icon={Sparkles}
          accent="text-primary bg-primary-tint"
        />
        <StatCard
          label="Existing findings"
          value={lifecycleSummary.existing_findings ?? 0}
          icon={History}
          accent="text-sev-low-text bg-sev-low-bg"
        />
        <StatCard
          label="Exceptions applied"
          value={lifecycleSummary.exception_applied_count ?? 0}
          icon={CheckCircle2}
          accent="text-status-good-text bg-status-good-bg"
        />
        <StatCard
          label="Exception registry size"
          value={lifecycleSummary.exception_registry_count ?? 0}
          icon={ShieldOff}
          accent="text-sev-medium-text bg-sev-medium-bg"
        />
      </div>

      <Card title="Status breakdown">
        <div className="flex flex-wrap gap-3">
          {Object.entries(lifecycleSummary.status_counts ?? {}).map(([status, count]) => {
            const classes = STATUS_COLORS[status] ?? "bg-surface-rail text-text-body border-border-strong";
            return (
              <span
                key={status}
                className={`rounded-full border px-3 py-1 text-sm capitalize ${classes}`}
              >
                {status}: {count as number}
              </span>
            );
          })}
        </div>
        {(lifecycleSummary.exception_applied_count ?? 0) === 0 &&
          (lifecycleSummary.exception_registry_count ?? 0) === 0 && (
            <p className="mt-3 text-xs text-text-muted">
              No exceptions have been registered for this assessment.
            </p>
          )}
      </Card>

      <Card title={`Finding lifecycle (${filteredEntries.length})`}>
        <div className="mb-3 flex flex-wrap gap-2">
          <select
            className="rounded-md border border-border-strong bg-surface-card px-3 py-2 text-sm text-text-strong"
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
          >
            <option value="all">All statuses</option>
            {statuses.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </div>
        <div className="overflow-hidden rounded-lg border border-border-card">
          <table className="w-full text-left text-sm">
            <thead className="bg-surface-subtle text-xs uppercase tracking-wide text-text-muted">
              <tr>
                <th className="px-4 py-2">Finding</th>
                <th className="px-4 py-2">Priority</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2">First seen</th>
                <th className="px-4 py-2">Last seen</th>
                <th className="px-4 py-2 text-right">Recurrence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-row">
              {filteredEntries.slice(0, 50).map(({ risk, lifecycle }) => {
                const classes =
                  STATUS_COLORS[lifecycle.status] ?? "bg-surface-rail text-text-body border-border-strong";
                return (
                  <tr key={risk.finding_id}>
                    <td className="px-4 py-2 text-text-strong">
                      <div className="font-mono text-xs text-text-muted">{risk.control_id}</div>
                      <div>{risk.title}</div>
                      {lifecycle.is_new && (
                        <span className="mt-1 inline-flex items-center gap-1 rounded-full border border-violet-500/40 bg-primary-tint px-2 py-0.5 text-xs text-primary-on-tint">
                          <Sparkles className="h-3 w-3" /> New
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2">
                      <SeverityBadge severity={risk.severity} />
                    </td>
                    <td className="px-4 py-2">
                      <span className={`rounded-full border px-2 py-0.5 text-xs capitalize ${classes}`}>
                        {lifecycle.status}
                      </span>
                      {lifecycle.status_reason && (
                        <div className="mt-1 text-xs text-text-muted">{lifecycle.status_reason}</div>
                      )}
                    </td>
                    <td className="px-4 py-2 text-xs text-text-muted">
                      <FileClock className="mr-1 inline h-3 w-3" />
                      {lifecycle.first_seen ? new Date(lifecycle.first_seen).toLocaleDateString() : "—"}
                    </td>
                    <td className="px-4 py-2 text-xs text-text-muted">
                      {lifecycle.last_seen ? new Date(lifecycle.last_seen).toLocaleDateString() : "—"}
                    </td>
                    <td className="px-4 py-2 text-right text-text-body">
                      {lifecycle.recurrence_count ?? 0}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {filteredEntries.length > 50 && (
          <p className="mt-2 text-xs text-text-muted">
            Showing first 50 of {filteredEntries.length} findings.
          </p>
        )}
      </Card>
    </div>
  );
}
