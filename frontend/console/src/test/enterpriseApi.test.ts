import { afterEach, describe, expect, it, vi } from "vitest";
import { EnterpriseApi, type Artifact } from "../enterprise/api";
import { identitySettings } from "../enterprise/config";
import { baseReport } from "./fixtures/report";
import { webcrypto } from "node:crypto";

afterEach(() => vi.unstubAllGlobals());
const env = { VITE_OIDC_AUTHORITY: "https://identity.example", VITE_OIDC_CLIENT_ID: "console" };

describe("enterprise identity configuration", () => {
  it("uses code flow and a same-origin callback with no offline grant", () => {
    expect(identitySettings(env, "https://cris.example", "/console/")).toMatchObject({
      response_type: "code", scope: "openid cris.api", redirect_uri: "https://cris.example/console/auth/callback", automaticSilentRenew: false,
    });
  });
  it.each([
    { VITE_OIDC_AUTHORITY: "http://identity.example" }, { VITE_OIDC_AUTHORITY: "https://name:password@identity.example" },
    { VITE_OIDC_AUTHORITY: "https://identity.example?redirect=foo" }, { VITE_OIDC_CLIENT_ID: "" },
    { VITE_API_BASE_URL: "https://elsewhere.example" }, { VITE_DEMO_MODE: "true" },
    { VITE_OIDC_SCOPE: "openid" }, { VITE_OIDC_SCOPE: "openid cris.api offline_access" },
  ])("rejects unsafe settings %j", overrides => {
    expect(() => identitySettings({ ...env, ...overrides }, "https://cris.example", "/")).toThrow();
  });
});

describe("enterprise transport", () => {
  it("sends bearer credentials only to versioned same-origin endpoints", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ tenants: [] })));
    vi.stubGlobal("fetch", fetch);
    const api = new EnterpriseApi(() => "token", vi.fn());
    await api.tenants();
    expect(fetch).toHaveBeenCalledWith("/api/v1/tenants", expect.objectContaining({ credentials: "omit", cache: "no-store", redirect: "error", headers: { Authorization: "Bearer token" } }));
    await expect(api.request("https://attacker.example/api/v1/tenants")).rejects.toThrow("Enterprise endpoint required");
    await expect(api.request("/api/assessment-history")).rejects.toThrow("Enterprise endpoint required");
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it("rejects absent tokens without network access", async () => {
    const fetch = vi.fn(); const invalid = vi.fn(); vi.stubGlobal("fetch", fetch);
    await expect(new EnterpriseApi(() => undefined, invalid).tenants()).rejects.toMatchObject({ status: 401 });
    expect(fetch).not.toHaveBeenCalled(); expect(invalid).toHaveBeenCalledOnce();
  });
  it.each([401, 403, 404, 503])("fails closed for %i without exposing server content", async status => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("secret backend trace", { status })));
    const invalid = vi.fn();
    await expect(new EnterpriseApi(() => "token", invalid).tenants()).rejects.toMatchObject({ status });
    expect(invalid).toHaveBeenCalledTimes(status === 401 ? 1 : 0);
  });
  it("fences responses that finish parsing after organization switch", async () => {
    let finish!: (value: unknown) => void;
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: () => new Promise(resolve => { finish = resolve; }) }));
    const api = new EnterpriseApi(() => "token", vi.fn());
    const pending = api.tenants();
    await vi.waitFor(() => expect(finish).toBeDefined());
    api.cancel(); finish({ tenants: [{ name: "old organization" }] });
    await expect(pending).rejects.toMatchObject({ name: "AbortError" });
  });
  it("retains caller idempotency key on scan requests", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response("{}")); vi.stubGlobal("fetch", fetch);
    await new EnterpriseApi(() => "token", vi.fn()).request("/api/v1/tenants/org/assessments", { connection_id: "connection", authorization_confirmed: true }, "POST", "stable-key");
    expect(fetch.mock.calls[0][1].headers["Idempotency-Key"]).toBe("stable-key");
  });
});

describe("authorized artifacts", () => {
  async function fixture(value: unknown) {
    vi.stubGlobal("crypto", webcrypto);
    const text = JSON.stringify(value);
    const bytes = new TextEncoder().encode(text);
    const sha256 = Array.from(new Uint8Array(await webcrypto.subtle.digest("SHA-256", bytes)), b => b.toString(16).padStart(2, "0")).join("");
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => Promise.resolve(new Response(text))));
    const artifact: Artifact = { id: "opaque-id", name: "cris_sme_report.json", sha256, size: bytes.byteLength };
    return { api: new EnterpriseApi(() => "token", vi.fn()), artifact };
  }
  it("checks digest and strips embedded filesystem download paths", async () => {
    const { api, artifact } = await fixture({ ...baseReport, report_artifacts: { json_report: "/some/other/tenant/report.json" } });
    const report = await api.report("organization", artifact);
    expect(report.report_artifacts).toBeUndefined();
    expect(fetch).toHaveBeenCalledWith("/api/v1/tenants/organization/artifacts/opaque-id", expect.anything());
  });
  it("rejects size mismatch", async () => {
    const { api, artifact } = await fixture(baseReport);
    await expect(api.artifact("org", { ...artifact, size: 0 })).rejects.toThrow("size check failed");
  });
  it("rejects digest mismatch", async () => {
    const { api, artifact } = await fixture(baseReport);
    await expect(api.artifact("org", { ...artifact, sha256: "0".repeat(64) })).rejects.toThrow("integrity check failed");
  });
  it("rejects non-report JSON", async () => {
    const { api, artifact } = await fixture({ other: "payload" });
    await expect(api.report("org", artifact)).rejects.toThrow("Unsupported report structure");
  });
});
