import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Download, Play, X } from "lucide-react";
import type { Connection, Job, Tenant } from "./api";
import { useSession } from "./Auth";
import { useClock } from "./useClock";

export function Assessments({ tenant, jobs, connections, select }: { tenant: Tenant; jobs: Job[]; connections: Connection[]; select: (id: string) => void }) {
  const { api } = useSession();
  const cache = useQueryClient();
  const [connectionId, setConnection] = useState("");
  const [authorized, setAuthorized] = useState(false);
  const key = useRef<{ connection: string; key: string } | null>(null);
  const operate = ["owner", "admin", "operator"].includes(tenant.role);
  const now = useClock();
  const available = connections.filter(c => c.enabled && c.verified_until * 1000 > now);
  const refresh = () => cache.invalidateQueries({ queryKey: ["enterprise", tenant.id, "jobs"] });
  const submit = useMutation({ mutationFn: () => {
    if (!operate || !authorized || !available.some(c => c.id === connectionId)) throw new Error("Select a verified connection and confirm authorization.");
    if (key.current?.connection !== connectionId) key.current = { connection: connectionId, key: crypto.randomUUID() };
    return api.request<Job>(api.path(tenant.id, "assessments"), { connection_id: connectionId, authorization_confirmed: true }, "POST", key.current.key);
  }, onSuccess: () => { key.current = null; setAuthorized(false); void refresh(); } });
  const cancel = useMutation({ mutationFn: (id: string) => api.request(api.path(tenant.id, `assessments/${encodeURIComponent(id)}/cancel`), {}, "POST"), onSuccess: () => { void refresh(); } });
  return <main className="space-y-6 p-4 md:p-6"><h1 className="text-xl font-semibold text-text-strong">Assessments</h1>
    {operate && <form className="flex max-w-3xl flex-wrap items-end gap-3" onSubmit={e => { e.preventDefault(); submit.mutate(); }}>
      <label className="min-w-0 flex-1">Cloud connection<select required aria-label="Scan connection" value={connectionId} onChange={e => { setConnection(e.target.value); key.current = null; }}>
        <option value="">Select verified connection</option>{available.map(c => <option key={c.id} value={c.id}>{c.name} - {c.provider.toUpperCase()} - {c.scope_id}</option>)}
      </select></label>
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={authorized} onChange={e => setAuthorized(e.target.checked)} />I am authorized to assess this cloud scope</label>
      <button className="enterprise-primary" disabled={!authorized || !available.some(c => c.id === connectionId) || submit.isPending}><Play size={16} />Start assessment</button>
    </form>}
    {(submit.error || cancel.error) && <p role="alert">{(submit.error || cancel.error)?.message}</p>}
    {submit.isSuccess && <p role="status">Assessment queued.</p>}
    {!jobs.length ? <p>No assessments available.</p> : <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr><th>Requested</th><th>Connection</th><th>Assessment ID</th><th>Status</th><th>Actions</th></tr></thead><tbody>
      {jobs.map(j => <tr key={j.id}><td>{new Date(j.requested_at * 1000).toLocaleString()}</td><td>{connections.find(c => c.id === j.connection_id)?.name ?? j.connection_id}</td><td className="font-mono text-xs">{j.id}</td><td>{j.status}{j.error_code && <span className="block">{j.error_code}</span>}</td><td>
        {j.status === "completed" && <button onClick={() => select(j.id)}>Select report</button>}
        {operate && ["queued", "running"].includes(j.status) && <button title="Cancel assessment" aria-label={`Cancel ${j.id}`} disabled={cancel.isPending} onClick={() => cancel.mutate(j.id)}><X size={16} /></button>}
      </td></tr>)}
    </tbody></table></div>}
  </main>;
}

export function Reports({ tenant, job }: { tenant: Tenant; job?: Job }) {
  const { api } = useSession();
  const download = useMutation({ mutationFn: async (id: string) => {
    const artifact = job?.artifacts?.find(a => a.id === id);
    if (!artifact || job?.status !== "completed") throw new Error("Select a completed assessment.");
    const bytes = await api.artifact(tenant.id, artifact);
    const url = URL.createObjectURL(new Blob([bytes], { type: "application/octet-stream" }));
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = artifact.name.replace(/[^A-Za-z0-9_.-]/g, "_"); anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } });
  return <main className="space-y-4 p-4 md:p-6"><h1 className="text-xl font-semibold text-text-strong">Reports</h1>
    {download.error && <p role="alert">{download.error.message}</p>}
    {!job || job.status !== "completed" ? <p>No completed assessment selected.</p> : <>
      <p className="break-words text-sm">{tenant.name} / {job.id}</p>
      <ul className="divide-y divide-border-card">{job.artifacts?.map(a => <li className="flex min-w-0 flex-wrap items-center gap-3 py-3" key={a.id}>
        <div className="min-w-0 flex-1"><strong className="break-all">{a.name}</strong><div className="break-all font-mono text-xs">SHA-256 {a.sha256}</div><div className="text-sm">{a.size.toLocaleString()} bytes</div></div>
        <button aria-label={`Download ${a.name}`} title={`Download ${a.name}`} disabled={download.isPending} onClick={() => download.mutate(a.id)}><Download size={18} /></button>
      </li>)}</ul>
    </>}
  </main>;
}
