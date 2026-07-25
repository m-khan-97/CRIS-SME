import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AssessmentProvider } from "../context/AssessmentContext";

import { AttackPaths } from "../pages/AttackPaths";
import { Compliance } from "../pages/Compliance";
import { CyberEssentials } from "../pages/CyberEssentials";
import { DisclosureRoom } from "../pages/DisclosureRoom";
import { EvidenceProvenance } from "../pages/EvidenceProvenance";
import { Findings } from "../pages/Findings";
import { Governance } from "../pages/Governance";
import { HealthcareIot } from "../pages/HealthcareIot";
import { NativeValidation } from "../pages/NativeValidation";
import { NewAssessment } from "../pages/NewAssessment";
import { Overview } from "../pages/Overview";
import { Personas } from "../pages/Personas";
import { PublicExposure } from "../pages/PublicExposure";
import { Remediation } from "../pages/Remediation";
import { ReportsArtifacts } from "../pages/ReportsArtifacts";
import { Resources } from "../pages/Resources";
import { TrendHistory } from "../pages/TrendHistory";
import { TrustCenter } from "../pages/TrustCenter";

// Real anonymised demo report — the same fixture the live static demo ships,
// so a smoke-test pass here means the actual demo bundle's data shape works
// against every route, not a hand-trimmed stand-in that could drift from it.
const DEMO_REPORT_PATH = resolve(process.cwd(), "public/outputs/cris_sme_report.json");
const demoReport = JSON.parse(readFileSync(DEMO_REPORT_PATH, "utf-8"));

const ROUTES: { path: string; name: string; Component: React.ComponentType }[] = [
  { path: "/", name: "Overview", Component: Overview },
  { path: "/assessment", name: "NewAssessment", Component: NewAssessment },
  { path: "/findings", name: "Findings", Component: Findings },
  { path: "/resources", name: "Resources", Component: Resources },
  { path: "/attack-paths", name: "AttackPaths", Component: AttackPaths },
  { path: "/personas", name: "Personas", Component: Personas },
  { path: "/compliance", name: "Compliance", Component: Compliance },
  { path: "/cyber-essentials", name: "CyberEssentials", Component: CyberEssentials },
  { path: "/iomt", name: "HealthcareIot", Component: HealthcareIot },
  { path: "/remediation", name: "Remediation", Component: Remediation },
  { path: "/evidence", name: "EvidenceProvenance", Component: EvidenceProvenance },
  { path: "/trust", name: "TrustCenter", Component: TrustCenter },
  { path: "/disclosure", name: "DisclosureRoom", Component: DisclosureRoom },
  { path: "/reports", name: "ReportsArtifacts", Component: ReportsArtifacts },
  { path: "/trend", name: "TrendHistory", Component: TrendHistory },
  { path: "/governance", name: "Governance", Component: Governance },
  { path: "/native-validation", name: "NativeValidation", Component: NativeValidation },
  { path: "/public-exposure", name: "PublicExposure", Component: PublicExposure },
];

function mockFetchWith(report: unknown | null) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();

      if (url.includes("/health")) {
        return jsonResponse({ status: "ok", service: "cris-sme", message: "ok" });
      }
      // Matches what the real static demo deploy sees: no backend, so
      // history/environment endpoints 404 and every page falls back to the
      // bundled report via getLatestReport().
      if (url.includes("/api/")) {
        return new Response("not found", { status: 404 });
      }
      if (url.includes("cris_sme_report.json")) {
        return report === null
          ? new Response("not found", { status: 404 })
          : jsonResponse(report);
      }
      return new Response("not found", { status: 404 });
    })
  );
}

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function renderRoute(path: string, Component: React.ComponentType) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <AssessmentProvider>
          <Component />
        </AssessmentProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("console routes render without throwing", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });

  describe("against the real demo report", () => {
    for (const { path, name, Component } of ROUTES) {
      it(`${name} (${path})`, async () => {
        mockFetchWith(demoReport);
        renderRoute(path, Component);
        await waitFor(() => {
          expect(document.body.textContent).not.toBe("");
        });
      });
    }
  });

  describe("against a missing report (empty-state guard)", () => {
    // Every page's loading/error/empty-state branch is the first thing a
    // brand-new account (or a broken deploy) hits, so it deserves the same
    // coverage as the happy path rather than being assumed safe.
    for (const { path, name, Component } of ROUTES) {
      it(`${name} (${path}) shows an empty state instead of crashing`, async () => {
        mockFetchWith(null);
        renderRoute(path, Component);
        await waitFor(() => {
          expect(document.body.textContent).not.toBe("");
        });
        expect(screen.queryByText(/unexpected application error/i)).not.toBeInTheDocument();
      });
    }
  });
});
