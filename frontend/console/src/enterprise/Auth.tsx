/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { UserManager, WebStorageStateStore, type User } from "oidc-client-ts";
import { useQueryClient } from "@tanstack/react-query";
import { identitySettings } from "./config";
import { EnterpriseApi } from "./api";

interface Session { api: EnterpriseApi; signOut: () => void }
const SessionContext = createContext<Session | null>(null);
export function useSession() {
  const value = useContext(SessionContext);
  if (!value) throw new Error("Enterprise session required");
  return value;
}

let manager: UserManager | undefined;
let callback: Promise<User> | undefined;
function identity() {
  manager ??= new UserManager({ ...identitySettings(import.meta.env, window.location.origin, import.meta.env.BASE_URL),
    userStore: new WebStorageStateStore({ store: window.sessionStorage }),
    stateStore: new WebStorageStateStore({ store: window.sessionStorage }) });
  return manager;
}

export function EnterpriseAuth({ children }: { children: ReactNode }) {
  const cache = useQueryClient();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [session] = useState(() => {
    let current: User | null = null;
    let removing = false;
    const signOut = () => {
      current = null;
      api.cancel();
      cache.clear();
      setUser(null);
      if (!removing && manager) {
        removing = true;
        void manager.removeUser().finally(() => { removing = false; });
      }
    };
    const api = new EnterpriseApi(() => current && !current.expired ? current.access_token : undefined, signOut);
    return { api, signOut, accept: (value: User | null) => {
      if (current && (current.access_token !== value?.access_token || current.profile?.sub !== value?.profile?.sub || current.profile?.iss !== value?.profile?.iss)) {
        api.cancel(); cache.clear();
      }
      current = value; setUser(value);
    } };
  });
  useEffect(() => {
    let alive = true;
    let idp: UserManager;
    const expired = () => session.signOut();
    const changed = (value: User) => { if (alive) session.accept(value.expired ? null : value); };
    try {
      idp = identity();
      idp.events.addAccessTokenExpired(expired);
      idp.events.addUserUnloaded(expired);
      idp.events.addUserLoaded(changed);
      const isCallback = window.location.pathname === new URL(idp.settings.redirect_uri).pathname;
      const load = isCallback ? (callback ??= idp.signinRedirectCallback()) : idp.getUser();
      void load.then(value => {
        if (!alive) return;
        if (isCallback) window.history.replaceState({}, "", import.meta.env.BASE_URL);
        session.accept(value && !value.expired ? value : null);
        setLoading(false);
      }).catch(() => {
        if (!alive) return;
        if (isCallback) window.history.replaceState({}, "", import.meta.env.BASE_URL);
        setError("Sign-in could not be completed. Start a new sign-in.");
        session.signOut(); setLoading(false);
      });
    } catch {
      void Promise.resolve().then(() => { if (alive) {
        setError("Enterprise sign-in is not configured. Contact your administrator."); setLoading(false);
      } });
    }
    return () => {
      alive = false;
      idp?.events.removeAccessTokenExpired(expired);
      idp?.events.removeUserUnloaded(expired);
      idp?.events.removeUserLoaded(changed);
    };
  }, [session]);
  if (loading) return <main className="p-8" role="status">Checking session...</main>;
  if (!user) return <main className="mx-auto max-w-lg space-y-5 p-8"><h1 className="text-2xl font-semibold">CRIS Enterprise</h1>
    {error && <p role="alert">{error}</p>}
    <button className="enterprise-primary" onClick={() => { setError(""); try { void identity().signinRedirect().catch(() => setError("Sign-in unavailable. Contact your administrator.")); } catch { setError("Enterprise sign-in is not configured. Contact your administrator."); } }}>Sign in</button>
  </main>;
  return <SessionContext.Provider key={`${user.profile?.iss ?? ""}:${user.profile?.sub ?? ""}`} value={session}>{children}</SessionContext.Provider>;
}
