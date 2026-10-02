import { expect, test, type Page } from "@playwright/test";
import { baseReport, finding } from "../src/test/fixtures/report";
import type { AssessmentHistoryEntry, AssessmentRun, CrisReport } from "../src/api/types";

const entries: AssessmentHistoryEntry[] = ["alpha", "beta"].map((id) => ({
  report_id: id, run_id: id, organization_id: id, organization_name: `Fixture ${id}`,
  provider: "azure", generated_at: "2026-09-25T10:00:00Z", overall_risk_score: 20,
  finding_count: 1, collector_mode: "mock",
}));

function report(id: string): CrisReport {
  return { ...baseReport, prioritized_risks: [finding(id, "open")],
    report_artifacts: { json_report: `outputs/${id}/report.json` } };
}

async function mockApi(page: Page, options: { unavailable?: boolean; failedScan?: boolean } = {}) {
  const state = { polls: 0, submissions: [] as Record<string, unknown>[], completed: false, publicCompleted: false };
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  // Fail closed: no test may call a real backend or an external service.
  await page.context().route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.origin !== "http://127.0.0.1:4179") return route.abort();
    const path = url.pathname;
    if (!path.startsWith("/api/") && !path.startsWith("/outputs/") && path !== "/health") return route.continue();
    if (options.unavailable) return route.fulfill({ status: 404, json: { message: "Fixture backend unavailable" } });
    if (path === "/health") return route.fulfill({ json: { status: "ok" } });
    if (path === "/api/assessment-history") return route.fulfill({ json: { assessments: state.completed
      ? [{ ...entries[0], run_id: "scan", report_id: "scan", organization_name: "Fixture scan" }, ...entries] : entries } });
    if (path.startsWith("/api/assessment-reports/")) return route.fulfill({ json: report(path.split("/").at(-1)!) });
    if (path === "/api/report-artifact") return route.fulfill({ json: { fixture_artifact: url.searchParams.get("path") } });
    if (path === "/api/environment/azure") return route.fulfill({ json: {
      status: "authenticated", authenticated: true, azure_cli_available: true, account: null, message: "Fixture credentials",
    } });
    if (path === "/api/public-exposure-history") return route.fulfill({ json: {
      assessments: (state.publicCompleted ? ["public-scan", "public-alpha", "public-beta"] : ["public-alpha", "public-beta"]).map((run_id) => ({
        run_id, generated_at: "2026-10-02T12:00:00Z", targets: ["example.com"], finding_count: 1,
      })),
    } });
    if (path.startsWith("/api/public-exposure-reports/")) return route.fulfill({ json: publicReport(path.split("/").at(-1)!) });
    if (path === "/api/public-exposure" && route.request().method() === "POST") {
      state.submissions.push(route.request().postDataJSON() as Record<string, unknown>);
      state.publicCompleted = true;
      return route.fulfill({ json: publicReport("public-scan") });
    }
    const run: AssessmentRun = {
      run_id: "scan", collector: "azure", status: "queued", requested_at: baseReport.generated_at,
      started_at: "", completed_at: "", authorization_confirmed: true, subscription_id: "", tenant_id: "",
      account_id: "", role_arn: "", output_dir: "", figure_dir: "", returncode: null,
      stdout_tail: "", stderr_tail: "", error: "", runner_events: [], artifacts: {},
    };
    if (path === "/api/assessments/azure" && route.request().method() === "POST") {
      state.submissions.push(route.request().postDataJSON() as Record<string, unknown>);
      return route.fulfill({ status: 202, json: run });
    }
    if (path === "/api/assessments/scan") {
      state.polls++;
      const finished = state.polls >= 2;
      state.completed = finished && !options.failedScan;
      return route.fulfill({ json: { ...run, status: !finished ? "running" : options.failedScan ? "failed" : "completed",
        error: finished && options.failedScan ? "Fixture permission denied" : "" } });
    }
    return route.fulfill({ status: 404, json: { message: "Unconfigured fixture route" } });
  });
  return { state, errors };
}

function publicReport(run_id: string) {
  return { run_id, assessment_type: "public_exposure", generated_at: "2026-10-02T12:00:00Z",
    summary: { target_count: 1, finding_count: 1 }, targets: [{ host: "example.com" }],
    findings: [{ id: "PE-001", title: `Public finding ${run_id}`, severity: "medium", target: "example.com" }],
    artifacts: { json: `outputs/assessments/${run_id}/reports/cris_sme_public_exposure.json`,
      markdown: `outputs/assessments/${run_id}/reports/cris_sme_public_exposure.md` } };
}

test("public scan selection survives reload, exports its report and selects a new authorized scan", async ({ page }) => {
  const { state, errors } = await mockApi(page);
  await page.goto("/public-exposure");
  const selection = page.getByRole("combobox", { name: "Public exposure assessment" });
  await expect(page.getByRole("combobox", { name: "Active assessment" })).toHaveCount(0);
  await expect(page.getByText("Public finding public-alpha", { exact: true })).toBeVisible();
  await selection.selectOption("public-beta");
  await expect(page.getByText("Public finding public-beta", { exact: true })).toBeVisible();
  await page.reload();
  await expect(selection).toHaveValue("public-beta");
  await expect(page.getByText("Public finding public-beta", { exact: true })).toBeVisible();
  const exportLink = page.getByRole("link", { name: "JSON", exact: true });
  await expect(exportLink).toHaveAttribute("href", /public-beta/);
  const popupPromise = page.waitForEvent("popup");
  await exportLink.click();
  const popup = await popupPromise;
  await expect(popup.locator("body")).toContainText("public-beta");
  await popup.close();
  await page.getByRole("textbox", { name: /Targets/ }).fill("example.com");
  await page.getByRole("checkbox", { name: /I confirm I am authorized/ }).check();
  await page.getByRole("button", { name: "Run assessment", exact: true }).click();
  await expect(selection).toHaveValue("public-scan");
  await expect(page.getByText("Public finding public-scan", { exact: true })).toBeVisible();
  await page.screenshot({ path: test.info().outputPath("public-history-desktop.png"), fullPage: true });
  expect(state.submissions).toEqual([{ targets: "example.com", authorization_confirmed: true, scan_common_ports: false }]);
  expect(errors).toEqual([]);
});

test("mobile public history shows a missing selected report without stale findings", async ({ page }) => {
  const { errors } = await mockApi(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/api/public-exposure-reports/public-beta", (route) => route.fulfill({ status: 404, json: { message: "Missing report" } }));
  await page.goto("/public-exposure");
  await expect(page.getByText("Public finding public-alpha", { exact: true })).toBeVisible();
  await page.screenshot({ path: test.info().outputPath("public-history-mobile.png"), fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
  await page.getByRole("combobox", { name: "Public exposure assessment" }).selectOption("public-beta");
  await expect(page.getByText(/Selected assessment is unavailable/)).toBeVisible();
  await expect(page.getByText("Public finding public-alpha", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("link", { name: "JSON", exact: true })).toHaveCount(0);
  await page.getByRole("combobox", { name: "Navigation" }).selectOption("/findings");
  await expect(page.getByRole("heading", { name: "Finding alpha", exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

test("switches report, persists selection and retrieves its artifact", async ({ page }) => {
  const { errors } = await mockApi(page);
  await page.goto("/findings");
  await expect(page.getByRole("heading", { name: "Finding alpha", exact: true })).toBeVisible();
  await page.getByRole("combobox", { name: "Active assessment" }).selectOption("beta");
  await expect(page.getByRole("heading", { name: "Finding beta", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Finding alpha", exact: true })).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole("combobox", { name: "Active assessment" })).toHaveValue("beta");
  await page.getByRole("link", { name: "Reports & Artifacts", exact: true }).click();
  const link = page.getByRole("link", { name: "Open", exact: true });
  await expect(link).toHaveAttribute("href", /outputs%2Fbeta%2Freport.json/);
  const popupPromise = page.waitForEvent("popup");
  await link.click();
  const popup = await popupPromise;
  await expect(popup.locator("body")).toContainText("outputs/beta/report.json");
  await page.screenshot({ path: test.info().outputPath("selected-report.png"), fullPage: true });
  expect(errors).toEqual([]);
});

test("missing backend settles into an explicit empty state", async ({ page }) => {
  const { errors } = await mockApi(page, { unavailable: true });
  await page.goto("/findings");
  await expect(page.getByText("No assessment report found yet.", { exact: true })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("Local runner · unavailable", { exact: true })).toBeVisible();
  expect(errors).toEqual([]);
});

for (const failedScan of [false, true]) {
  test(`authorized mock scan ${failedScan ? "fails visibly" : "completes and selects its report"}`, async ({ page }) => {
    const { state, errors } = await mockApi(page, { failedScan });
    await page.goto("/assessment");
    const start = page.getByRole("button", { name: "Start assessment", exact: true });
    await expect(start).toBeDisabled();
    await page.getByRole("textbox", { name: /Organization name/ }).fill("Fixture scan");
    await expect(start).toBeDisabled();
    await page.getByRole("checkbox", { name: /I confirm I am authorized/ }).check();
    await start.click();
    await expect(page.getByText("running", { exact: true })).toBeVisible();
    if (failedScan) {
      await expect(page.getByText("Fixture permission denied", { exact: true })).toBeVisible();
      await expect(page.getByRole("combobox", { name: "Active assessment" })).toHaveValue("alpha");
    } else {
      await expect(page.getByText(/Assessment complete\. Visit Overview/)).toBeVisible();
      await expect(page.getByRole("combobox", { name: "Active assessment" })).toHaveValue("scan");
      await page.getByRole("link", { name: "Findings", exact: true }).click();
      await expect(page.getByRole("heading", { name: "Finding scan", exact: true })).toBeVisible();
    }
    expect(state.submissions).toEqual([{ authorization_confirmed: true, organization_name: "Fixture scan" }]);
    expect(errors).toEqual([]);
  });
}
