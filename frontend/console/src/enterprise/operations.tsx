import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { useSession } from "./Auth";
import type { Tenant } from "./api";

interface OperationsSnapshot {
  quota_bytes: number; max_artifacts: number; registered_bytes: number; registered_artifacts: number;
  reserved_bytes: number; reserved_artifacts: number; pending_assessments: number;
  assessments: Record<string, number>; oldest_queue_age_seconds: number; expired_leases: number;
  rate_limits: Record<string, { used: number; limit: number; remaining: number; reset_after_seconds: number }>;
}

function bytes(value: number) {
  return value >= 1024 ** 3 ? `${(value / 1024 ** 3).toFixed(2)} GiB` : `${(value / 1024 ** 2).toFixed(2)} MiB`;
}

export function Operations({ tenant }: { tenant: Tenant }) {
  const { api } = useSession();
  const allowed = ["owner", "admin", "auditor"].includes(tenant.role);
  const query = useQuery({ queryKey: ["enterprise", tenant.id, "operations"], enabled: allowed,
    queryFn: () => api.request<OperationsSnapshot>(api.path(tenant.id, "operations")), refetchInterval: 10_000, retry: false });
  const data = query.isError ? undefined : query.data;
  return <main className="space-y-6 p-4 md:p-6">
    <div className="flex items-center justify-between gap-3"><h1 className="text-xl font-semibold">Operations</h1>
      {allowed && <button title="Refresh operations" aria-label="Refresh operations" disabled={query.isFetching} onClick={() => { void query.refetch(); }}><RefreshCw size={18} /></button>}
    </div>
    {!allowed ? <p role="alert">Your role does not permit this view.</p> : query.error ? <p role="alert">{query.error.message}</p> : !data ? <p role="status">Loading operations...</p> : <>
      <section aria-label="Storage capacity" className="space-y-3 border-b border-border-card pb-5">
        <h2 className="text-base font-semibold">Storage capacity</h2>
        <meter aria-label="Committed and reserved report storage" className="h-4 w-full max-w-3xl" min={0} max={data.quota_bytes}
          low={data.quota_bytes * 0.6} high={data.quota_bytes * 0.85} optimum={0} value={Math.min(data.quota_bytes, data.registered_bytes + data.reserved_bytes)} />
        <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm md:grid-cols-4">
          <div><dt>Committed reports</dt><dd className="font-semibold">{bytes(data.registered_bytes)}</dd></div>
          <div><dt>Reserved</dt><dd className="font-semibold">{bytes(data.reserved_bytes)}</dd></div>
          <div><dt>Quota</dt><dd className="font-semibold">{bytes(data.quota_bytes)}</dd></div>
          <div><dt>Artifacts</dt><dd className="font-semibold">{data.registered_artifacts.toLocaleString()} / {data.max_artifacts.toLocaleString()}</dd></div>
        </dl>
      </section>
      <section aria-label="Assessment health" className="space-y-3 border-b border-border-card pb-5">
        <h2 className="text-base font-semibold">Assessment health</h2>
        <dl className="grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
          {Object.entries(data.assessments).map(([status, count]) => <div key={status}><dt className="capitalize">{status}</dt><dd className="font-semibold">{count.toLocaleString()}</dd></div>)}
          <div><dt>Oldest queued</dt><dd className="font-semibold">{data.oldest_queue_age_seconds}s</dd></div>
          <div><dt>Expired leases</dt><dd className="font-semibold">{data.expired_leases}</dd></div>
        </dl>
      </section>
      <section aria-label="Action budgets" className="space-y-3">
        <h2 className="text-base font-semibold">Action budgets</h2>
        <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr><th>Action</th><th>Used</th><th>Remaining</th><th>Reset</th></tr></thead><tbody>
          {Object.entries(data.rate_limits).map(([action, rate]) => <tr key={action}><td className="py-2 capitalize">{action.replaceAll("_", " ")}</td><td className="whitespace-nowrap tabular-nums">{rate.used} / {rate.limit}</td><td className="whitespace-nowrap tabular-nums">{rate.remaining}</td><td className="whitespace-nowrap tabular-nums">{rate.reset_after_seconds}s</td></tr>)}
        </tbody></table></div>
      </section>
    </>}
  </main>;
}
