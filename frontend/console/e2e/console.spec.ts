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
  const state = { polls: 0, submissions: [] as Record<string, unknown>[], completed: false };
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
