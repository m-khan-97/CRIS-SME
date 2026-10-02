import type {
  AssessmentRun,
  AssessmentHistoryEntry,
  AwsEnvironment,
  AwsRoleValidation,
  AzureEnvironment,
  CrisReport,
  PublicExposureReport,
  PublicExposureHistoryEntry,
} from "./types";

// Empty by default so requests stay relative and rely on the Vite dev proxy
// (or a same-origin reverse proxy in production) to reach the local runner API.
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`GET ${path} failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = (await response.json()) as T & { message?: string };
  if (!response.ok) {
    throw new Error(payload.message ?? `POST ${path} failed with status ${response.status}`);
  }
  return payload;
}

export function getHealth() {
  return apiGet<{ status: string; service: string; message: string }>("/health");
}

export function getAzureEnvironment() {
  return apiGet<AzureEnvironment>("/api/environment/azure");
}

export function getAwsEnvironment() {
  return apiGet<AwsEnvironment>("/api/environment/aws");
}

export function validateAwsRole(payload: { role_arn: string; external_id?: string }) {
  return apiPost<AwsRoleValidation>("/api/environment/aws/validate-role", payload);
}

export function getLatestArtifacts() {
  return apiGet<{ artifacts: AssessmentRun["artifacts"] }>("/api/artifacts/latest");
}

export function startAzureAssessment(payload: {
  authorization_confirmed: boolean;
  organization_name?: string;
  subscription_id?: string;
  tenant_id?: string;
}) {
  return apiPost<AssessmentRun>("/api/assessments/azure", payload);
}

export function startAwsAssessment(payload: {
  authorization_confirmed: boolean;
  organization_name?: string;
  account_id?: string;
  role_arn?: string;
  external_id?: string;
}) {
  return apiPost<AssessmentRun>("/api/assessments/aws", payload);
}

export function getAssessmentRun(runId: string) {
  return apiGet<AssessmentRun>(`/api/assessments/${encodeURIComponent(runId)}`);
}

export function getAssessmentHistory() {
  return apiGet<{ assessments: AssessmentHistoryEntry[] }>("/api/assessment-history");
}

export function getAssessmentReport(reportId: string) {
  return apiGet<CrisReport>(`/api/assessment-reports/${encodeURIComponent(reportId)}`);
}

export function runPublicExposureAssessment(payload: {
  targets: string;
  authorization_confirmed: boolean;
  scan_common_ports?: boolean;
}) {
  return apiPost<PublicExposureReport>("/api/public-exposure", payload);
}

export function getPublicExposureHistory() {
  return apiGet<{ assessments: PublicExposureHistoryEntry[] }>("/api/public-exposure-history");
}

export function getPublicExposureReport(runId: string) {
  return apiGet<PublicExposureReport>(`/api/public-exposure-reports/${encodeURIComponent(runId)}`);
}

export async function getLatestReport(): Promise<CrisReport | null> {
  const response = await fetch(outputUrl("cris_sme_report.json"), {
    cache: "no-store",
  });
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`GET cris_sme_report.json failed with status ${response.status}`);
  }
  return (await response.json()) as CrisReport;
}

// In dev, BASE_URL is "/" and the Vite proxy forwards /outputs to the local
// runner. In static production builds, BASE_URL is "/console/" and report
// artifacts are copied alongside the bundle under console/outputs/.
export function outputUrl(filename: string): string {
  return `${API_BASE}${import.meta.env.BASE_URL}outputs/${filename}`;
}

// report_artifacts paths are repo-relative (e.g. "outputs/reports/cris_sme_report.sarif").
// The local runner serves files under outputs/reports/ at /outputs/, so strip that prefix.
export function artifactUrl(path: string): string {
  return `${API_BASE}/api/report-artifact?path=${encodeURIComponent(path)}`;
}
