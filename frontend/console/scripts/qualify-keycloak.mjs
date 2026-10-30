// Opt-in local integration: actual Keycloak, PostgreSQL and API; no cloud calls.
import assert from "node:assert/strict";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { chromium } from "playwright";

const state = resolve(process.argv[2] ?? "../../.local/keycloak");
const accounts = JSON.parse(await readFile(resolve(state, "accounts.json"), "utf8"));
const pin = (await readFile(resolve(state, "certificate-spki.txt"), "utf8")).trim();
const normalTrust = process.env.CRIS_KEYCLOAK_SYSTEM_TRUST === "true";
const output = resolve(state, "qualification");
await mkdir(output, { recursive: true, mode: 0o700 });
const results = { environment: "local_identity_integration", identity_provider: "Keycloak 26.8.1",
  started_at: new Date().toISOString(), console: "http://localhost:5174", issuer: "https://localhost:8443/realms/cris",
  tls: normalTrust ? "private CA verified by backend; normal Chrome NSS exact-leaf trust, no TLS bypass flags"
    : "private CA verified by backend; exact server SPKI pinned in isolated Chromium",
  database: "dedicated local PostgreSQL", cloud_calls: false, checks: [] };
const browser = await chromium.launch(normalTrust ? { channel: "chrome" }
  : { args: [`--ignore-certificate-errors-spki-list=${pin}`] });
const contexts = [];
const errors = [];

async function check(name, fn) {
  await fn(); results.checks.push({ name, status: "passed" });
  console.log(`PASS ${name}`);
}
async function login(account) {
  const context = await browser.newContext(); contexts.push(context);
  const page = await context.newPage();
  page.setDefaultTimeout(20_000);
  page.on("pageerror", error => errors.push(error.message));
  await page.goto(results.console);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.locator("#username").fill(account.username);
  await page.locator("#password").fill(account.password);
  await page.locator("#kc-login").click();
  await page.getByRole("combobox", { name: "Organization", exact: true }).waitFor({ timeout: 30_000 });
  const user = await page.evaluate(() => JSON.parse(sessionStorage.getItem("oidc.user:https://localhost:8443/realms/cris:cris-console")));
  assert.equal(user.profile.sub, account.id, "Identity must match the provisioned account");
  assert.ok(user.access_token && user.id_token, "Code flow must return identity and API tokens");
  return { context, page, user };
}
async function request(user, path, options = {}) {
  return fetch(`http://127.0.0.1:8788${path}`, { ...options,
    headers: { ...(user ? { Authorization: `Bearer ${user.access_token}` } : {}),
      ...(options.body ? { "Content-Type": "application/json" } : {}) }, redirect: "error", signal: AbortSignal.timeout(15_000) });
}

let owner;
let analyst;
let tenant;
let removed = false;
try {
  await check("unauthenticated API is denied and legacy routes are absent", async () => {
    assert.equal((await request(null, "/api/v1/me")).status, 401);
    assert.equal((await request(null, "/api/assessment-history")).status, 404);
  });
  await check("real browser PKCE sign-in and signed access token reach PostgreSQL membership", async () => {
    owner = await login(accounts.owner);
    const me = await request(owner.user, "/api/v1/me"); assert.equal(me.status, 200);
    assert.equal((await me.json()).subject, accounts.owner.id);
    const response = await request(owner.user, "/api/v1/tenants"); assert.equal(response.status, 200);
    const rows = (await response.json()).tenants;
    const workspaces = rows.filter(row => row.name === "CRIS Local Workspace" && row.role === "owner");
    assert.equal(workspaces.length, 1, "The dedicated qualification workspace must exist exactly once");
    tenant = workspaces[0].id;
    const inventory = await request(owner.user, `/api/v1/tenants/${tenant}/storage`);
    assert.equal(inventory.status, 200);
    const usage = await inventory.json();
    assert.ok(Number.isSafeInteger(usage.registered_bytes) && usage.registered_bytes >= 0);
    assert.equal(usage.includes_unreferenced_files, false);
    const retention = await request(owner.user, `/api/v1/tenants/${tenant}/retention`);
    assert.equal(retention.status, 200);
    assert.ok(Array.isArray((await retention.json()).holds));
    const operations = await request(owner.user, `/api/v1/tenants/${tenant}/operations`);
    assert.equal(operations.status, 200);
    const operational = await operations.json();
    assert.ok(operational.quota_bytes > 0 && operational.registered_bytes >= 0);
    assert.equal(operational.rate_limits.scan_submission.limit, 24);
    await owner.page.getByRole("combobox", { name: "Organization", exact: true }).selectOption(tenant);
    await owner.page.getByRole("heading", { name: "Assessments", exact: true }).waitFor();
    await owner.page.screenshot({ path: resolve(output, "owner-workspace.png"), fullPage: true });
  });
  await check("real identity token cannot substitute for an API access token", async () => {
    assert.equal((await request({ access_token: owner.user.id_token }, "/api/v1/me")).status, 401);
  });
  await check("tampered signed token is rejected", async () => {
    const parts = owner.user.access_token.split(".");
    parts[2] = (parts[2][0] === "A" ? "B" : "A") + parts[2].slice(1);
    assert.equal((await request({ access_token: parts.join(".") }, "/api/v1/me")).status, 401);
  });
  await check("second real identity cannot discover another organization's jobs or connections", async () => {
    const other = await login(accounts.outsider);
    const rows = (await (await request(other.user, "/api/v1/tenants")).json()).tenants;
    assert.equal(rows.length, 1); assert.notEqual(rows[0].id, tenant);
    assert.equal((await request(other.user, `/api/v1/tenants/${tenant}/assessments`)).status, 404);
    assert.equal((await request(other.user, `/api/v1/tenants/${tenant}/connections`)).status, 404);
    assert.equal((await request(other.user, `/api/v1/tenants/${tenant}/operations`)).status, 404);
  });
  await check("analyst identity reads its organization but cannot create cloud connections", async () => {
    analyst = await login(accounts.analyst);
    assert.equal((await request(analyst.user, `/api/v1/tenants/${tenant}/assessments`)).status, 200);
    assert.equal((await request(analyst.user, `/api/v1/tenants/${tenant}/storage`)).status, 403);
    assert.equal((await request(analyst.user, `/api/v1/tenants/${tenant}/retention`)).status, 403);
    assert.equal((await request(analyst.user, `/api/v1/tenants/${tenant}/operations`)).status, 403);
    assert.equal((await request(analyst.user, `/api/v1/tenants/${tenant}/connections`, { method: "POST", body: JSON.stringify({
      name: "Denied qualification request", provider: "aws", scope_id: "000000000000", role_arn: "arn:aws:iam::000000000000:role/not-created",
    }) })).status, 403);
  });
  await check("membership revocation immediately denies an existing real access token", async () => {
    const path = `/api/v1/tenants/${tenant}/members/${accounts.analyst.id}`;
    const response = await request(owner.user, path, { method: "DELETE" }); assert.equal(response.status, 200); removed = true;
    assert.equal((await request(analyst.user, `/api/v1/tenants/${tenant}/assessments`)).status, 404);
    await analyst.page.getByRole("button", { name: "Refresh organizations", exact: true }).click();
    await analyst.page.getByText("No organization access. Contact your administrator.", { exact: true }).waitFor();
    assert.equal((await request(owner.user, path, { method: "PUT", body: JSON.stringify({ role: "analyst" }) })).status, 200); removed = false;
  });
  await check("browser sign-out clears its session without a local report fallback", async () => {
    await owner.page.getByRole("button", { name: "Sign out", exact: true }).click();
    await owner.page.getByRole("button", { name: "Sign in", exact: true }).waitFor();
    assert.equal(await owner.page.evaluate(() => sessionStorage.getItem("oidc.user:https://localhost:8443/realms/cris:cris-console")), null);
    assert.deepEqual(errors, []);
  });
  results.status = "passed";
} catch (error) {
  results.status = "failed";
  results.failure = `Check ${results.checks.length + 1} failed (${error.name})`;
  await writeFile(resolve(output, "failure.txt"), error.message, { mode: 0o600 });
  const page = contexts.at(-1)?.pages().at(-1);
  if (page) await page.screenshot({ path: resolve(output, "failure.png"), fullPage: true }).catch(() => undefined);
  process.exitCode = 1;
} finally {
  if (removed && owner && tenant) {
    try {
      const response = await request(owner.user, `/api/v1/tenants/${tenant}/members/${accounts.analyst.id}`, { method: "PUT", body: JSON.stringify({ role: "analyst" }) });
      if (!response.ok) throw new Error("Restore failed");
    } catch {
      results.status = "failed"; results.cleanup = "Analyst membership restore failed; restore explicitly before re-running."; process.exitCode = 1;
    }
  }
  await Promise.allSettled(contexts.map(context => context.close()));
  await browser.close().catch(() => undefined);
  results.completed_at = new Date().toISOString();
  await writeFile(resolve(output, "result.json"), JSON.stringify(results, null, 2) + "\n", { mode: 0o600 });
  console.log(`Local identity qualification ${results.status}. Private results: ${output}`);
}
