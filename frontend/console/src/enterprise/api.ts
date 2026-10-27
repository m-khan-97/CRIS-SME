import type { CrisReport } from "../api/types";

export type Role = "owner" | "admin" | "operator" | "analyst" | "auditor";
export interface Tenant { id: string; name: string; role: Role }
export interface Connection { id: string; name: string; provider: "aws" | "azure"; scope_id: string; enabled: boolean; verified_until: number }
export interface Artifact { id: string; name: string; sha256: string; size: number }
export interface Job { id: string; tenant_id: string; connection_id: string; status: "queued" | "running" | "cancelling" | "cancelled" | "completed" | "failed"; requested_at: number; attempt: number; error_code: string; artifacts?: Artifact[] }
export interface Member { subject: string; issuer: string; role: Role }
export interface Audit { id: string; subject: string; action: string; resource_id: string; created_at: number }
export interface ConnectionInput { name: string; provider: "aws" | "azure"; scope_id: string; role_arn?: string; tenant_id?: string; client_id?: string; client_secret?: string }
export class ApiError extends Error {
  status: number;
  constructor(status: number) { super(status === 401 ? "Your session has expired. Sign in again." : status === 403 ? "Your role does not permit this action." : status === 404 ? "This organization or resource is unavailable." : `Request failed (${status}).`); this.status = status; }
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
      cache: "no-store", credentials: "omit", redirect: "error", signal: this.controller.signal });
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
    const response = await this.fetch(this.path(tenant, `artifacts/${encodeURIComponent(artifact.id)}`));
    const bytes = await response.arrayBuffer();
    if (bytes.byteLength > 32 * 1024 * 1024 || bytes.byteLength !== artifact.size) throw new Error("Artifact size check failed.");
    const digest = Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), b => b.toString(16).padStart(2, "0")).join("");
    if (digest !== artifact.sha256) throw new Error("Artifact integrity check failed.");
    this.assertCurrent(generation);
    return bytes;
  }
  async report(tenant: string, artifact: Artifact): Promise<CrisReport> {
    const report = JSON.parse(new TextDecoder().decode(await this.artifact(tenant, artifact))) as CrisReport;
    if (!report || !Array.isArray(report.prioritized_risks) || !report.resource_context || !report.assessment_runner || typeof report.generated_at !== "string") throw new Error("Unsupported report structure.");
    // Filesystem paths embedded in reports are never download authority in enterprise mode.
    return { ...report, report_artifacts: undefined };
  }
}
