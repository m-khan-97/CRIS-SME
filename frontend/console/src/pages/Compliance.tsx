import { ShieldCheck } from "lucide-react";
import { useAssessmentReport } from "../context/AssessmentContext";
import { Card, EmptyState, ProgressRing, Spinner } from "../components/ui";

export function Compliance() {
  const { data: report, isLoading, error } = useAssessmentReport();

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-8 text-text-muted">
        <Spinner /> Loading compliance mappings…
      </div>
    );
  }

  if (error) {
    return <div className="p-8"><EmptyState message={`Failed to load report: ${(error as Error).message}`} /></div>;
  }

  const compliance = report?.compliance;
  if (!report || !compliance) {
    return <div className="p-8"><EmptyState message="No compliance mapping data found in the latest report." /></div>;
  }

  const findingsByFramework = Object.entries(compliance.findings_by_framework).sort(
    (a, b) => b[1] - a[1]
  );
  const controlReferenceCounts = Object.entries(compliance.control_reference_counts).sort(
    (a, b) => b[1] - a[1]
  );

  return (
    <div className="flex flex-col gap-6 p-[24px_26px_28px]">
      <div>
        <h1 className="text-2xl font-semibold text-text-strong">Compliance</h1>
        <p className="mt-1 text-sm text-text-muted">
          {compliance.frameworks_covered.length} frameworks covered ·{" "}
          {compliance.mapped_findings.length} mapped findings
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {compliance.frameworks_covered.map((framework) => {
          const count = compliance.findings_by_framework[framework] ?? 0;
          const share = compliance.mapped_findings.length
            ? (count / compliance.mapped_findings.length) * 100
            : 0;
          return (
            <Card key={framework}>
              <div className="flex items-center gap-4">
                <ProgressRing value={share} label={`${count}`} />
                <div>
                  <div className="flex items-center gap-2 font-medium text-text-strong">
                    <ShieldCheck className="h-4 w-4 text-sev-low-text" />
                    {framework}
                  </div>
                  <div className="mt-1 text-xs text-text-muted">
                    {count} mapped finding{count === 1 ? "" : "s"}
                  </div>
                </div>
              </div>
            </Card>
          );
        })}
      </div>

      <Card title="Findings by framework">
        <div className="flex flex-col gap-3">
          {findingsByFramework.map(([framework, count]) => (
            <div key={framework} className="flex items-center gap-3">
              <div className="w-48 shrink-0 text-sm text-text-body">{framework}</div>
              <div className="flex-1 overflow-hidden rounded-full bg-surface-rail">
                <div
                  className="h-2 rounded-full bg-sev-low"
                  style={{
                    width: `${Math.min(
                      100,
                      (count / (findingsByFramework[0]?.[1] || 1)) * 100
                    )}%`,
                  }}
                />
              </div>
              <div className="w-10 shrink-0 text-right text-sm text-text-muted">
                {count}
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Control reference counts">
        <div className="grid grid-cols-2 gap-2 text-sm md:grid-cols-4">
          {controlReferenceCounts.map(([control, count]) => (
            <div
              key={control}
              className="flex items-center justify-between rounded-md border border-border-card px-3 py-2"
            >
              <span className="font-mono text-xs text-text-body">{control}</span>
              <span className="text-text-muted">{count}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
