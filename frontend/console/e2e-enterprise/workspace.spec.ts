import { createHash } from "node:crypto";
import { expect, test, type Page } from "@playwright/test";
import { baseReport, finding } from "../src/test/fixtures/report";

const orgA = "11111111-1111-4111-8111-111111111111";
const orgB = "22222222-2222-4222-8222-222222222222";
const conn = "33333333-3333-4333-8333-333333333333";
const runA = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const runB = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const artifactA = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";
const artifactB = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee";
const queuedId = "ffffffff-ffff-4fff-8fff-ffffffffffff";

async function setup(page: Page, options: { role?: string; authenticated?: boolean; expiry?: number } = {}) {
  const state = { role: options.role ?? "owner", revoked: false, expired: false, missing: false, queued: false,
    cancel: false, connections: true, verified: true, failSubmission: false, submissions: [] as { key: string; body: unknown }[],
    requests: [] as string[], legacy: [] as string[], created: [] as Record<string, unknown>[], tokenRequests: [] as string[], authorization: "" };
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  if (options.authenticated !== false) await page.addInitScript(({ expiry }) => {
    // Standard oidc-client-ts session fixture, not an application auth bypass.
    if (!sessionStorage.getItem("fixture.initialized")) {
      sessionStorage.setItem("fixture.initialized", "true");
      sessionStorage.setItem("oidc.user:https://identity.invalid:cris-console", JSON.stringify({
        access_token: "fixture-api-token", token_type: "Bearer", scope: "openid cris.api",
        profile: { sub: "fixture-owner", iss: "https://identity.invalid", aud: "cris-console" },
        expires_at: Math.floor(Date.now() / 1000) + expiry,
      }));
    }
  }, { expiry: options.expiry ?? 3600 });
  const texts = new Map([orgA, orgB].map((id, index) => {
    const label = index ? "Beta" : "Alpha";
    return [id, JSON.stringify({ ...baseReport, prioritized_risks: [{ ...finding(label), organization_id: id }],
      report_artifacts: { csv_exports: { findings_csv: "outputs/private/foreign/findings.csv" } } })];
  }));
  const artifacts = (org: string) => {
    const text = texts.get(org)!;
    return [{ id: org === orgA ? artifactA : artifactB, name: "cris_sme_report.json", size: Buffer.byteLength(text), sha256: createHash("sha256").update(text).digest("hex") }];
  };
  const job = (org: string) => ({ id: org === orgA ? runA : runB, tenant_id: org, connection_id: conn,
    requested_at: 1790000000, status: "completed", attempt: 1, error_code: "" });
  await page.context().route("**/*", async route => {
    const request = route.request(); const url = new URL(request.url());
    if (url.origin === "https://identity.invalid") {
      if (url.pathname === "/.well-known/openid-configuration") return route.fulfill({ json: {
        issuer: url.origin, authorization_endpoint: `${url.origin}/authorize`, token_endpoint: `${url.origin}/token`, jwks_uri: `${url.origin}/jwks`,
        response_types_supported: ["code"], subject_types_supported: ["public"], id_token_signing_alg_values_supported: ["RS256"],
      }, headers: { "Access-Control-Allow-Origin": "http://127.0.0.1:4180" } });
      if (url.pathname === "/authorize") {
        state.authorization = url.href;
        const callback = new URL(url.searchParams.get("redirect_uri")!);
        callback.searchParams.set("code", "fixture-code"); callback.searchParams.set("state", url.searchParams.get("state")!);
        return route.fulfill({ status: 302, headers: { Location: callback.href }, body: "" });
      }
      if (url.pathname === "/token") {
        state.tokenRequests.push(request.postData() ?? "");
        const now = Math.floor(Date.now() / 1000);
        const authorization = new URL(state.authorization);
        const idToken = [Buffer.from(JSON.stringify({ alg: "RS256", typ: "JWT" })).toString("base64url"), Buffer.from(JSON.stringify({
          iss: url.origin, aud: "cris-console", sub: "fixture-owner", iat: now, exp: now + 3600,
          nonce: authorization.searchParams.get("nonce") ?? undefined,
        })).toString("base64url"), "fixture"].join(".");
        return route.fulfill({ json: { access_token: "fixture-api-token", id_token: idToken, token_type: "Bearer", expires_in: 3600, scope: "openid cris.api" }, headers: { "Access-Control-Allow-Origin": "http://127.0.0.1:4180" } });
      }
      return route.abort();
    }
    if (url.origin !== "http://127.0.0.1:4180") return route.abort();
    if (!url.pathname.startsWith("/api/") && !url.pathname.startsWith("/outputs/") && url.pathname !== "/health") return route.continue();
    state.requests.push(`${request.method()} ${url.pathname}`);
    if (!url.pathname.startsWith("/api/v1/")) { state.legacy.push(url.pathname); return route.abort(); }
    if (request.headers().authorization !== "Bearer fixture-api-token" || state.expired) return route.fulfill({ status: 401, json: { detail: "Invalid token" } });
    if (url.pathname === "/api/v1/tenants") return route.fulfill({ json: { tenants: state.revoked ? [] : [
      { id: orgA, name: "Alpha Organization", role: state.role }, { id: orgB, name: "Beta Organization", role: "analyst" },
    ] } });
    const parts = url.pathname.split("/"); const org = parts[4]; const section = parts[5]; const id = parts[6]; const action = parts[7];
    if (state.revoked || ![orgA, orgB].includes(org)) return route.fulfill({ status: 404, json: { detail: "Resource not found" } });
    if (section === "connections") {
      if (request.method() === "POST" && !id) { state.created.push(request.postDataJSON()); return route.fulfill({ status: 201, json: { id: conn } }); }
      if (action === "onboarding") return route.fulfill({ json: { external_id: "fixture-external-id", role_arn: "arn:aws:iam::123456789012:role/CRIS", trust_policy: { Version: "2012-10-17" } } });
      if (action === "verify") { state.verified = true; return route.fulfill({ json: { status: "verified" } }); }
      if (action === "disconnect") { state.connections = false; return route.fulfill({ json: { status: "disconnected" } }); }
      return route.fulfill({ json: { connections: [{ id: conn, name: "AWS Production", provider: "aws", scope_id: "123456789012", enabled: state.connections,
        verified_until: state.verified ? Math.floor(Date.now() / 1000) + 3600 : 0 }] } });
    }
    if (section === "assessments") {
      if (request.method() === "POST" && !id) {
        state.submissions.push({ key: request.headers()["idempotency-key"], body: request.postDataJSON() });
        if (state.failSubmission) { state.failSubmission = false; return route.fulfill({ status: 503, json: { detail: "Lost acknowledgement" } }); }
        state.queued = true; return route.fulfill({ status: 202, json: { ...job(org), id: queuedId, status: "queued" } });
      }
      if (action === "cancel") { state.cancel = true; return route.fulfill({ json: { ...job(org), id: queuedId, status: "cancelled" } }); }
      if (id) return state.missing ? route.fulfill({ status: 404, json: { detail: "Resource not found" } }) : route.fulfill({ json: { ...job(org), artifacts: artifacts(org) } });
      return route.fulfill({ json: { assessments: [job(org), ...(state.queued ? [{ ...job(org), id: queuedId, status: state.cancel ? "cancelled" : "queued" }] : [])] } });
    }
    if (section === "artifacts") {
      if (id !== artifacts(org)[0].id) return route.fulfill({ status: 404, json: { detail: "Resource not found" } });
      return route.fulfill({ body: texts.get(org), contentType: "application/octet-stream" });
    }
    if (section === "members") return route.fulfill({ json: { members: [{ issuer: "https://identity.invalid", subject: "fixture-owner", role: state.role }] } });
    if (section === "audit") return route.fulfill({ json: { events: [] } });
    return route.fulfill({ status: 404, json: { detail: "Unconfigured fixture route" } });
  });
  return { state, errors };
}

test("unauthenticated browser makes no protected or legacy requests", async ({ page }) => {
  const { state, errors } = await setup(page, { authenticated: false });
  await page.goto("/findings");
  await expect(page.getByRole("heading", { name: "CRIS Enterprise" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign in", exact: true })).toBeVisible();
  expect(state.requests).toEqual([]); expect(errors).toEqual([]);
});

test("library authorization code PKCE roundtrip returns to scoped workspace", async ({ page }) => {
  const { state, errors } = await setup(page, { authenticated: false });
  await page.goto("/"); await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("combobox", { name: "Organization", exact: true })).toHaveValue(orgA);
  const authorization = new URL(state.authorization);
  expect(authorization.searchParams.get("code_challenge_method")).toBe("S256");
  expect(authorization.searchParams.get("response_type")).toBe("code");
  const token = new URLSearchParams(state.tokenRequests[0]);
  expect(token.get("client_secret")).toBeNull();
  expect(createHash("sha256").update(token.get("code_verifier")!).digest("base64url")).toBe(authorization.searchParams.get("code_challenge"));
  expect(new URL(page.url()).search).toBe(""); expect(state.legacy).toEqual([]); expect(errors).toEqual([]);
});

test("organization switching clears old findings, preserves scoped selection and exports with bearer", async ({ page }) => {
  const { state, errors } = await setup(page);
  await page.goto("/findings");
  await expect(page.getByRole("heading", { name: "Finding Alpha", exact: true })).toBeVisible();
  await page.getByRole("combobox", { name: "Organization", exact: true }).selectOption(orgB);
  await expect(page.getByRole("heading", { name: "Finding Beta", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Finding Alpha", exact: true })).toHaveCount(0);
  await expect(page.getByRole("combobox", { name: "Active assessment" })).toHaveValue(runB);
  await page.getByRole("link", { name: "Reports", exact: true }).click();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download cris_sme_report.json", exact: true }).click();
  expect((await download).suggestedFilename()).toBe("cris_sme_report.json");
  expect(state.requests).toContain(`GET /api/v1/tenants/${orgB}/artifacts/${artifactB}`);
  expect(state.legacy).toEqual([]); expect(errors).toEqual([]);
  await page.screenshot({ path: test.info().outputPath("enterprise-reports-desktop.png"), fullPage: true });
});

test("analysts see reports but no connection or scan administration", async ({ page }) => {
  const { state, errors } = await setup(page, { role: "analyst" });
  await page.goto("/"); await expect(page.getByRole("heading", { name: "Assessments", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Start assessment" })).toHaveCount(0);
  await page.getByRole("link", { name: "Cloud connections", exact: true }).click();
  await expect(page.getByRole("button", { name: "Create connection" })).toHaveCount(0);
  await page.getByRole("link", { name: "Members", exact: true }).click();
  await expect(page.getByText("Your role does not permit member administration.", { exact: true })).toBeVisible();
  expect(state.requests.some(r => r.endsWith("/members"))).toBe(false);
  expect(state.legacy).toEqual([]); expect(errors).toEqual([]);
});

test("submission retries preserve idempotency and cancellation keeps completed report", async ({ page }) => {
  const { state, errors } = await setup(page); state.failSubmission = true;
  await page.goto("/");
  await page.getByRole("combobox", { name: "Scan connection" }).selectOption(conn);
  await page.getByRole("checkbox", { name: "I am authorized to assess this cloud scope" }).check();
  await page.getByRole("button", { name: "Start assessment" }).click();
  await expect(page.getByRole("alert")).toContainText("503");
  await page.getByRole("button", { name: "Start assessment" }).click();
  await expect(page.getByText("Assessment queued.", { exact: true })).toBeVisible();
  expect(state.submissions).toHaveLength(2); expect(state.submissions[0]).toEqual(state.submissions[1]);
  expect(state.submissions[0].body).toEqual({ connection_id: conn, authorization_confirmed: true });
  await page.getByRole("button", { name: `Cancel ${queuedId}`, exact: true }).click();
  await expect(page.getByRole("cell", { name: "cancelled", exact: true })).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Active assessment" })).toHaveValue(runA);
  expect(state.legacy).toEqual([]); expect(errors).toEqual([]);
});

test("AWS onboarding verification and confirmed disconnect are scoped", async ({ page }) => {
  const { state, errors } = await setup(page); state.verified = false;
  await page.goto("/connections");
  await page.getByRole("button", { name: "Onboarding", exact: true }).click();
  await expect(page.getByText(/fixture-external-id/)).toBeVisible();
  await page.getByRole("button", { name: "Verify AWS Production", exact: true }).click();
  await expect(page.getByRole("cell", { name: "Verified", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Disconnect AWS Production", exact: true }).click();
  expect(state.connections).toBe(true);
  await page.getByRole("button", { name: "Confirm disconnect", exact: true }).click();
  await expect(page.getByRole("cell", { name: "Disconnected", exact: true })).toBeVisible();
  expect(state.legacy).toEqual([]); expect(errors).toEqual([]);
});

test("Azure credential is submitted once, cleared and never written to browser storage", async ({ page }) => {
  const { state, errors } = await setup(page);
  await page.goto("/connections"); await page.getByLabel("Provider", { exact: true }).selectOption("azure");
  await page.getByLabel("Connection name", { exact: true }).fill("Azure test");
  await page.getByLabel("Subscription ID", { exact: true }).fill(orgA);
  await page.getByLabel("Azure tenant ID", { exact: true }).fill(orgB);
  await page.getByLabel("Application ID", { exact: true }).fill(conn);
  await page.getByLabel("Application secret", { exact: true }).fill("fixture-secret-never-persist");
  await page.getByRole("button", { name: "Create connection", exact: true }).click();
  await expect(page.getByLabel("Application secret", { exact: true })).toHaveValue("");
  await expect.poll(() => state.created.length).toBe(1);
  expect(state.created[0]).toMatchObject({ provider: "azure", client_secret: "fixture-secret-never-persist", tenant_id: orgB, scope_id: orgA });
  expect(await page.evaluate(() => JSON.stringify({ ...sessionStorage, ...localStorage }))).not.toContain("fixture-secret-never-persist");
  expect(state.legacy).toEqual([]); expect(errors).toEqual([]);
});

test("401 clears visible findings and requires a new sign-in", async ({ page }) => {
  const { state, errors } = await setup(page);
  await page.goto("/findings"); await expect(page.getByRole("heading", { name: "Finding Alpha", exact: true })).toBeVisible();
  state.expired = true; await page.getByRole("button", { name: "Refresh organizations" }).click();
  await expect(page.getByRole("button", { name: "Sign in", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Finding Alpha", exact: true })).toHaveCount(0);
  expect(await page.evaluate(() => sessionStorage.getItem("oidc.user:https://identity.invalid:cris-console"))).toBeNull();
  expect(state.legacy).toEqual([]); expect(errors).toEqual([]);
});

test("membership revocation removes the workspace and never falls back to local results", async ({ page }) => {
  const { state, errors } = await setup(page);
  await page.goto("/findings"); await expect(page.getByRole("heading", { name: "Finding Alpha", exact: true })).toBeVisible();
  state.revoked = true; await page.getByRole("button", { name: "Refresh organizations" }).click();
  await expect(page.getByText("No organization access. Contact your administrator.", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Finding Alpha", exact: true })).toHaveCount(0);
  expect(state.legacy).toEqual([]); expect(errors).toEqual([]);
});

test("missing selected run cannot reveal a cached report or downloads", async ({ page }) => {
  const { state, errors } = await setup(page);
  await page.goto("/findings"); await expect(page.getByRole("heading", { name: "Finding Alpha", exact: true })).toBeVisible();
  state.missing = true;
  await page.reload();
  await expect(page.getByRole("heading", { name: "Finding Alpha", exact: true })).toHaveCount(0);
  await expect(page.getByRole("alert").first()).toContainText("unavailable");
  await page.getByRole("link", { name: "Reports", exact: true }).click();
  await expect(page.getByRole("button", { name: "Download cris_sme_report.json", exact: true })).toHaveCount(0);
  expect(state.legacy).toEqual([]); expect(errors).toEqual([]);
});

test("mobile workspace remains within viewport and clears expired sessions", async ({ page }) => {
  const { state, errors } = await setup(page);
  await page.setViewportSize({ width: 390, height: 844 }); await page.goto("/connections");
  await expect(page.getByRole("heading", { name: "Cloud connections", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await page.screenshot({ path: test.info().outputPath("enterprise-connections-mobile.png"), fullPage: true });
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page.getByRole("button", { name: "Sign in", exact: true })).toBeVisible();
  expect(state.legacy).toEqual([]); expect(errors).toEqual([]);
});
