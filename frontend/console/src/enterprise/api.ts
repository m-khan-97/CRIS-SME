import type { CrisReport } from "../api/types";

export type Role = "owner" | "admin" | "operator" | "analyst" | "auditor";
export interface Tenant { id: string; name: string; role: Role }
export interface Connection { id: string; name: string; provider: "aws" | "azure"; scope_id: string; enabled: boolean; verified_until: number; origin?: "cloud" | "historical_archive" }
export interface Artifact { id: string; name: string; sha256: string; size: number }
export interface HistoricalImport { source_run_id: string; source_organization_id: string; source_sha256: string; bundle_sha256: string; generated_at: string; imported_at: number; provider: "aws" | "azure"; scope_id: string; reported_source_type: string }
export interface Job { id: string; tenant_id: string; connection_id: string; status: "queued" | "running" | "cancelling" | "cancelled" | "completed" | "failed"; requested_at: number; attempt: number; error_code: string; artifacts?: Artifact[]; origin?: "live_scan" | "historical_import"; historical_import?: HistoricalImport | null; report_state?: "available" | "expired"; expired_at?: number | null }
export interface Member { subject: string; issuer: string; role: Role }
export interface Audit { id: string; subject: string; action: string; resource_id: string; created_at: number }
export interface ConnectionInput { name: string; provider: "aws" | "azure"; scope_id: string; role_arn?: string; tenant_id?: string; client_id?: string; client_secret?: string }
export class ApiError extends Error {
  status: number;
  constructor(status: number) { super(status === 401 ? "Your session has expired. Sign in again." : status === 403 ? "Your role does not permit this action." : status === 404 ? "This organization or resource is unavailable." : status === 410 ? "This report has expired under approved retention." : `Request failed (${status}).`); this.status = status; }
}

export class EnterpriseApi {
  private controller = new AbortController();
  private generation = 0;
  private token: () => string | undefined;
  private unauthorized: () => void;
  constructor(token: () => string | undefined, unauthorized: () => void) { this.token = token; this.unauthorized = unauthorized; }
  cancel() { this.generation++; this.controller.abort(); this.controller = new AbortController(); }
  private assertCurrent(generation: number) { if (generation !== this.generation) throw new DOMException("Scope changed", "AbortError"); }
  async request<T>(path: string, body?: unknown, method = "GET", key?: string): Promise<T> {
    const generation = this.generation;
    const response = await this.fetch(path, body, method, key);
    const value = await response.json() as T;
    this.assertCurrent(generation);
    return value;
  }
  private async fetch(path: string, body?: unknown, method = "GET", key?: string) {
    if (!path.startsWith("/api/v1/")) throw new Error("Enterprise endpoint required");
    const token = this.token();
    if (!token) { this.unauthorized(); throw new ApiError(401); }
    const response = await fetch(path, { method, body: body === undefined ? undefined : JSON.stringify(body),
      headers: { Authorization: `Bearer ${token}`, ...(body === undefined ? {} : { "Content-Type": "application/json" }), ...(key ? { "Idempotency-Key": key } : {}) },
      cache: "no-store", credentials: "omit", redirect: "error", signal: AbortSignal.any([this.controller.signal, AbortSignal.timeout(30_000)]) });
    if (response.status === 401) this.unauthorized();
    if (!response.ok) throw new ApiError(response.status);
    return response;
  }
  tenants() { return this.request<{ tenants: Tenant[] }>("/api/v1/tenants"); }
  path(tenant: string, suffix: string) { return `/api/v1/tenants/${encodeURIComponent(tenant)}/${suffix}`; }
  connections(tenant: string) { return this.request<{ connections: Connection[] }>(this.path(tenant, "connections")); }
  jobs(tenant: string) { return this.request<{ assessments: Job[] }>(this.path(tenant, "assessments")); }
  job(tenant: string, id: string) { return this.request<Job>(this.path(tenant, `assessments/${encodeURIComponent(id)}`)); }
  async artifact(tenant: string, artifact: Artifact) {
    const generation = this.generation;
    if (!Number.isSafeInteger(artifact.size) || artifact.size < 0 || artifact.size > 32 * 1024 * 1024) throw new Error("Artifact size check failed.");
    const response = await this.fetch(this.path(tenant, `artifacts/${encodeURIComponent(artifact.id)}`));
    const reader = response.body?.getReader();
    if (!reader) throw new Error("Artifact body unavailable.");
    const bytes = new Uint8Array(artifact.size);
    let offset = 0;
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        if (offset + value.byteLength > bytes.length) throw new Error("Artifact size check failed.");
        bytes.set(value, offset); offset += value.byteLength;
      }
    } finally { await reader.cancel(); reader.releaseLock(); }
    if (offset !== artifact.size) throw new Error("Artifact size check failed.");
    const digest = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), b => b.toString(16).padStart(2, "0")).join("");
    if (digest !== artifact.sha256) throw new Error("Artifact integrity check failed.");
    this.assertCurrent(generation);
    return bytes.buffer;
  }
  async report(tenant: string, artifact: Artifact): Promise<CrisReport> {
    const report = JSON.parse(new TextDecoder().decode(await this.artifact(tenant, artifact))) as CrisReport;
    if (!report || !Array.isArray(report.prioritized_risks) || !report.resource_context || !report.assessment_runner || typeof report.generated_at !== "string") throw new Error("Unsupported report structure.");
    // Filesystem paths embedded in reports are never download authority in enterprise mode.
    return { ...report, report_artifacts: undefined };
  }
}
