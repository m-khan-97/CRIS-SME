import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Workspace } from "../enterprise/Workspace";
import { baseReport } from "./fixtures/report";

const mocks = vi.hoisted(() => ({ tenants: vi.fn(), jobs: vi.fn(), job: vi.fn(), connections: vi.fn(), request: vi.fn(), artifact: vi.fn(), report: vi.fn(), cancel: vi.fn(), signOut: vi.fn() }));
vi.mock("../enterprise/Auth", () => ({ useSession: () => ({ api: { ...mocks, path: (org: string, suffix: string) => `/api/v1/tenants/${org}/${suffix}` }, signOut: mocks.signOut }) }));
const tenant = { id: "alpha", name: "Alpha Organization", role: "owner" };
const connection = { id: "connection", name: "AWS Test", provider: "aws", scope_id: "123456789012", enabled: true, verified_until: 4000000000 };
const job = { id: "run-a", tenant_id: "alpha", connection_id: "connection", status: "completed", requested_at: 1790000000, error_code: "", attempt: 1,
  artifacts: [{ id: "artifact-a", name: "cris_sme_report.json", sha256: "a".repeat(64), size: 2 }] };

function mount(path = "/") {
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const result = render(<QueryClientProvider client={cache}><MemoryRouter initialEntries={[path]}><Workspace /></MemoryRouter></QueryClientProvider>);
  return { ...result, cache };
}
beforeEach(() => {
  vi.clearAllMocks(); sessionStorage.clear();
  mocks.tenants.mockResolvedValue({ tenants: [tenant, { id: "beta", name: "Beta Organization", role: "analyst" }] });
  mocks.connections.mockResolvedValue({ connections: [connection] });
  mocks.jobs.mockResolvedValue({ assessments: [job] }); mocks.job.mockResolvedValue(job);
  mocks.report.mockResolvedValue(baseReport); mocks.request.mockResolvedValue({ status: "updated" });
});

describe("enterprise workspace", () => {
  it("changes organization with request cancellation and signs out", async () => {
    mount();
    await screen.findByRole("heading", { name: "Assessments" });
    fireEvent.change(screen.getByRole("combobox", { name: "Organization" }), { target: { value: "beta" } });
    await waitFor(() => expect(mocks.jobs).toHaveBeenCalledWith("beta"));
    expect(mocks.cancel).toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Sign out" })); expect(mocks.signOut).toHaveBeenCalled();
  });
  it("keeps a membership lookup failure outside the workspace", async () => {
    mocks.tenants.mockRejectedValue(new Error("Denied")); mount();
    await screen.findByRole("alert"); expect(screen.queryByRole("heading", { name: "Assessments" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(mocks.tenants).toHaveBeenCalledTimes(2));
  });
  it("requires authorization, uses an idempotency key and cancels a queued scan", async () => {
    mocks.jobs.mockResolvedValue({ assessments: [job, { ...job, id: "queued", status: "queued" }] });
    mount(); await screen.findByRole("heading", { name: "Assessments" });
    await screen.findByRole("option", { name: /AWS Test/ });
    expect(screen.getByRole("button", { name: "Start assessment" })).toBeDisabled();
    fireEvent.change(screen.getByRole("combobox", { name: "Scan connection" }), { target: { value: "connection" } });
    fireEvent.click(screen.getByRole("checkbox")); fireEvent.click(screen.getByRole("button", { name: "Start assessment" }));
    await screen.findByText("Assessment queued.");
    expect(mocks.request).toHaveBeenCalledWith("/api/v1/tenants/alpha/assessments", { connection_id: "connection", authorization_confirmed: true }, "POST", expect.any(String));
    fireEvent.click(screen.getByRole("button", { name: "Cancel queued" }));
    await waitFor(() => expect(mocks.request).toHaveBeenCalledWith("/api/v1/tenants/alpha/assessments/queued/cancel", {}, "POST"));
  });
  it("persists explicit assessment selection within the organization", async () => {
    mocks.jobs.mockResolvedValue({ assessments: [job, { ...job, id: "run-b" }] });
    mount(); const select = await screen.findByRole("combobox", { name: "Active assessment" });
    await waitFor(() => expect(select).toHaveValue("run-a"));
    fireEvent.change(select, { target: { value: "run-b" } });
    await waitFor(() => expect(mocks.job).toHaveBeenCalledWith("alpha", "run-b"));
    expect(sessionStorage.getItem("cris.enterprise.run.alpha")).toBe("run-b");
  });
  it("shows connection creation and AWS onboarding only to administrators", async () => {
    mocks.request.mockResolvedValue({ external_id: "fixture-id" });
    mount("/connections"); await screen.findByRole("heading", { name: "Cloud connections" });
    fireEvent.change(screen.getByLabelText("Connection name"), { target: { value: "New account" } });
    fireEvent.change(screen.getByLabelText("AWS account ID"), { target: { value: "123456789012" } });
    fireEvent.change(screen.getByLabelText("Target role ARN"), { target: { value: "arn:aws:iam::123456789012:role/CRIS" } });
    fireEvent.click(screen.getByRole("button", { name: "Create connection" }));
    await waitFor(() => expect(mocks.request).toHaveBeenCalledWith("/api/v1/tenants/alpha/connections", expect.objectContaining({ provider: "aws", name: "New account" }), "POST"));
    fireEvent.click(screen.getByRole("button", { name: "Onboarding" }));
    await screen.findByText(/fixture-id/);
    fireEvent.click(screen.getByRole("button", { name: "Verify AWS Test" }));
    await waitFor(() => expect(mocks.request).toHaveBeenCalledWith("/api/v1/tenants/alpha/connections/connection/verify", {}, "POST"));
    fireEvent.click(screen.getByRole("button", { name: "Disconnect AWS Test" }));
    await screen.findByRole("alertdialog"); fireEvent.click(screen.getByRole("button", { name: "Confirm disconnect" }));
    await waitFor(() => expect(mocks.request).toHaveBeenCalledWith("/api/v1/tenants/alpha/connections/connection/disconnect", {}, "POST"));
  });
  it("clears a submitted Azure secret on error without a credential-bearing mutation", async () => {
    mocks.request.mockRejectedValue(new Error("Connection creation failed"));
    const { cache } = mount("/connections"); await screen.findByRole("heading", { name: "Cloud connections" });
    fireEvent.change(screen.getByRole("combobox", { name: "Provider" }), { target: { value: "azure" } });
    for (const [label, value] of [["Connection name", "Azure"], ["Subscription ID", "sub"], ["Azure tenant ID", "tenant"], ["Application ID", "app"], ["Application secret", "private-secret"]]) {
      fireEvent.change(screen.getByLabelText(label, { exact: true }), { target: { value } });
    }
    fireEvent.submit(screen.getByRole("button", { name: "Create connection" }).closest("form")!);
    await screen.findByText("Connection creation failed");
    expect(screen.getByLabelText("Application secret")).toHaveValue("");
    expect(JSON.stringify(cache.getMutationCache().getAll().map(m => m.state.variables))).not.toContain("private-secret");
  });
  it("supports member updates and confirmed removal", async () => {
    mocks.request.mockImplementation((_path: string, _body: unknown, method?: string) => method ? Promise.resolve({ status: "updated" }) : Promise.resolve({ members: [{ subject: "fixture-member", issuer: "https://identity.example", role: "analyst" }] }));
    mount("/members"); await screen.findByText("fixture-member");
    fireEvent.change(screen.getByLabelText("Identity subject"), { target: { value: "new-member" } });
    fireEvent.click(screen.getByRole("button", { name: "Save member" }));
    await waitFor(() => expect(mocks.request).toHaveBeenCalledWith("/api/v1/tenants/alpha/members/new-member", { role: "analyst" }, "PUT"));
    fireEvent.click(screen.getByRole("button", { name: "Remove fixture-member" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm removal" }));
    await waitFor(() => expect(mocks.request).toHaveBeenCalledWith("/api/v1/tenants/alpha/members/fixture-member", undefined, "DELETE"));
  });
  it("shows successful audit events", async () => {
    mocks.request.mockResolvedValue({ events: [{ id: "event", subject: "actor", action: "connection.verified", resource_id: "connection", created_at: 1790000000 }] });
    mount("/audit"); await screen.findByText("connection.verified");
    fireEvent.click(screen.getByRole("button", { name: "Refresh audit" }));
    await waitFor(() => expect(mocks.request).toHaveBeenCalledTimes(2));
  });
  it("shows organization-scoped quota, queue and action budgets", async () => {
    mocks.request.mockResolvedValue({ quota_bytes: 1073741824, max_artifacts: 10000,
      registered_bytes: 4096, registered_artifacts: 2, reserved_bytes: 134217728, reserved_artifacts: 5,
      pending_assessments: 1, assessments: { queued: 1, running: 0, failed: 2 }, oldest_queue_age_seconds: 15,
      expired_leases: 0, rate_limits: { scan_submission: { used: 2, limit: 24, remaining: 22, reset_after_seconds: 60 } } });
    mount("/operations");
    await screen.findByText("1.00 GiB");
    expect(screen.getByRole("region", { name: "Action budgets" })).toHaveTextContent("2 / 24");
    expect(mocks.request).toHaveBeenCalledWith("/api/v1/tenants/alpha/operations");
    fireEvent.click(screen.getByRole("button", { name: "Refresh operations" }));
    await waitFor(() => expect(mocks.request).toHaveBeenCalledTimes(2));
  });
  it("does not load operations for analysts", async () => {
    mocks.tenants.mockResolvedValue({ tenants: [{ ...tenant, role: "analyst" }] });
    mount("/operations");
    await screen.findByText("Your role does not permit this view.");
    expect(mocks.request).not.toHaveBeenCalled();
  });
  it("hides operations data on a request failure", async () => {
    mocks.request.mockRejectedValue(new Error("Operation unavailable"));
    mount("/operations");
    await screen.findByText("Operation unavailable");
    expect(screen.queryByRole("region", { name: "Storage capacity" })).not.toBeInTheDocument();
  });
  it("does not request member or audit administration for an analyst", async () => {
    mocks.tenants.mockResolvedValue({ tenants: [{ ...tenant, role: "analyst" }] });
    const view = mount("/members"); await screen.findByText("Your role does not permit member administration.");
    expect(mocks.request).not.toHaveBeenCalled(); view.unmount();
    mount("/audit"); await screen.findByText("Your role does not permit audit access."); expect(mocks.request).not.toHaveBeenCalled();
  });
  it("renders missing report state without artifact links", async () => {
    mocks.jobs.mockResolvedValue({ assessments: [] }); mount("/reports");
    await screen.findByText("No completed assessment selected."); expect(mocks.artifact).not.toHaveBeenCalled();
  });
  it("renders download metadata and an integrity failure", async () => {
    mocks.artifact.mockRejectedValue(new Error("Artifact integrity check failed.")); mount("/reports");
    fireEvent.click(await screen.findByRole("button", { name: "Download cris_sme_report.json" }));
    await screen.findByText("Artifact integrity check failed.");
  });
  it("identifies imported assessments with original IDs and source classifications", async () => {
    const historical_import = { source_run_id: "original-source-run", source_organization_id: "old-org-id",
      source_sha256: "b".repeat(64), bundle_sha256: "c".repeat(64), generated_at: "2026-07-03T12:40:13Z",
      imported_at: 1790000000, provider: "aws", scope_id: "123456789012", reported_source_type: "vulnerable_lab" };
    const imported = { ...job, origin: "historical_import", historical_import };
    mocks.jobs.mockResolvedValue({ assessments: [imported] }); mocks.job.mockResolvedValue(imported);
    mocks.connections.mockResolvedValue({ connections: [{ ...connection, enabled: false, origin: "historical_archive" }] });
    mount("/reports");
    await screen.findByRole("region", { name: "Historical import" });
    expect(screen.getByText("Imported historical assessment · Not rescanned")).toBeInTheDocument();
    expect(screen.getByText(/vulnerable_lab.*preserved as supplied, not revalidated/)).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Active assessment" })).toHaveValue("run-a");
    expect(screen.getByRole("option", { name: /\[Imported\].*original-source-run/ })).toBeInTheDocument();
  });
  it("never offers onboarding or verification for an archive connection", async () => {
    mocks.connections.mockResolvedValue({ connections: [{ ...connection, enabled: false, origin: "historical_archive" }] });
    mount("/connections");
    await screen.findByRole("cell", { name: "Historical archive" });
    expect(screen.queryByRole("button", { name: "Onboarding" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Verify AWS Test" })).not.toBeInTheDocument();
  });
});
