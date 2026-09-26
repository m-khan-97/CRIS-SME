import type { CrisReport, PrioritizedRisk } from "../../api/types";

export const baseReport: CrisReport = {
  report_schema_version: "test",
  generated_at: "2026-09-25T10:00:00Z",
  collector_mode: "mock",
  summary: {},
  overall_risk_score: 20,
  category_scores: {},
  prioritized_risks: [],
  resource_context: { context_model: "test", assets: [], relationships: [], evidence_records: [], finding_asset_links: [] },
  assessment_runner: {
    events: [],
    control_selection: { requested_control_ids: [], selected_control_ids: [], selected_domains: [], registry_filtered: false },
    evidence_sufficiency: { sufficiency_counts: {}, sufficient_ratio: 0, findings_requiring_attention: [] },
  },
};


export function finding(id: string, status?: string): PrioritizedRisk {
  return {
    finding_id: id, control_id: id, title: `Finding ${id}`,
    organization: "Fixture", organization_id: "fixture", provider: "mock",
    category: "IAM", severity: "high", score: 20, priority: "high",
    resource_scope: "fixture", evidence: [], asset_ids: [], evidence_ids: [],
    evidence_quality: {
      observation_class: "direct", sufficiency: "sufficient", direct_evidence_count: 1,
      inferred_evidence_count: 0, unavailable_evidence_count: 0, provider_support: "mock", missing_requirements: [],
    },
    remediation_summary: "Review fixture", remediation_cost_tier: null,
    lifecycle: status ? { status, recurrence_count: 2 } : undefined,
  };
}
