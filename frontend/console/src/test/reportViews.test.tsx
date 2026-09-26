import { baseReport, finding } from "./fixtures/report";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { CrisReport } from "../api/types";
import { useAssessmentReport } from "../context/AssessmentContext";
import { Governance } from "../pages/Governance";
import { NativeValidation } from "../pages/NativeValidation";
import { TrendHistory } from "../pages/TrendHistory";

vi.mock("../context/AssessmentContext", () => ({ useAssessmentReport: vi.fn() }));


function showReport(fields: Partial<CrisReport>) {
  vi.mocked(useAssessmentReport).mockReturnValue({ data: { ...baseReport, ...fields }, isLoading: false, error: null });
}


beforeEach(() => showReport({}));
afterEach(cleanup);

describe("populated assurance views", () => {
  it("renders native disagreement and nullable CRIS scores without inventing a score", () => {
    showReport({ native_validation: {
      framework: "Fixture provider", controls_mapped: 1,
      control_comparisons: [{ control_id: "IAM-001", comparison_status: "native_only", cris_active: false,
        native_active: true, cris_score: null, native_recommendation_count: 2, notes: "Needs review" }],
    } });
    render(<NativeValidation />);
    const row = screen.getByText("IAM-001").closest("tr")!;
    expect(within(row).getByText("native only")).toBeInTheDocument();
    expect(within(row).getByText("Needs review")).toBeInTheDocument();
    expect(within(row).getAllByRole("cell")[3]).toBeEmptyDOMElement();
  });

  it("filters lifecycle entries and excludes findings with missing lifecycle data", () => {
    showReport({ finding_lifecycle_summary: { status_counts: { open: 1, resolved: 1 } },
      prioritized_risks: [finding("open-control", "open"), finding("resolved-control", "resolved"), finding("legacy")] });
    render(<Governance />);
    expect(screen.queryByText("Finding legacy")).not.toBeInTheDocument();
    expect(screen.getByText("Finding resolved-control")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("combobox", { name: "Lifecycle status" }), { target: { value: "open" } });
    expect(screen.getByText("Finding open-control")).toBeInTheDocument();
    expect(screen.queryByText("Finding resolved-control")).not.toBeInTheDocument();
  });

  it("shows signed trend deltas and excludes unchanged controls", () => {
    showReport({ risk_drift_analysis: { run_count: 2, overall_risk: { direction: "improving", change_total: -7 } },
      history_comparison: { control_score_deltas: [
        { control_id: "changed", title: "Changed control", previous_score: 0, current_score: 12,
          delta: 12, previous_priority: null, current_priority: "high" },
        { control_id: "unchanged", title: "Unchanged control", previous_score: 12, current_score: 12,
          delta: 0, previous_priority: "high", current_priority: "high" },
      ] } });
    render(<TrendHistory />);
    expect(screen.getByText("improving")).toBeInTheDocument();
    expect(screen.getByText("-7")).toBeInTheDocument();
    expect(screen.getByText("+12")).toBeInTheDocument();
    expect(screen.queryByText("Unchanged control")).not.toBeInTheDocument();
  });
});

describe.each([
  ["governance", Governance, /No finding lifecycle data/],
  ["native validation", NativeValidation, /No native validation comparison/],
  ["trend", TrendHistory, /No trend or history data/],
] as const)("%s states", (_name, Component, emptyText) => {
  it("handles an older report without its optional section", () => {
    render(<Component />);
    expect(screen.getByText(emptyText)).toBeInTheDocument();
  });

  it("shows fetch errors instead of an empty success state", () => {
    vi.mocked(useAssessmentReport).mockReturnValue({ data: undefined, isLoading: false, error: new Error("fixture failure") });
    render(<Component />);
    expect(screen.getByText(/Failed to load report: fixture failure/)).toBeInTheDocument();
    expect(screen.queryByText(emptyText)).not.toBeInTheDocument();
  });
});
