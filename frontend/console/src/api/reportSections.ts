// Fields consumed by the console. These are wire contracts, not runtime validators.
export interface Claim {
  claim_id: string;
  statement: string;
  claim_type: string;
  audience: string;
  verification_status: string;
  confidence: number;
}

export interface CeReadiness {
  overall_readiness_score?: number;
  pillar_count?: number;
  pillars: { pillar_id: string; pillar_name: string; readiness_score: number; status: string; controls_met: number; total_controls: number }[];
}

export interface CeReviewEntry {
  question_id: string;
  section: string;
  short_paraphrase: string;
  proposed_status: string;
  proposed_answer: string;
  answer_basis: string;
  caveat?: string | null;
  supporting_control_ids: string[];
}

export interface TrustBadge {
  assurance_score?: number;
  level?: string;
  label?: string;
  statement?: string;
  caveats?: string[];
  high_priority_evidence_gaps?: number;
  replay_verified?: boolean;
  rbom_present?: boolean;
  provider_conformance_passed?: boolean;
}

export interface AssessmentAssurance {
  risk_score_impact?: string;
  assurance_score?: number;
  assurance_level?: string;
  signals: { signal_id: string; label: string; explanation: string; passed: boolean }[];
  gaps: string[];
}

export interface ReportAction {
  control_id: string;
  title: string;
  organization: string;
  category: string;
  priority: string;
  remediation_summary?: string;
  remediation_cost_tier: string | null;
  remediation_value_score?: number;
  action_rationale?: string;
}

export interface BudgetProfile {
  profile_id: string;
  label: string;
  description: string;
  max_monthly_cost_gbp: number;
  total_recommended: number;
  average_value_score: number;
  recommended_actions: ReportAction[];
}

export interface SimulationScenario {
  scenario_id: string;
  label: string;
  basis: string;
  current_overall_risk_score: number;
  simulated_overall_risk_score: number;
  selected_action_count: number;
  expected_risk_reduction: number;
  expected_risk_reduction_percent: number;
  current_non_compliant_findings: number;
  simulated_non_compliant_findings: number;
  category_score_deltas: Record<string, number>;
}

export interface ReportArtifacts {
  [key: string]: unknown;
  csv_exports?: Record<string, string>;
  remediation_script_pack?: Record<string, string>;
  selective_disclosure?: { evidence_room_html?: string };
}

export interface DisclosureProfile {
  profile_id: string;
  profile_name: string;
  audience: string;
  disclosure_level: string;
  included_claim_count: number;
  shared_evidence_count: number;
  redaction_count: number;
  withheld_count: number;
  deterministic_score_impact?: string;
  integrity?: { room_sha256?: string; rbom_report_sha256?: string };
  claims: Claim[];
  shared_evidence: { finding_id: string; title: string; proof_strength: string; control_id: string; priority: string; score: number; resource_scope?: string; evidence: string[] }[];
  redactions: { redaction_id: string; field_path: string; reason: string; redaction_type: string }[];
  withheld_items: { item_id: string; source_section: string; reason: string; replacement_summary?: string }[];
}

export interface InsuranceReadiness {
  readiness_score?: number;
  met_count?: number;
  partial_count?: number;
  not_met_count?: number;
  question_count?: number;
}

export interface OrganizationSummary {
  organization_id: string;
  organization_name: string;
  sector?: string;
  provider: string;
  collection_details?: Record<string, unknown>;
}

export interface ReportSections {
  report_artifacts?: ReportArtifacts;
  organizations?: OrganizationSummary[];
  assessment_summary?: {
    risk_band?: string;
    finding_summary?: { severity_counts?: Record<string, number> };
    assurance_summary?: { assessment_assurance_score?: number; assessment_assurance_level?: string };
  };
  run_metadata?: { generated_at?: string; run_id?: string; policy_pack?: { controls_total?: number } };
  report_trust_badge?: TrustBadge;
  assessment_assurance?: AssessmentAssurance;
  risk_bill_of_materials?: { canonical_report_sha256?: string; engine_version?: string; scoring_model?: string; policy_pack_version?: string };
  decision_ledger?: { event_count?: number; current_run_id?: string };
  assurance_case?: {
    overall_conclusion: string; supported_argument_count: number; caveated_argument_count: number; argument_count: number;
    arguments: { argument_id: string; top_claim: string; conclusion: string; reasoning: string; confidence: number; caveats: string[] }[];
  };
  claim_bound_narrative?: { sections: { section_id: string; heading: string; text: string; caveats: string[]; cited_claim_ids: string[] }[] };
  claim_verification_pack?: { claims: Claim[]; claim_count: number; verified_claim_count: number; caveated_claim_count: number };
  selective_disclosure?: { rooms: DisclosureProfile[] };
  budget_aware_remediation?: { budget_profiles: BudgetProfile[] };
  action_plan_30_day?: { phases: { phase_id: string; label: string; time_window: string; actions: ReportAction[] }[] };
  remediation_simulation?: { scenarios: SimulationScenario[] };
  decision_provenance_graph?: { node_count?: number; edge_count?: number; path_count?: number; node_type_counts?: Record<string, number>; edge_type_counts?: Record<string, number> };
  decision_review_queue?: {
    item_count: number; priority_counts: Record<string, number>;
    items: { review_id: string; priority: string; title: string; control_id?: string | null; provider?: string | null; decision_type: string; recommended_decision: string }[];
  };
  control_drift_attribution?: { primary_attribution?: string; overall_risk_delta?: number };
  evidence_gap_backlog?: {
    item_count: number; high_priority_count: number;
    items: { gap_id: string; domain: string; priority: string; title: string; control_id?: string | null; provider?: string | null; evidence_gap: string; recommended_action: string }[];
  };
  confidence_calibration?: { average_calibrated_confidence?: number; controls_with_calibration?: number; method_summary?: string; status_counts?: Record<string, number> };
  collector_coverage?: { provider: string; collection_mode: string; evidence_quality_note?: string; observed_domains: string[]; partially_observed_domains: string[]; unavailable_domains: string[] }[];
  provider_evidence_contracts?: { contract_count: number; provider_count: number; support_status_counts: Record<string, number> };
  cyber_essentials_readiness?: CeReadiness;
  cyber_essentials_self_assessment?: { certification_boundary?: string; question_count?: number; technical_question_count?: number; coverage_summary?: Record<string, number> };
  cyber_essentials_evaluation_metrics?: { question_count: number; observability_metrics?: Record<string, number> };
  cyber_essentials_review_console?: { console_schema_version?: string; entries: CeReviewEntry[]; review_policy?: { allowed_review_states?: string[]; default_state?: string; score_boundary?: string } };
  executive_pack?: {
    board_message?: string;
    top_risks?: { control_id: string; title: string; organization: string; remediation_summary?: string; score?: number }[];
    quick_wins?: { free_fix_count?: number; free_fix_risk_total?: number };
    cyber_essentials_readiness?: Partial<CeReadiness>;
    insurance_readiness?: InsuranceReadiness;
  };
  cyber_insurance_evidence?: {
    disclaimer?: string;
    readiness_summary?: InsuranceReadiness;
    questions?: { question_id: string; question: string; evidence_statement: string; recommended_next_step?: string; status: string }[];
  };
}
