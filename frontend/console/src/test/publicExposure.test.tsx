import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PublicExposure } from "../pages/PublicExposure";

const ids = ["run_1111111111111111", "run_2222222222222222"];
function report(id: string) {
  return { run_id: id, assessment_type: "public_exposure", generated_at: "2026-10-02T12:00:00Z",
    summary: { target_count: 1, finding_count: 1 }, targets: [{ host: `${id}.example.com` }],
    findings: [{ id: "PE-001", title: `Finding ${id}`, severity: "medium", target: "example.com" }],
    artifacts: { json: `outputs/assessments/${id}/reports/cris_sme_public_exposure.json` } };
}

function setup(options: { missing?: boolean; historyError?: boolean } = {}) {
  const submissions: unknown[] = [];
  const fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    let body: unknown;
    if (url === "/api/public-exposure-history") {
      if (options.historyError) return new Response("unavailable", { status: 503 });
      body = { assessments: ids.map((run_id) => ({ run_id, generated_at: "2026-10-02T12:00:00Z", targets: ["example.com"], finding_count: 1 })) };
    } else if (url === "/api/public-exposure") {
      submissions.push(JSON.parse(init?.body as string));
      body = report("run_3333333333333333");
    } else if (url.startsWith("/api/public-exposure-reports/")) {
      if (options.missing && url.endsWith(ids[1])) return new Response("missing", { status: 404 });
      body = report(url.split("/").at(-1)!);
    } else return new Response("unexpected request", { status: 404 });
    return new Response(JSON.stringify(body), { headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetch);
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <PublicExposure />
  </QueryClientProvider>);
  return { submissions, fetch };
}

afterEach(() => { vi.unstubAllGlobals(); localStorage.clear(); });

describe("public exposure saved assessments", () => {
  it("loads the latest then selects an older report with its exact export", async () => {
    const { submissions } = setup();
    expect(await screen.findByText(`Finding ${ids[0]}`)).toBeVisible();
    fireEvent.change(screen.getByRole("combobox", { name: "Public exposure assessment" }), { target: { value: ids[1] } });
    expect(await screen.findByText(`Finding ${ids[1]}`)).toBeVisible();
    expect(screen.queryByText(`Finding ${ids[0]}`)).not.toBeInTheDocument();
    expect(localStorage.getItem("cris-public-exposure-run")).toBe(ids[1]);
    expect(screen.getByRole("link", { name: "JSON" })).toHaveAttribute("href", expect.stringContaining(ids[1]));
    expect(submissions).toEqual([]);
  });

  it("restores the saved selection and shows failure without another report's findings", async () => {
    localStorage.setItem("cris-public-exposure-run", ids[1]);
    setup({ missing: true });
    expect(await screen.findByText(/Selected assessment is unavailable/)).toBeVisible();
    expect(screen.queryByText(`Finding ${ids[0]}`)).not.toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Public exposure assessment" })).toHaveValue(ids[1]);
  });

  it("selects a newly completed scan and records explicit authorization", async () => {
    const { submissions } = setup();
    await screen.findByText(`Finding ${ids[0]}`);
    fireEvent.change(screen.getByRole("textbox", { name: /Targets/ }), { target: { value: "example.com" } });
    fireEvent.click(screen.getByRole("checkbox", { name: /I confirm I am authorized/ }));
    fireEvent.click(screen.getByRole("button", { name: "Run assessment" }));
    expect(await screen.findByText("Finding run_3333333333333333")).toBeVisible();
    expect(submissions).toEqual([{ targets: "example.com", authorization_confirmed: true, scan_common_ports: false }]);
    expect(localStorage.getItem("cris-public-exposure-run")).toBe("run_3333333333333333");
  });

  it("refreshes history and keeps the scan form available when history fails", async () => {
    const { fetch } = setup({ historyError: true });
    expect(await screen.findByText(/Saved scans are unavailable/)).toBeVisible();
    expect(screen.getByRole("textbox", { name: /Targets/ })).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Refresh saved scans" }));
    await waitFor(() => expect(fetch.mock.calls.filter(([url]) => url === "/api/public-exposure-history")).toHaveLength(2));
  });
});
