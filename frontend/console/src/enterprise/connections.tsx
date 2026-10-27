import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, PlugZap, Unplug } from "lucide-react";
import type { Connection, ConnectionInput, Tenant } from "./api";
import { useSession } from "./Auth";
import { useClock } from "./useClock";

export function Connections({ tenant, connections, error }: { tenant: Tenant; connections: Connection[]; error: Error | null }) {
  const { api } = useSession();
  const cache = useQueryClient();
  const admin = ["owner", "admin"].includes(tenant.role);
  const now = useClock();
  const [provider, setProvider] = useState<"aws" | "azure">("aws");
  const [onboarding, setOnboarding] = useState<{ id: string; value: unknown } | null>(null);
  const [confirm, setConfirm] = useState("");
  const [secretReset, setSecretReset] = useState(0);
  const refresh = () => cache.invalidateQueries({ queryKey: ["enterprise", tenant.id, "connections"] });
  const action = useMutation({ mutationFn: async ({ id, command }: { id: string; command: string }) => {
    const value = await api.request(api.path(tenant.id, `connections/${encodeURIComponent(id)}/${command}`), command === "onboarding" ? undefined : {}, command === "onboarding" ? "GET" : "POST");
    if (command === "onboarding") setOnboarding({ id, value });
    else { setOnboarding(null); setConfirm(""); }
  }, onSuccess: () => { void refresh(); } });
  const [createError, setCreateError] = useState("");
  const [creating, setCreating] = useState(false);
  return <main className="space-y-6 p-4 md:p-6"><h1 className="text-xl font-semibold text-text-strong">Cloud connections</h1>
    {(error || action.error || createError) && <p role="alert">{error?.message ?? action.error?.message ?? createError}</p>}
    {admin && <form className="grid max-w-3xl grid-cols-1 gap-4 sm:grid-cols-2" onSubmit={e => {
      e.preventDefault();
      const data = new FormData(e.currentTarget);
      const body: ConnectionInput = { name: String(data.get("name")), provider, scope_id: String(data.get("scope_id")) };
      if (provider === "aws") body.role_arn = String(data.get("role_arn"));
      else Object.assign(body, { tenant_id: String(data.get("tenant_id")), client_id: String(data.get("client_id")), client_secret: String(data.get("client_secret")) });
      // Use a direct promise rather than mutation variables for credential-bearing input.
      setCreating(true); setCreateError("");
      void api.request<Connection>(api.path(tenant.id, "connections"), body, "POST").then(() => { void refresh(); }).catch((failure: Error) => setCreateError(failure.message)).finally(() => {
        body.client_secret = undefined; setSecretReset(n => n + 1); setCreating(false);
      });
      e.currentTarget.reset();
    }}>
      <label>Provider<select aria-label="Provider" value={provider} onChange={e => { setProvider(e.target.value as "aws" | "azure"); setSecretReset(n => n + 1); }}><option value="aws">AWS</option><option value="azure">Azure</option></select></label>
      <label>Connection name<input name="name" required maxLength={200} /></label>
      <label>{provider === "aws" ? "AWS account ID" : "Subscription ID"}<input name="scope_id" required pattern={provider === "aws" ? "[0-9]{12}" : "[a-fA-F0-9-]{36}"} /></label>
      {provider === "aws" ? <label>Target role ARN<input name="role_arn" required maxLength={600} /></label> : <>
        <label>Azure tenant ID<input name="tenant_id" required /></label><label>Application ID<input name="client_id" required /></label>
        <label>Application secret<input key={secretReset} name="client_secret" type="password" required autoComplete="off" maxLength={4096} /></label>
      </>}
      <div className="sm:col-span-2"><button className="enterprise-primary" disabled={creating}><PlugZap size={16} />Create connection</button></div>
    </form>}
    {!connections.length ? <p>No cloud connections.</p> : <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr><th>Name</th><th>Provider / scope</th><th>Status</th>{admin && <th>Actions</th>}</tr></thead><tbody>
      {connections.map(c => <tr key={c.id}><td>{c.name}</td><td>{c.provider.toUpperCase()}<span className="block font-mono text-xs">{c.scope_id}</span></td>
        <td>{!c.enabled ? "Disconnected" : c.verified_until * 1000 > now ? "Verified" : "Verification required"}</td>
        {admin && <td><div className="flex flex-wrap gap-2">
          <button disabled={!c.enabled || action.isPending} onClick={() => action.mutate({ id: c.id, command: "onboarding" })}>Onboarding</button>
          <button aria-label={`Verify ${c.name}`} title="Verify connection" disabled={!c.enabled || action.isPending} onClick={() => action.mutate({ id: c.id, command: "verify" })}><Check size={16} /></button>
          <button aria-label={`Disconnect ${c.name}`} title="Disconnect connection" disabled={!c.enabled || action.isPending} onClick={() => setConfirm(c.id)}><Unplug size={16} /></button>
        </div></td>}
      </tr>)}
    </tbody></table></div>}
    {confirm && <div role="alertdialog" aria-label="Confirm disconnection" className="space-y-3 border border-border-card p-4"><p>Disconnect {connections.find(c => c.id === confirm)?.name}? Queued and active assessments will be cancelled.</p><button onClick={() => action.mutate({ id: confirm, command: "disconnect" })} disabled={action.isPending}>Confirm disconnect</button> <button onClick={() => setConfirm("")}>Keep connection</button></div>}
    {onboarding && <section className="space-y-3"><h2 className="font-semibold">Connection onboarding</h2><pre className="max-w-full overflow-auto whitespace-pre-wrap break-all border border-border-card p-4 text-xs">{JSON.stringify(onboarding.value, null, 2)}</pre></section>}
  </main>;
}
