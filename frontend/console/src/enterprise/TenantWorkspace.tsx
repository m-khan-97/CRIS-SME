import { lazy, Suspense, useState } from "react";
import { Outlet, Route, Routes } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ScopedAssessmentProvider } from "../context/AssessmentContext";
import type { AssessmentHistoryEntry } from "../api/types";
import type { Tenant } from "./api";
import { useSession } from "./Auth";
import { WorkspaceNav, EnterpriseFallback } from "./navigation";
import { Assessments, Reports } from "./assessments";
import { Connections } from "./connections";
import { Members, AuditLog } from "./administration";

const Findings = lazy(() => import("../pages/Findings").then(m => ({ default: m.Findings })));
const Resources = lazy(() => import("../pages/Resources").then(m => ({ default: m.Resources })));
const AttackPaths = lazy(() => import("../pages/AttackPaths").then(m => ({ default: m.AttackPaths })));
const Compliance = lazy(() => import("../pages/Compliance").then(m => ({ default: m.Compliance })));
const CyberEssentials = lazy(() => import("../pages/CyberEssentials").then(m => ({ default: m.CyberEssentials })));
const HealthcareIot = lazy(() => import("../pages/HealthcareIot").then(m => ({ default: m.HealthcareIot })));
const Evidence = lazy(() => import("../pages/EvidenceProvenance").then(m => ({ default: m.EvidenceProvenance })));
const Overview = lazy(() => import("../pages/Overview").then(m => ({ default: m.Overview })));
const Remediation = lazy(() => import("../pages/Remediation").then(m => ({ default: m.Remediation })));
const Personas = lazy(() => import("../pages/Personas").then(m => ({ default: m.Personas })));
const TrustCenter = lazy(() => import("../pages/TrustCenter").then(m => ({ default: m.TrustCenter })));
const Disclosure = lazy(() => import("../pages/DisclosureRoom").then(m => ({ default: m.DisclosureRoom })));
const Governance = lazy(() => import("../pages/Governance").then(m => ({ default: m.Governance })));
const Trends = lazy(() => import("../pages/TrendHistory").then(m => ({ default: m.TrendHistory })));
const NativeValidation = lazy(() => import("../pages/NativeValidation").then(m => ({ default: m.NativeValidation })));

function ReportScope() { return <main><Outlet /></main>; }

export function TenantWorkspace({ tenant }: { tenant: Tenant }) {
  const { api } = useSession();
  const cache = useQueryClient();
  const [requested, setRequested] = useState(() => sessionStorage.getItem(`cris.enterprise.run.${tenant.id}`) ?? "");
  const jobs = useQuery({ queryKey: ["enterprise", tenant.id, "jobs"], queryFn: () => api.jobs(tenant.id), refetchInterval: 3000, retry: false });
  const connections = useQuery({ queryKey: ["enterprise", tenant.id, "connections"], queryFn: () => api.connections(tenant.id), refetchInterval: 15_000, retry: false });
  const completed = jobs.isError ? [] : jobs.data?.assessments.filter(j => j.status === "completed") ?? [];
  const chosen = requested ? completed.find(j => j.id === requested) : completed[0];
  const job = useQuery({ queryKey: ["enterprise", tenant.id, "job", chosen?.id], queryFn: () => api.job(tenant.id, chosen!.id), enabled: !!chosen, retry: false, refetchInterval: 15_000 });
  const expired = chosen?.report_state === "expired" || job.data?.report_state === "expired";
  const artifact = !expired && !job.isError && job.data?.status === "completed" ? job.data.artifacts?.find(a => a.name === "cris_sme_report.json") : undefined;
  const report = useQuery({ queryKey: ["enterprise", tenant.id, chosen?.id, artifact?.id, artifact?.sha256],
    queryFn: () => api.report(tenant.id, artifact!), enabled: !!artifact, retry: false });
  const error = jobs.error ?? job.error ?? report.error;
  const visibleReport = chosen && artifact && !error ? report.data : undefined;
  const selectedConnection = !connections.isError ? connections.data?.connections.find(c => c.id === chosen?.connection_id) : undefined;
  const coverage = visibleReport?.collector_coverage ?? [];
  const historical = chosen?.historical_import;
  const entries: AssessmentHistoryEntry[] = completed.map(j => ({ report_id: j.id, run_id: j.historical_import?.source_run_id ?? j.id,
    organization_id: tenant.id, organization_name: tenant.name, provider: j.historical_import?.provider ?? connections.data?.connections.find(c => c.id === j.connection_id)?.provider ?? "cloud",
    generated_at: j.historical_import?.generated_at ?? new Date(j.requested_at * 1000).toISOString(), overall_risk_score: j.id === chosen?.id ? visibleReport?.overall_risk_score ?? null : null,
    finding_count: j.id === chosen?.id ? visibleReport?.prioritized_risks.length ?? 0 : 0, collector_mode: j.id === chosen?.id ? visibleReport?.collector_mode ?? "unknown" : "unknown" }));
  const select = async (id: string) => {
    if (id === chosen?.id) return;
    await cache.cancelQueries({ queryKey: ["enterprise", tenant.id] });
    api.cancel();
    setRequested(id);
    sessionStorage.setItem(`cris.enterprise.run.${tenant.id}`, id);
    void cache.invalidateQueries({ queryKey: ["enterprise", tenant.id] });
  };
  const value = { assessments: entries, selectedAssessment: entries.find(e => e.report_id === chosen?.id) ?? null,
    selectedReportId: chosen?.id ?? "", setSelectedReportId: select, historyLoading: jobs.isPending,
    report: visibleReport, reportLoading: jobs.isPending || (!!chosen && (job.isPending || (!!artifact && report.isPending))), reportError: error };
  return <><WorkspaceNav role={tenant.role} />
    <div className="flex flex-wrap items-center gap-3 border-b border-border-card px-4 py-3">
      <strong className="min-w-0 max-w-full break-words">{tenant.name}</strong>
      <label className="flex min-w-0 flex-1 items-center gap-2 text-sm">Assessment
        <select aria-label="Active assessment" className="min-w-0 max-w-xl flex-1" value={chosen?.id ?? ""} onChange={e => select(e.target.value)}>
          {!chosen && <option value="">{requested ? "Selected assessment unavailable" : "No completed assessments"}</option>}
          {entries.map(e => <option key={e.report_id} value={e.report_id}>{completed.find(j => j.id === e.report_id)?.report_state === "expired" ? "[Expired] " : ""}{completed.find(j => j.id === e.report_id)?.origin === "historical_import" ? "[Imported] " : ""}{new Date(e.generated_at).toLocaleString()} - {e.provider.toUpperCase()} - {e.run_id}</option>)}
        </select>
      </label>
    </div>
    {historical && <section aria-label="Historical import" className="space-y-1 border-b border-border-card bg-surface-card px-4 py-3 text-sm">
      <strong>Imported historical assessment · Not rescanned</strong>
      <p className="break-words">Generated {new Date(historical.generated_at).toLocaleString()} · Imported {new Date(historical.imported_at * 1000).toLocaleString()} · Original run: {historical.source_run_id}</p>
      <p className="break-all font-mono text-xs">Source SHA-256: {historical.source_sha256}</p>
      <p className="text-xs text-text-muted">Recorded source: {historical.reported_source_type || "Unspecified"}. Original source classifications are preserved as supplied, not revalidated.</p>
    </section>}
    {chosen && <div aria-label="Assessment scope" className="flex flex-wrap gap-x-5 gap-y-1 border-b border-border-card px-4 py-2 text-xs text-text-muted">
      <span className="min-w-0 break-all">Scope: {selectedConnection ? `${selectedConnection.provider.toUpperCase()} / ${selectedConnection.scope_id}` : "Unavailable"}</span>
      <span>Evidence mode: {visibleReport?.collector_mode ?? "Unavailable"}</span>
      <span>Coverage: {coverage.length ? `${new Set(coverage.flatMap(c => c.observed_domains)).size} observed / ${new Set(coverage.flatMap(c => c.partially_observed_domains)).size} partial / ${new Set(coverage.flatMap(c => c.unavailable_domains)).size} unavailable domains` : "Not reported"}</span>
    </div>}
    {expired && <section aria-label="Expired report" className="space-y-1 border-b border-border-card px-4 py-3 text-sm">
      <strong>Report expired under approved retention</strong>
      <p>Assessment history is preserved. Report contents and downloads are unavailable.</p>
    </section>}
    {error && <p role="alert" className="p-4">{error.message}</p>}
    <ScopedAssessmentProvider value={value}><Suspense fallback={<p className="p-6">Loading view...</p>}>
      <Routes>
        <Route index element={<Assessments tenant={tenant} jobs={jobs.isError ? [] : jobs.data?.assessments ?? []} connections={connections.isError ? [] : connections.data?.connections ?? []} select={select} />} />
        <Route path="connections" element={<Connections tenant={tenant} connections={connections.isError ? [] : connections.data?.connections ?? []} error={connections.error} />} />
        <Route element={<ReportScope key={chosen?.id ?? "empty"} />}>
        <Route path="findings" element={<Findings />} /><Route path="resources" element={<Resources />} />
        <Route path="attack-paths" element={<AttackPaths />} /><Route path="compliance" element={<Compliance />} />
        <Route path="cyber-essentials" element={<CyberEssentials />} /><Route path="iomt" element={<HealthcareIot />} />
        <Route path="evidence" element={<Evidence />} />
        <Route path="overview" element={<Overview />} /><Route path="remediation" element={<Remediation />} />
        <Route path="personas" element={<Personas />} /><Route path="trust" element={<TrustCenter />} />
        <Route path="disclosure" element={<Disclosure />} /><Route path="governance" element={<Governance />} />
        <Route path="trend" element={<Trends />} /><Route path="native-validation" element={<NativeValidation />} />
        </Route>
        <Route path="reports" element={<Reports key={chosen?.id ?? "empty"} tenant={tenant} job={error ? undefined : expired && job.data ? { ...job.data, report_state: "expired", artifacts: [] } : job.data} />} />
        <Route path="members" element={<Members tenant={tenant} />} /><Route path="audit" element={<AuditLog tenant={tenant} />} />
        <Route path="*" element={<EnterpriseFallback />} />
      </Routes>
    </Suspense></ScopedAssessmentProvider>
  </>;
}
