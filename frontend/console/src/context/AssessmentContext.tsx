/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAssessmentHistory, getAssessmentReport, getLatestReport } from "../api/client";
import type { AssessmentHistoryEntry, CrisReport } from "../api/types";

const STORAGE_KEY = "cris-sme-selected-assessment";

interface AssessmentContextValue {
  assessments: AssessmentHistoryEntry[];
  selectedAssessment: AssessmentHistoryEntry | null;
  selectedReportId: string;
  setSelectedReportId: (reportId: string) => void;
  historyLoading: boolean;
  report: CrisReport | null | undefined;
  reportLoading: boolean;
  reportError: Error | null;
}

const AssessmentContext = createContext<AssessmentContextValue | null>(null);

export function AssessmentProvider({ children }: { children: ReactNode }) {
  const [requestedReportId, setRequestedReportId] = useState(
    () => window.localStorage.getItem(STORAGE_KEY) ?? ""
  );
  const history = useQuery({
    queryKey: ["assessment-history"],
    queryFn: getAssessmentHistory,
    retry: 1,
  });
  const assessments = useMemo(() => history.data?.assessments ?? [], [history.data]);
  const selectedAssessment =
    assessments.find((assessment) => assessment.report_id === requestedReportId) ??
    assessments[0] ??
    null;
  const selectedReportId = selectedAssessment?.report_id ?? "";

  useEffect(() => {
    if (selectedReportId && (!requestedReportId || selectedReportId === requestedReportId)) {
      window.localStorage.setItem(STORAGE_KEY, selectedReportId);
    }
  }, [requestedReportId, selectedReportId]);

  const selectedReport = useQuery({
    queryKey: ["assessment-report", selectedReportId || "latest"],
    queryFn: () => selectedReportId ? getAssessmentReport(selectedReportId) : getLatestReport(),
    enabled: !history.isLoading,
  });

  const value = useMemo<AssessmentContextValue>(() => ({
    assessments,
    selectedAssessment,
    selectedReportId,
    setSelectedReportId: setRequestedReportId,
    historyLoading: history.isLoading,
    report: selectedReport.data,
    reportLoading: history.isLoading || selectedReport.isLoading,
    reportError: selectedReport.error,
  }), [assessments, selectedAssessment, selectedReportId, history.isLoading, selectedReport.data, selectedReport.isLoading, selectedReport.error]);

  return <AssessmentContext.Provider value={value}>{children}</AssessmentContext.Provider>;
}

export function useAssessment() {
  const context = useContext(AssessmentContext);
  if (!context) throw new Error("useAssessment must be used within AssessmentProvider");
  return context;
}

export function useAssessmentReport() {
  const { report, reportLoading, reportError } = useAssessment();
  return { data: report, isLoading: reportLoading, error: reportError };
}
