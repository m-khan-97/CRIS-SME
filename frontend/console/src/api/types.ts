export interface ArtifactInfo {
  path: string;
  exists: boolean;
  updated_at: string;
}

export type ArtifactMap = Record<string, ArtifactInfo>;

export interface AzureAccount {
  subscription_id: string;
  subscription_name: string;
  tenant_id: string;
  user?: Record<string, unknown>;
}

export interface AzureEnvironment {
  status: string;
  azure_cli_available: boolean;
  authenticated: boolean;
  account: AzureAccount | null;
  error?: string;
  message: string;
}

export interface AwsAccount {
  account_id: string;
  organization_name: string;
  arn: string;
}

export interface AwsEnvironment {
  status: string;
  credentials_available: boolean;
  authenticated: boolean;
  account: AwsAccount | null;
  error?: string;
  message: string;
}

export interface AwsRoleValidation {
  status: string;
  verified: boolean;
  account_id: string | null;
  arn: string | null;
  message: string;
}

export interface RunnerEvent {
  sequence: number;
  phase: string;
  status: "started" | "completed";
  message: string;
  generated_at: string;
  detail: Record<string, unknown>;
}

export interface AssessmentRun {
  run_id: string;
  collector: string;
  status: "queued" | "running" | "completed" | "failed";
  requested_at: string;
  started_at: string;
  completed_at: string;
  authorization_confirmed: boolean;
  subscription_id: string;
  tenant_id: string;
  account_id: string;
  role_arn: string;
  output_dir: string;
  figure_dir: string;
  returncode: number | null;
  stdout_tail: string;
  stderr_tail: string;
  error: string;
  runner_events: RunnerEvent[];
  artifacts: ArtifactMap;
}

export interface AssessmentHistoryEntry {
  report_id: string;
  run_id: string;
  organization_id: string;
  organization_name: string;
  provider: string;
  generated_at: string;
  overall_risk_score: number | null;
  finding_count: number;
  collector_mode: string;
}

export interface ScoreBreakdown {
  observed_confidence: number;
  calibrated_confidence: number;
  calibration_status: string;
  [key: string]: unknown;
}

export interface PrioritizedRisk {
  finding_id: string;
  control_id: string;
  title: string;
  organization: string;
  organization_id: string;
  provider: string;
  category: string;
  severity: string;
  score: number;
  priority: string;
  resource_scope: string;
  evidence: string[];
  asset_ids: string[];
  evidence_ids: string[];
  evidence_quality: {
    observation_class: string;
    sufficiency: string;
    direct_evidence_count: number;
    inferred_evidence_count: number;
    unavailable_evidence_count: number;
    provider_support: string;
    missing_requirements: string[];
  };
  remediation_summary: string;
  remediation_cost_tier: string | null;
  [key: string]: unknown;
}

export interface CrisAsset {
  asset_id: string;
  provider: string;
  asset_type: string;
  name: string;
  scope: string;
  criticality: string;
  internet_exposed: boolean;
  tags: Record<string, string>;
}

export interface AssetRelationship {
  relationship_id: string;
  from_asset_id: string;
  to_asset_id: string;
  relationship_type: string;
  confidence: number;
}

export interface ResourceContext {
  context_model: string;
  assets: CrisAsset[];
  relationships: AssetRelationship[];
  evidence_records: unknown[];
  finding_asset_links: unknown[];
}

export interface AssessmentRunnerOverview {
  events: RunnerEvent[];
  control_selection: {
    requested_control_ids: string[];
    selected_control_ids: string[];
    selected_domains: string[];
    registry_filtered: boolean;
  };
  evidence_sufficiency: {
    sufficiency_counts: Record<string, number>;
    sufficient_ratio: number;
    findings_requiring_attention: string[];
  };
}

export interface ComplianceResult {
  frameworks_covered: string[];
  control_reference_counts: Record<string, number>;
  findings_by_framework: Record<string, number>;
  mapped_findings: Record<string, unknown>[];
  uk_sme_profile?: Record<string, unknown> | null;
}

export interface CrisReport {
  report_schema_version: string;
  generated_at: string;
  collector_mode: string;
  summary: Record<string, unknown>;
  overall_risk_score: number;
  category_scores: Record<string, number>;
  prioritized_risks: PrioritizedRisk[];
  resource_context: ResourceContext;
  assessment_runner: AssessmentRunnerOverview;
  compliance?: ComplianceResult;
  executive_summary?: string;
  [key: string]: unknown;
}

export interface PublicExposureReport {
  assessment_type: string;
  generated_at: string;
  scope_note: string;
  summary: {
    target_count: number;
    finding_count: number;
    high_finding_count?: number;
    https_available_count?: number;
    resolved_target_count?: number;
  };
  targets: unknown[];
  findings: unknown[];
  status?: string;
  message?: string;
  artifacts?: ArtifactMap;
}
