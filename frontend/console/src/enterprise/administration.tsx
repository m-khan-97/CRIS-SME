import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { UserMinus } from "lucide-react";
import type { Audit, Member, Role, Tenant } from "./api";
import { useSession } from "./Auth";

export function Members({ tenant }: { tenant: Tenant }) {
  const { api } = useSession();
  const cache = useQueryClient();
  const admin = ["owner", "admin"].includes(tenant.role);
  const [subject, setSubject] = useState("");
  const [role, setRole] = useState<Role>("analyst");
  const [remove, setRemove] = useState("");
  const members = useQuery({ queryKey: ["enterprise", tenant.id, "members"], queryFn: () => api.request<{ members: Member[] }>(api.path(tenant.id, "members")), enabled: admin, retry: false });
  const update = useMutation({ mutationFn: (deleting: boolean) => api.request(api.path(tenant.id, `members/${encodeURIComponent(deleting ? remove : subject)}`), deleting ? undefined : { role }, deleting ? "DELETE" : "PUT"),
    onSuccess: () => { setSubject(""); setRemove(""); void cache.invalidateQueries({ queryKey: ["enterprise"] }); } });
  return <main className="space-y-5 p-4 md:p-6"><h1 className="text-xl font-semibold text-text-strong">Organization members</h1>
    {!admin && <p>Your role does not permit member administration.</p>}
    {(members.error || update.error) && <p role="alert">{(members.error || update.error)?.message}</p>}
    {admin && <form className="flex max-w-3xl flex-wrap items-end gap-3" onSubmit={e => { e.preventDefault(); update.mutate(false); }}>
      <label className="min-w-0 flex-1">Identity subject<input required value={subject} maxLength={255} onChange={e => setSubject(e.target.value)} /></label>
      <label>Role<select value={role} onChange={e => setRole(e.target.value as Role)}>{(["owner", "admin", "operator", "analyst", "auditor"] as Role[]).filter(r => r !== "owner" || tenant.role === "owner").map(r => <option key={r}>{r}</option>)}</select></label>
      <button className="enterprise-primary" disabled={update.isPending}>Save member</button>
    </form>}
    <ul className="divide-y divide-border-card">{!members.isError && members.data?.members.map(m => <li key={`${m.issuer}:${m.subject}`} className="flex min-w-0 items-center gap-3 py-3">
      <div className="min-w-0 flex-1"><strong className="break-all">{m.subject}</strong><div className="break-all text-xs">{m.issuer}</div></div><span>{m.role}</span>
      {admin && (tenant.role === "owner" || m.role !== "owner") && <button title="Remove member" aria-label={`Remove ${m.subject}`} onClick={() => setRemove(m.subject)}><UserMinus size={18} /></button>}
    </li>)}</ul>
    {remove && <div role="alertdialog" aria-label="Confirm member removal" className="space-y-3 border border-border-card p-4"><p className="break-all">Remove {remove}? Access will be revoked and their active scans cancelled.</p><button disabled={update.isPending} onClick={() => update.mutate(true)}>Confirm removal</button> <button onClick={() => setRemove("")}>Keep member</button></div>}
  </main>;
}

export function AuditLog({ tenant }: { tenant: Tenant }) {
  const { api } = useSession();
  const allowed = ["owner", "admin", "auditor"].includes(tenant.role);
  const audit = useQuery({ queryKey: ["enterprise", tenant.id, "audit"], queryFn: () => api.request<{ events: Audit[] }>(api.path(tenant.id, "audit")), enabled: allowed, retry: false });
  return <main className="space-y-5 p-4 md:p-6"><h1 className="text-xl font-semibold text-text-strong">Audit log</h1>
    {!allowed ? <p>Your role does not permit audit access.</p> : audit.error ? <p role="alert">{audit.error.message}</p> : <>
      <button disabled={audit.isFetching} onClick={() => { void audit.refetch(); }}>Refresh audit</button>
      <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Resource</th></tr></thead><tbody>
        {audit.data?.events.map(e => <tr key={e.id}><td>{new Date(e.created_at * 1000).toLocaleString()}</td><td>{e.subject}</td><td>{e.action}</td><td className="font-mono text-xs">{e.resource_id}</td></tr>)}
      </tbody></table></div>
    </>}
  </main>;
}
