export const enterpriseMode = import.meta.env.VITE_ENTERPRISE_MODE === "true";

export function identitySettings(env: Record<string, string | undefined>, origin: string, base: string) {
  const authority = env.VITE_OIDC_AUTHORITY ?? "";
  const client_id = env.VITE_OIDC_CLIENT_ID ?? "";
  const url = new URL(authority);
  if (url.protocol !== "https:" || url.username || url.password || url.search || url.hash || !client_id.trim()) {
    throw new Error("Configure an HTTPS identity authority and public client ID.");
  }
  if (env.VITE_DEMO_MODE === "true" || env.VITE_API_BASE_URL) {
    throw new Error("Enterprise mode requires a same-origin API and cannot use demo mode.");
  }
  const scope = env.VITE_OIDC_SCOPE || "openid cris.api";
  const scopes = scope.split(/\s+/);
  if (!scopes.includes("openid") || !scopes.some(s => s === "cris.api" || s.endsWith("/cris.api")) || scopes.includes("offline_access")) {
    throw new Error("Configure openid and cris.api scopes without offline_access.");
  }
  return { authority, client_id, scope, redirect_uri: new URL(`${base}auth/callback`, origin).href,
    response_type: "code", automaticSilentRenew: false, monitorSession: false,
    loadUserInfo: false, revokeTokensOnSignout: false, requestTimeoutInSeconds: 15,
    resource: env.VITE_OIDC_RESOURCE || undefined,
    extraQueryParams: env.VITE_OIDC_AUDIENCE ? { audience: env.VITE_OIDC_AUDIENCE } : undefined };
}
