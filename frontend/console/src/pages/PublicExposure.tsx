import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { FileDown, RefreshCw } from "lucide-react";
import { artifactUrl, getPublicExposureHistory, getPublicExposureReport, runPublicExposureAssessment } from "../api/client";
import { EmptyState, Spinner } from "../components/ui";
import { DataTable, KpiCard, Panel, SeverityTag, type DataTableColumn } from "../components/clarion";
import { normalizeSeverity } from "../components/severity";

interface ExposureFindingRow {
  id: string;
  title: string;
  severity: string;
  target: string;
  evidence_summary?: string;
  recommendation?: string;
}

const SELECTION_KEY = "cris-public-exposure-run";

function savedSelection(): string {
  try {
    return localStorage.getItem(SELECTION_KEY) ?? "";
  } catch {
    return "";
  }
}

function scanDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Date unavailable" : date.toLocaleString();
}

export function PublicExposure() {
  const queryClient = useQueryClient();
  const [selectedRunId, setSelectedRunId] = useState(savedSelection);
  const [targets, setTargets] = useState("");
  const [authorizationConfirmed, setAuthorizationConfirmed] = useState(false);
  const [scanCommonPorts, setScanCommonPorts] = useState(false);

  const history = useQuery({ queryKey: ["public-exposure-history"], queryFn: getPublicExposureHistory, retry: false });
  const entries = history.data?.assessments ?? [];
  const activeRunId = selectedRunId || entries[0]?.run_id || "";
  const savedReport = useQuery({
    queryKey: ["public-exposure-report", activeRunId],
    queryFn: () => getPublicExposureReport(activeRunId),
    enabled: !!activeRunId,
    retry: false,
  });

  function selectRun(runId: string) {
    setSelectedRunId(runId);
    try {
      localStorage.setItem(SELECTION_KEY, runId);
    } catch {
      // The selected run remains usable when browser storage is unavailable.
    }
  }

  const assessment = useMutation({
    mutationFn: runPublicExposureAssessment,
    onSuccess: (report) => {
      if (report.run_id) {
        queryClient.setQueryData(["public-exposure-report", report.run_id], report);
        selectRun(report.run_id);
      }
      void queryClient.invalidateQueries({ queryKey: ["public-exposure-history"] });
    },
  });

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    assessment.mutate({
      targets,
      authorization_confirmed: authorizationConfirmed,
      scan_common_ports: scanCommonPorts,
    });
  };

  const report = activeRunId ? (savedReport.isError ? undefined : savedReport.data) : assessment.data;
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
    <div className="flex min-w-0 flex-col gap-[18px] p-4 sm:p-[24px_26px_28px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="m-0 text-[15px] font-bold text-text-strong">Public Exposure</h1>
          <p className="m-0 mt-1 text-[11.5px] font-medium text-text-muted">
            Internet-facing attack surface · DNS/HTTP/HTTPS/TLS evidence only
          </p>
        </div>
      </div>

      <div className="flex min-w-0 flex-col gap-2 border-b border-border-strong pb-4">
        <label htmlFor="public-scan-selection" className="text-[12.5px] font-semibold text-text-body">Saved assessment</label>
        <div className="flex min-w-0 items-center gap-2">
          <select
            id="public-scan-selection"
            aria-label="Public exposure assessment"
            className="h-9 min-w-0 flex-1 rounded-md border border-border-strong bg-surface-card px-3 text-[12.5px] text-text-body"
            value={activeRunId}
            onChange={(event) => selectRun(event.target.value)}
            disabled={!entries.length && !activeRunId}
          >
            {!activeRunId && <option value="">{history.isPending ? "Loading saved scans…" : "No saved scans"}</option>}
            {activeRunId && !entries.some((entry) => entry.run_id === activeRunId) &&
              <option value={activeRunId}>{activeRunId}</option>}
            {entries.map((entry) => <option key={entry.run_id} value={entry.run_id}>
              {scanDate(entry.generated_at)} · {entry.targets.join(", ") || "Targets unavailable"} · {entry.run_id}
            </option>)}
          </select>
          <button type="button" title="Refresh saved scans" aria-label="Refresh saved scans"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-border-strong text-text-body"
            disabled={history.isFetching} onClick={() => { void history.refetch(); }}>
            <RefreshCw className={`h-4 w-4 ${history.isFetching ? "animate-spin" : ""}`} />
          </button>
        </div>
        {history.isError && <p role="alert" className="m-0 text-[12px] text-sev-critical-text">Saved scans are unavailable. {(history.error as Error).message}</p>}
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
              className="h-4 w-4 shrink-0 rounded border-border-strong text-primary"
            />
            I confirm I am authorized to run external reconnaissance against these targets.
          </label>

          <label className="flex items-center gap-2 text-[12.5px] font-medium text-text-body">
            <input
              type="checkbox"
              checked={scanCommonPorts}
              onChange={(event) => setScanCommonPorts(event.target.checked)}
              className="h-4 w-4 shrink-0 rounded border-border-strong text-primary"
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

      {activeRunId && savedReport.isPending && <p className="text-[12.5px] text-text-muted">Loading selected assessment…</p>}
      {savedReport.isError && <p role="alert" className="text-[12.5px] text-sev-critical-text">
        Selected assessment is unavailable. {(savedReport.error as Error).message}
      </p>}
      {report && (
        <>
          <div className="flex min-w-0 flex-wrap items-center justify-between gap-3 border-b border-border-strong pb-3">
            <div className="min-w-0 text-[12px] text-text-muted">
              <time dateTime={report.generated_at}>{scanDate(report.generated_at)}</time>
              {report.run_id && <div className="break-all font-mono text-text-body">{report.run_id}</div>}
            </div>
            <div className="flex flex-wrap gap-3 text-[12px] font-semibold text-text-body">
              {Object.entries(report.artifacts ?? {}).filter(([kind]) => kind === "json" || kind === "markdown").map(([kind, path]) =>
                <a key={kind} href={artifactUrl(path)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5">
                  <FileDown className="h-4 w-4" />{kind === "json" ? "JSON" : "Markdown"}
                </a>)}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3.5 lg:grid-cols-4">
            <KpiCard label="Targets scanned" value={report.summary?.target_count ?? 0} accent={undefined} />
            <KpiCard
              label="Findings"
              value={report.summary?.finding_count ?? 0}
              accent={(report.summary?.high_finding_count ?? 0) > 0 ? "critical" : undefined}
            />
            <KpiCard label="HTTPS available" value={report.summary?.https_available_count ?? "—"} />
            <KpiCard label="Resolved targets" value={report.summary?.resolved_target_count ?? "—"} />
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
