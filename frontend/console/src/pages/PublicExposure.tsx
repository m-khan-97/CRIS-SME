import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { runPublicExposureAssessment } from "../api/client";
import { EmptyState, Spinner } from "../components/ui";
import { DataTable, KpiCard, Panel, SeverityTag, normalizeSeverity, type DataTableColumn } from "../components/clarion";

interface ExposureFindingRow {
  id: string;
  title: string;
  severity: string;
  target: string;
  evidence_summary?: string;
  recommendation?: string;
}

export function PublicExposure() {
  const [targets, setTargets] = useState("");
  const [authorizationConfirmed, setAuthorizationConfirmed] = useState(false);
  const [scanCommonPorts, setScanCommonPorts] = useState(false);

  const assessment = useMutation({
    mutationFn: runPublicExposureAssessment,
  });

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    assessment.mutate({
      targets,
      authorization_confirmed: authorizationConfirmed,
      scan_common_ports: scanCommonPorts,
    });
  };

  const report = assessment.data;
  const findings = (report?.findings ?? []) as ExposureFindingRow[];

  const columns: DataTableColumn<ExposureFindingRow>[] = [
    {
      key: "id",
      header: "ID",
      width: "70px",
      render: (row) => <span className="font-mono text-[11px] font-semibold text-text-muted">{row.id}</span>,
    },
    {
      key: "sev",
      header: "Sev",
      width: "60px",
      render: (row) => <SeverityTag level={normalizeSeverity(row.severity)} />,
    },
    {
      key: "finding",
      header: "Finding",
      render: (row) => (
        <span className="min-w-0">
          <span className="block truncate text-[12.5px] font-semibold text-text-strong">{row.title}</span>
          <span className="block truncate text-[11px] font-medium text-text-muted">
            {row.target} {row.evidence_summary ? `· ${row.evidence_summary}` : ""}
          </span>
        </span>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-[18px] p-[24px_26px_28px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="m-0 text-[15px] font-bold text-text-strong">Public Exposure</h1>
          <p className="m-0 mt-1 text-[11.5px] font-medium text-text-muted">
            Internet-facing attack surface · DNS/HTTP/HTTPS/TLS evidence only
          </p>
        </div>
      </div>

      <Panel title="Targets">
        <form className="flex flex-col gap-4" onSubmit={onSubmit}>
          <label className="flex flex-col gap-1.5 text-[13px] font-semibold text-text-body">
            Targets (one per line, or comma-separated)
            <textarea
              className="min-h-[100px] rounded-md border border-border-strong bg-surface-card px-3 py-2 text-[13px] font-medium text-text-body placeholder:text-text-muted focus:border-primary focus:outline-none"
              value={targets}
              onChange={(event) => setTargets(event.target.value)}
              placeholder="example.com&#10;203.0.113.10"
            />
          </label>

          <label className="flex items-center gap-2 text-[12.5px] font-medium text-text-body">
            <input
              type="checkbox"
              checked={authorizationConfirmed}
              onChange={(event) => setAuthorizationConfirmed(event.target.checked)}
              className="h-4 w-4 rounded border-border-strong text-primary"
            />
            I confirm I am authorized to run external reconnaissance against these targets.
          </label>

          <label className="flex items-center gap-2 text-[12.5px] font-medium text-text-body">
            <input
              type="checkbox"
              checked={scanCommonPorts}
              onChange={(event) => setScanCommonPorts(event.target.checked)}
              className="h-4 w-4 rounded border-border-strong text-primary"
            />
            Also scan common administrative/database ports (21/22/23/25/445/3306/3389/5432/6379/9200/27017)
          </label>

          {assessment.isError && (
            <p className="text-[12.5px] font-medium text-sev-critical-text">
              {(assessment.error as Error).message}
            </p>
          )}

          <button
            type="submit"
            disabled={!authorizationConfirmed || !targets.trim() || assessment.isPending}
            className="flex h-9 w-fit items-center gap-2 rounded-md bg-primary px-4 text-[12.5px] font-bold text-white shadow-primary transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {assessment.isPending ? (
              <>
                <Spinner /> Running…
              </>
            ) : (
              <>
                <RefreshCw className="h-3.5 w-3.5" strokeWidth={1.8} />
                Run assessment
              </>
            )}
          </button>
        </form>
      </Panel>

      {report && (
        <>
          <div className="grid grid-cols-2 gap-3.5 lg:grid-cols-4">
            <KpiCard label="Targets scanned" value={report.summary?.target_count ?? 0} accent={undefined} />
            <KpiCard
              label="Findings"
              value={report.summary?.finding_count ?? 0}
              accent={(report.summary as Record<string, any>)?.high_finding_count > 0 ? "critical" : undefined}
            />
            <KpiCard label="HTTPS available" value={(report.summary as Record<string, any>)?.https_available_count ?? "—"} />
            <KpiCard label="Resolved targets" value={(report.summary as Record<string, any>)?.resolved_target_count ?? "—"} />
          </div>

          <Panel title="Exposure findings" meta={report.message}>
            {findings.length > 0 ? (
              <DataTable columns={columns} rows={findings} />
            ) : (
              <EmptyState message="No exposure findings reported for the supplied targets." />
            )}
          </Panel>
        </>
      )}
    </div>
  );
}
