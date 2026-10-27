import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { EnterpriseAuth, useSession } from "../enterprise/Auth";

const sdk = vi.hoisted(() => ({ getUser: vi.fn(), removeUser: vi.fn(), signinRedirect: vi.fn(), signinRedirectCallback: vi.fn(),
  expired: new Set<() => void>(), unloaded: new Set<() => void>(), loaded: new Set<(user: unknown) => void>() }));
vi.mock("oidc-client-ts", () => ({
  WebStorageStateStore: class {},
  UserManager: class {
    settings: { redirect_uri: string };
    constructor(settings: { redirect_uri: string }) { this.settings = settings; }
    getUser = sdk.getUser;
    removeUser = sdk.removeUser;
    signinRedirect = sdk.signinRedirect;
    signinRedirectCallback = sdk.signinRedirectCallback;
    events = {
      addAccessTokenExpired: (fn: () => void) => sdk.expired.add(fn), removeAccessTokenExpired: (fn: () => void) => sdk.expired.delete(fn),
      addUserUnloaded: (fn: () => void) => sdk.unloaded.add(fn), removeUserUnloaded: (fn: () => void) => sdk.unloaded.delete(fn),
      addUserLoaded: (fn: (user: unknown) => void) => sdk.loaded.add(fn), removeUserLoaded: (fn: (user: unknown) => void) => sdk.loaded.delete(fn),
    };
  },
}));

function Protected() {
  const { api, signOut } = useSession();
  return <><p>Protected workspace</p><button onClick={signOut}>Local sign out</button>
    <button onClick={() => { void api.tenants().catch(() => undefined); }}>Protected request</button></>;
}
function mount() {
  const cache = new QueryClient(); cache.setQueryData(["private-report"], { value: "private" });
  render(<QueryClientProvider client={cache}><EnterpriseAuth><Protected /></EnterpriseAuth></QueryClientProvider>);
  return cache;
}
beforeEach(() => {
  vi.clearAllMocks();
  vi.stubEnv("VITE_OIDC_AUTHORITY", "https://identity.example"); vi.stubEnv("VITE_OIDC_CLIENT_ID", "console");
  sdk.getUser.mockResolvedValue({ access_token: "token", expired: false });
  sdk.removeUser.mockImplementation(async () => { sdk.unloaded.forEach(fn => fn()); });
  sdk.signinRedirect.mockResolvedValue(undefined);
  window.history.replaceState({}, "", "/");
});
afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); });

describe("enterprise session lifecycle", () => {
  it("keeps missing configuration locked without exposing reports", async () => {
    vi.stubEnv("VITE_OIDC_AUTHORITY", ""); mount();
    await screen.findByText("Enterprise sign-in is not configured. Contact your administrator.");
    expect(screen.queryByText("Protected workspace")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Sign in" })); expect(sdk.signinRedirect).not.toHaveBeenCalled();
  });
  it("loads the authenticated workspace", async () => {
    mount(); await screen.findByText("Protected workspace");
  });
  it("requires sign-in when stored user is expired", async () => {
    sdk.getUser.mockResolvedValue({ access_token: "token", expired: true }); mount();
    fireEvent.click(await screen.findByRole("button", { name: "Sign in" }));
    expect(sdk.signinRedirect).toHaveBeenCalledOnce(); expect(screen.queryByText("Protected workspace")).not.toBeInTheDocument();
  });
  it("clears cached reports and removes the user on sign-out without recursive events", async () => {
    const cache = mount(); await screen.findByText("Protected workspace");
    fireEvent.click(screen.getByRole("button", { name: "Local sign out" }));
    await screen.findByRole("button", { name: "Sign in" });
    expect(cache.getQueryData(["private-report"])).toBeUndefined(); expect(sdk.removeUser).toHaveBeenCalledOnce();
  });
  it("clears reports when the SDK announces token expiry", async () => {
    const cache = mount(); await screen.findByText("Protected workspace");
    act(() => { sdk.expired.forEach(fn => fn()); });
    await screen.findByRole("button", { name: "Sign in" }); expect(cache.getQueryData(["private-report"])).toBeUndefined();
  });
  it("clears cached reports on an API 401", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 401 })));
    const cache = mount(); await screen.findByText("Protected workspace");
    fireEvent.click(screen.getByRole("button", { name: "Protected request" }));
    await screen.findByRole("button", { name: "Sign in" }); expect(cache.getQueryData(["private-report"])).toBeUndefined();
  });
  it("drops old report state when the SDK loads a different identity", async () => {
    const cache = mount(); await screen.findByText("Protected workspace");
    cache.setQueryData(["private-report"], { value: "previous-user" });
    act(() => { sdk.loaded.forEach(fn => fn({ access_token: "another-token", expired: false, profile: { sub: "another-user", iss: "https://identity.example" } })); });
    await waitFor(() => expect(cache.getQueryData(["private-report"])).toBeUndefined());
  });
  it("handles redirect failures without displaying provider details", async () => {
    sdk.getUser.mockResolvedValue(null); sdk.signinRedirect.mockRejectedValue(new Error("Private provider trace")); mount();
    fireEvent.click(await screen.findByRole("button", { name: "Sign in" }));
    await screen.findByText("Sign-in unavailable. Contact your administrator."); expect(screen.queryByText("Private provider trace")).not.toBeInTheDocument();
  });
  it("rejects a failed callback and removes its authorization code from browser history", async () => {
    window.history.replaceState({}, "", "/auth/callback?code=fixture&state=invalid");
    sdk.signinRedirectCallback.mockRejectedValue(new Error("Sensitive callback detail")); mount();
    await screen.findByText("Sign-in could not be completed. Start a new sign-in.");
    await waitFor(() => expect(window.location.search).toBe("")); expect(sdk.removeUser).toHaveBeenCalledOnce();
  });
});
