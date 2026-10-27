import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { LogOut, RefreshCw, ShieldCheck } from "lucide-react";
import { useSession } from "./Auth";
import { TenantWorkspace } from "./TenantWorkspace";

export function Workspace() {
  const { api, signOut } = useSession();
  const cache = useQueryClient();
  const [selected, setSelected] = useState("");
  const tenants = useQuery({ queryKey: ["enterprise", "tenants"], queryFn: () => api.tenants(), retry: false,
    refetchInterval: 15_000, refetchOnWindowFocus: "always" });
  const tenant = tenants.data?.tenants.find(t => t.id === selected) ?? (!selected ? tenants.data?.tenants[0] : undefined);
  return <div className="enterprise-shell min-h-screen bg-surface-app text-text-body">
    <header className="flex flex-wrap items-center gap-4 border-b border-border-card bg-surface-card p-4">
      <div className="flex w-full items-center gap-2 font-bold text-text-strong sm:w-auto"><ShieldCheck size={22} /> CRIS Enterprise</div>
      <label className="flex w-full min-w-0 items-center gap-2 sm:w-auto sm:min-w-[240px] sm:flex-1">Organization
        <select aria-label="Organization" value={tenant?.id ?? ""} onChange={event => {
          api.cancel(); cache.clear(); setSelected(event.target.value);
        }} className="min-w-0 max-w-sm flex-1">
          {!tenant && <option value="">Select organization</option>}
          {tenants.data?.tenants.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
      </label>
      {tenant && <span className="text-sm capitalize">{tenant.role}</span>}
      <button title="Refresh organizations" aria-label="Refresh organizations" onClick={() => { void tenants.refetch(); }}><RefreshCw size={18} /></button>
      <button title="Sign out of this console" aria-label="Sign out" onClick={signOut}><LogOut size={18} /></button>
    </header>
    {tenants.isError ? <div role="alert" className="p-6">Organization access could not be verified. <button onClick={() => { void tenants.refetch(); }}>Retry</button></div>
      : tenants.isPending ? <p role="status" className="p-6">Loading organizations...</p>
      : tenant ? <TenantWorkspace key={`${tenant.id}:${tenant.role}`} tenant={tenant} />
      : <p className="p-6" role="status">No organization access. Contact your administrator.</p>}
  </div>;
}
