import { useState } from "react";
import { Wrench, TrendingDown, Wallet, FileDown } from "lucide-react";
import { artifactUrl } from "../api/client";
import { useAssessmentReport } from "../context/AssessmentContext";
import { Card, EmptyState, SeverityBadge, Spinner, StatCard } from "../components/ui";

const COST_TIER_LABELS: Record<string, string> = {
  free: "Free",
  low: "Low cost",
  medium: "Medium cost",
  high: "High cost",
};

type TabId = "budget" | "plan" | "simulation";

export function Remediation() {
  const { data: report, isLoading, error } = useAssessmentReport();

  const [tab, setTab] = useState<TabId>("budget");

  const data = (report ?? {}) as Record<string, any>;
  const budgetProfiles: Record<string, any>[] = data.budget_aware_remediation?.budget_profiles ?? [];
  const phases: Record<string, any>[] = data.action_plan_30_day?.phases ?? [];
  const scenarios: Record<string, any>[] = data.remediation_simulation?.scenarios ?? [];
  const scriptPack = data.report_artifacts?.remediation_script_pack as
    | Record<string, string>
    | undefined;

  const [selectedProfile, setSelectedProfile] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-8 text-text-muted">
        <Spinner /> Loading remediation guidance…
      </div>
    );
  }

  if (error) {
    return <div className="p-8"><EmptyState message={`Failed to load report: ${(error as Error).message}`} /></div>;
  }

  if (!report) {
    return <div className="p-8"><EmptyState message="No assessment report found yet." /></div>;
  }

  const activeProfile =
    budgetProfiles.find((profile) => profile.profile_id === selectedProfile) ?? budgetProfiles[0];

  return (
    <div className="flex flex-col gap-6 p-[24px_26px_28px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text-strong">Remediation</h1>
          <p className="mt-1 text-sm text-text-muted">
            Affordability-aware action plans and what-if risk reduction. CRIS-SME never
            executes these changes — review and apply them yourself.
          </p>
        </div>
        {scriptPack && (
          <a
            href={artifactUrl(Object.values(scriptPack)[0] ?? "")}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 rounded-md border border-border-strong bg-surface-subtle px-3 py-2 text-sm text-text-strong hover:border-violet-500 hover:text-text-strong"
          >
            <FileDown className="h-4 w-4" /> Remediation script pack
          </a>
        )}
      </div>

      <div className="flex gap-2 border-b border-border-card">
        {[
          { id: "budget" as const, label: "Budget profiles", icon: Wallet },
          { id: "plan" as const, label: "30-day action plan", icon: Wrench },
          { id: "simulation" as const, label: "What-if simulations", icon: TrendingDown },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`flex items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
              tab === id
                ? "border-violet-500 text-text-strong"
                : "border-transparent text-text-muted hover:text-text-strong"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {tab === "budget" && (
        <>
          {budgetProfiles.length === 0 ? (
            <EmptyState message="No budget-aware remediation profiles available." />
          ) : (
            <>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                {budgetProfiles.map((profile) => (
                  <button
                    key={profile.profile_id}
                    type="button"
                    onClick={() => setSelectedProfile(profile.profile_id)}
                    className={`rounded-xl border p-4 text-left transition-colors ${
                      activeProfile?.profile_id === profile.profile_id
                        ? "border-violet-500 bg-primary-tint"
                        : "border-border-card bg-surface-card hover:border-border-strong"
                    }`}
                  >
                    <div className="font-medium text-text-strong">{profile.label}</div>
                    <p className="mt-1 text-xs text-text-muted">{profile.description}</p>
                    <div className="mt-3 flex flex-wrap gap-3 text-xs text-text-muted">
                      <span>
                        Budget:{" "}
                        {profile.max_monthly_cost_gbp === 0
                          ? "£0/mo"
                          : `up to £${profile.max_monthly_cost_gbp}/mo`}
                      </span>
                      <span>{profile.total_recommended} actions</span>
                      <span>Avg value score {profile.average_value_score}</span>
                    </div>
                  </button>
                ))}
              </div>

              {activeProfile && (
                <Card title={`Recommended actions — ${activeProfile.label}`}>
                  <div className="flex flex-col gap-2">
                    {(activeProfile.recommended_actions ?? []).map(
                      (action: Record<string, any>, index: number) => (
                        <div
                          key={`${action.control_id}-${index}`}
                          className="flex items-center justify-between gap-3 rounded-md border border-border-card px-3 py-2"
                        >
                          <div className="min-w-0">
                            <div className="text-sm text-text-strong">{action.title}</div>
                            <div className="mt-0.5 text-xs text-text-muted">
                              {action.control_id} · {action.organization} · {action.category}
                            </div>
                            {action.remediation_summary && (
                              <p className="mt-1 text-xs text-text-muted">
                                {action.remediation_summary}
                              </p>
                            )}
                          </div>
                          <div className="flex flex-col items-end gap-1 text-xs">
                            <span className="rounded-full border border-border-strong px-2 py-0.5 text-text-body">
                              {COST_TIER_LABELS[action.remediation_cost_tier] ??
                                action.remediation_cost_tier ??
                                "unknown cost"}
                            </span>
                            <span className="text-text-muted">
                              Value score {action.remediation_value_score}
                            </span>
                          </div>
                        </div>
                      )
                    )}
                  </div>
                </Card>
              )}
            </>
          )}
        </>
      )}

      {tab === "plan" && (
        <>
          {phases.length === 0 ? (
            <EmptyState message="No 30-day action plan available." />
          ) : (
            <div className="flex flex-col gap-4">
              {phases.map((phase) => (
                <Card key={phase.phase_id} title={`${phase.label} (${phase.time_window})`}>
                  <div className="flex flex-col gap-2">
                    {(phase.actions ?? []).map((action: Record<string, any>, index: number) => (
                      <div
                        key={`${action.control_id}-${index}`}
                        className="flex items-center justify-between gap-3 rounded-md border border-border-card px-3 py-2"
                      >
                        <div className="min-w-0">
                          <div className="text-sm text-text-strong">{action.title}</div>
                          <div className="mt-0.5 text-xs text-text-muted">
                            {action.control_id} · {action.organization} · {action.category}
                          </div>
                          {action.action_rationale && (
                            <p className="mt-1 text-xs text-text-muted">{action.action_rationale}</p>
                          )}
                        </div>
                        <div className="flex flex-col items-end gap-1 text-xs">
                          <SeverityBadge severity={action.priority} />
                          <span className="text-text-muted">
                            {COST_TIER_LABELS[action.remediation_cost_tier] ??
                              action.remediation_cost_tier ??
                              "unknown cost"}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </>
      )}

      {tab === "simulation" && (
        <>
          {scenarios.length === 0 ? (
            <EmptyState message="No remediation simulation scenarios available." />
          ) : (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              {scenarios.map((scenario) => (
                <Card key={scenario.scenario_id} title={scenario.label}>
                  <p className="mb-3 text-xs text-text-muted">{scenario.basis}</p>
                  <div className="grid grid-cols-2 gap-3">
                    <StatCard
                      label="Current score"
                      value={scenario.current_overall_risk_score}
                      icon={TrendingDown}
                      accent="text-text-body bg-surface-rail"
                    />
                    <StatCard
                      label="Simulated score"
                      value={scenario.simulated_overall_risk_score}
                      hint={`${scenario.selected_action_count} actions applied`}
                      icon={TrendingDown}
                      accent="text-status-good-text bg-status-good-bg"
                    />
                  </div>
                  <div className="mt-3 text-sm text-text-body">
                    Expected reduction: {scenario.expected_risk_reduction} pts (
                    {scenario.expected_risk_reduction_percent}%)
                  </div>
                  <div className="mt-1 text-xs text-text-muted">
                    Non-compliant findings: {scenario.current_non_compliant_findings} →{" "}
                    {scenario.simulated_non_compliant_findings}
                  </div>
                  {scenario.category_score_deltas && (
                    <div className="mt-3">
                      <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">
                        Category score deltas
                      </div>
                      <div className="flex flex-col gap-1 text-xs">
                        {Object.entries(scenario.category_score_deltas)
                          .filter(([, delta]) => (delta as number) !== 0)
                          .map(([category, delta]) => (
                            <div key={category} className="flex justify-between text-text-muted">
                              <span>{category}</span>
                              <span className="text-status-good-text">-{delta as number}</span>
                            </div>
                          ))}
                      </div>
                    </div>
                  )}
                </Card>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
