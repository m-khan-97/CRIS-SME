import { useMemo, useState } from "react";
import { GitBranch, Gauge, AlertTriangle, ListChecks } from "lucide-react";
import { useAssessmentReport } from "../context/AssessmentContext";
import { Card, EmptyState, SeverityBadge, Spinner, StatCard } from "../components/ui";

type TabId = "overview" | "review-queue" | "evidence-gaps";

function CountBars({ counts }: { counts: Record<string, number> }) {
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const max = entries[0]?.[1] ?? 1;
  if (entries.length === 0) {
    return <p className="text-xs text-text-muted">No data.</p>;
  }
  return (
    <div className="flex flex-col gap-2">
      {entries.map(([key, count]) => (
        <div key={key} className="flex items-center gap-3">
          <div className="w-40 shrink-0 truncate text-xs text-text-body">{key}</div>
          <div className="flex-1 overflow-hidden rounded-full bg-surface-rail">
            <div
              className="h-2 rounded-full bg-sev-low"
              style={{ width: `${Math.min(100, (count / max) * 100)}%` }}
            />
          </div>
          <div className="w-8 shrink-0 text-right text-xs text-text-muted">{count}</div>
        </div>
      ))}
    </div>
  );
}

export function EvidenceProvenance() {
  const { data: report, isLoading, error } = useAssessmentReport();

  const [tab, setTab] = useState<TabId>("overview");
  const [queuePriority, setQueuePriority] = useState("all");
  const [gapDomain, setGapDomain] = useState("all");

  const data = (report ?? {}) as Record<string, any>;
  const graph = data.decision_provenance_graph as Record<string, any> | undefined;
  const reviewQueue = data.decision_review_queue as Record<string, any> | undefined;
  const drift = data.control_drift_attribution as Record<string, any> | undefined;
  const gapBacklog = data.evidence_gap_backlog as Record<string, any> | undefined;
  const calibration = data.confidence_calibration as Record<string, any> | undefined;
  const coverage: Record<string, any>[] = data.collector_coverage ?? [];
  const contracts = data.provider_evidence_contracts as Record<string, any> | undefined;

  const queueItems: Record<string, any>[] = reviewQueue?.items ?? [];
  const gapItems: Record<string, any>[] = gapBacklog?.items ?? [];

  const gapDomains = useMemo(
    () => [...new Set(gapItems.map((item) => String(item.domain)))].sort(),
    [gapItems]
  );

  const filteredQueue = useMemo(
    () =>
      queueItems.filter((item) =>
        queuePriority === "all" ? true : item.priority === queuePriority
      ),
    [queueItems, queuePriority]
  );
  const filteredGaps = useMemo(
    () => gapItems.filter((item) => (gapDomain === "all" ? true : item.domain === gapDomain)),
    [gapItems, gapDomain]
  );

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-8 text-text-muted">
        <Spinner /> Loading evidence and provenance data…
      </div>
    );
  }

  if (error) {
    return <div className="p-8"><EmptyState message={`Failed to load report: ${(error as Error).message}`} /></div>;
  }

  if (!report) {
    return <div className="p-8"><EmptyState message="No assessment report found yet." /></div>;
  }

  return (
    <div className="flex flex-col gap-6 p-[24px_26px_28px]">
      <div>
        <h1 className="text-2xl font-semibold text-text-strong">Evidence &amp; Provenance</h1>
        <p className="mt-1 text-sm text-text-muted">
          How every decision traces back to evidence, what changed since the last run, and where
          evidence is still missing.
        </p>
      </div>

      <div className="flex gap-2 border-b border-border-card">
        {[
          { id: "overview" as const, label: "Overview", icon: Gauge },
          { id: "review-queue" as const, label: "Decision review queue", icon: ListChecks },
          { id: "evidence-gaps" as const, label: "Evidence gap backlog", icon: AlertTriangle },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`flex items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
              tab === id
                ? "border-violet-500 text-text-strong"
                : "border-transparent text-text-muted hover:text-text-strong"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Provenance nodes"
              value={graph?.node_count ?? 0}
              hint={`${graph?.edge_count ?? 0} edges · ${graph?.path_count ?? 0} decision paths`}
              icon={GitBranch}
              accent="text-primary bg-primary-tint"
            />
            <StatCard
              label="Avg calibrated confidence"
              value={
                calibration ? `${Math.round((calibration.average_calibrated_confidence ?? 0) * 100)}%` : "—"
              }
              hint={`${calibration?.controls_with_calibration ?? 0} controls calibrated`}
              icon={Gauge}
              accent="text-sev-low-text bg-sev-low-bg"
            />
            <StatCard
              label="Control drift"
              value={drift?.primary_attribution ?? "unknown"}
              hint={`Risk delta ${drift?.overall_risk_delta ?? 0}`}
              icon={GitBranch}
              accent="text-sev-medium-text bg-sev-medium-bg"
            />
            <StatCard
              label="Evidence gaps"
              value={gapBacklog?.item_count ?? 0}
              hint={`${gapBacklog?.high_priority_count ?? 0} high priority`}
              icon={AlertTriangle}
              accent="text-sev-critical-text bg-sev-critical-bg"
            />
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Card title="Provenance graph — node types">
              {graph ? <CountBars counts={graph.node_type_counts ?? {}} /> : <p className="text-xs text-text-muted">No provenance graph available.</p>}
            </Card>
            <Card title="Provenance graph — edge types">
              {graph ? <CountBars counts={graph.edge_type_counts ?? {}} /> : <p className="text-xs text-text-muted">No provenance graph available.</p>}
            </Card>
          </div>

          {calibration && (
            <Card title="Confidence calibration">
              <p className="mb-2 text-sm text-text-body">{calibration.method_summary}</p>
              <CountBars counts={calibration.status_counts ?? {}} />
            </Card>
          )}

          {coverage.length > 0 && (
            <Card title="Collector coverage">
              <div className="flex flex-col gap-3">
                {coverage.map((entry, index) => (
                  <div key={index} className="rounded-md border border-border-card p-3 text-sm">
                    <div className="font-medium text-text-strong">
                      {entry.provider} · {entry.collection_mode}
                    </div>
                    <p className="mt-1 text-xs text-text-muted">{entry.evidence_quality_note}</p>
                    <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
                      <div>
                        <div className="text-text-muted">Observed</div>
                        <div className="text-text-body">
                          {(entry.observed_domains ?? []).join(", ") || "—"}
                        </div>
                      </div>
                      <div>
                        <div className="text-text-muted">Partial</div>
                        <div className="text-text-body">
                          {(entry.partially_observed_domains ?? []).join(", ") || "—"}
                        </div>
                      </div>
                      <div>
                        <div className="text-text-muted">Unavailable</div>
                        <div className="text-text-body">
                          {(entry.unavailable_domains ?? []).join(", ") || "—"}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              {contracts && (
                <div className="mt-3 text-xs text-text-muted">
                  Provider evidence contracts: {contracts.contract_count} across{" "}
                  {contracts.provider_count} providers · support status{" "}
                  {Object.entries(contracts.support_status_counts ?? {})
                    .map(([status, count]) => `${status}: ${count}`)
                    .join(", ")}
                </div>
              )}
            </Card>
          )}
        </>
      )}

      {tab === "review-queue" && (
        <>
          {queueItems.length === 0 ? (
            <EmptyState message="No decision review queue items available." />
          ) : (
            <Card title={`Decision review queue (${reviewQueue?.item_count})`}>
              <div className="mb-3 flex flex-wrap gap-2">
                <select
                  className="rounded-md border border-border-strong bg-surface-card px-3 py-2 text-sm text-text-strong"
                  value={queuePriority}
                  onChange={(event) => setQueuePriority(event.target.value)}
                >
                  <option value="all">All priorities</option>
                  {Object.keys(reviewQueue?.priority_counts ?? {}).map((priority) => (
                    <option key={priority} value={priority}>
                      {priority}
                    </option>
                  ))}
                </select>
              </div>
              <div className="overflow-hidden rounded-lg border border-border-card">
                <table className="w-full text-left text-sm">
                  <thead className="bg-surface-subtle text-xs uppercase tracking-wide text-text-muted">
                    <tr>
                      <th className="px-4 py-2">Title</th>
                      <th className="px-4 py-2">Decision type</th>
                      <th className="px-4 py-2">Recommended decision</th>
                      <th className="px-4 py-2">Priority</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-row">
                    {filteredQueue.slice(0, 50).map((item) => (
                      <tr key={item.review_id}>
                        <td className="px-4 py-2 text-text-strong">
                          <div>{item.title}</div>
                          <div className="text-xs text-text-muted">
                            {item.control_id} · {item.provider}
                          </div>
                        </td>
                        <td className="px-4 py-2 text-text-muted">{item.decision_type}</td>
                        <td className="px-4 py-2 text-text-muted">{item.recommended_decision}</td>
                        <td className="px-4 py-2">
                          <SeverityBadge severity={item.priority} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {filteredQueue.length > 50 && (
                <p className="mt-2 text-xs text-text-muted">
                  Showing first 50 of {filteredQueue.length} matching items.
                </p>
              )}
            </Card>
          )}
        </>
      )}

      {tab === "evidence-gaps" && (
        <>
          {gapItems.length === 0 ? (
            <EmptyState message="No evidence gap backlog items available." />
          ) : (
            <Card title={`Evidence gap backlog (${gapBacklog?.item_count})`}>
              <div className="mb-3 flex flex-wrap gap-2">
                <select
                  className="rounded-md border border-border-strong bg-surface-card px-3 py-2 text-sm text-text-strong"
                  value={gapDomain}
                  onChange={(event) => setGapDomain(event.target.value)}
                >
                  <option value="all">All domains</option>
                  {gapDomains.map((domain) => (
                    <option key={domain} value={domain}>
                      {domain}
                    </option>
                  ))}
                </select>
              </div>
              <div className="overflow-hidden rounded-lg border border-border-card">
                <table className="w-full text-left text-sm">
                  <thead className="bg-surface-subtle text-xs uppercase tracking-wide text-text-muted">
                    <tr>
                      <th className="px-4 py-2">Title</th>
                      <th className="px-4 py-2">Evidence gap</th>
                      <th className="px-4 py-2">Recommended action</th>
                      <th className="px-4 py-2">Priority</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-row">
                    {filteredGaps.slice(0, 50).map((item) => (
                      <tr key={item.gap_id}>
                        <td className="px-4 py-2 text-text-strong">
                          <div>{item.title}</div>
                          <div className="text-xs text-text-muted">
                            {item.control_id} · {item.provider} · {item.domain}
                          </div>
                        </td>
                        <td className="px-4 py-2 text-text-muted">{item.evidence_gap}</td>
                        <td className="px-4 py-2 text-text-muted">{item.recommended_action}</td>
                        <td className="px-4 py-2">
                          <SeverityBadge severity={item.priority} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {filteredGaps.length > 50 && (
                <p className="mt-2 text-xs text-text-muted">
                  Showing first 50 of {filteredGaps.length} matching items.
                </p>
              )}
            </Card>
          )}
        </>
      )}
    </div>
  );
}
