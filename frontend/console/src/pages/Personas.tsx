import { useState } from "react";
import {
  Building2,
  ClipboardCheck,
  ShieldCheck as InsurerIcon,
  Network,
  UserCog,
} from "lucide-react";
import { Link } from "react-router-dom";
import { useAssessmentReport } from "../context/AssessmentContext";
import { Card, EmptyState, ProgressRing, SeverityBadge, Spinner } from "../components/ui";
import type { CrisReport, PrioritizedRisk } from "../api/types";

type PersonaId = "owner" | "technical" | "assessor" | "msp" | "insurer";

const PERSONAS: { id: PersonaId; label: string; description: string; icon: typeof Building2 }[] = [
  {
    id: "owner",
    label: "SME Owner",
    description: "Board-level risk posture, top priorities, and quick wins.",
    icon: Building2,
  },
  {
    id: "technical",
    label: "Technical Lead",
    description: "Active findings, attack paths, and remediation detail.",
    icon: UserCog,
  },
  {
    id: "assessor",
    label: "Assessor",
    description: "Assurance signals, evidence sufficiency, and trust badge.",
    icon: ClipboardCheck,
  },
  {
    id: "msp",
    label: "MSP",
    description: "Cross-tenant risk comparison and action plans.",
    icon: Network,
  },
  {
    id: "insurer",
    label: "Insurer",
    description: "Cyber insurance readiness and underwriting questions.",
    icon: InsurerIcon,
  },
];

const STATUS_COLORS: Record<string, string> = {
  met: "border-status-good-border bg-status-good-bg text-status-good-text",
  partial: "border-sev-medium-border bg-sev-medium-bg text-sev-medium-text",
  not_met: "border-sev-critical-border bg-sev-critical-bg text-sev-critical-text",
  unknown: "border-border-strong bg-surface-rail text-text-body",
};

export function Personas() {
  const { data: report, isLoading, error } = useAssessmentReport();

  const [active, setActive] = useState<PersonaId>("owner");

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-8 text-text-muted">
        <Spinner /> Loading persona briefings…
      </div>
    );
  }

  if (error) {
    return <div className="p-8"><EmptyState message={`Failed to load report: ${(error as Error).message}`} /></div>;
  }

  if (!report) {
    return <div className="p-8"><EmptyState message="No assessment report found yet." /></div>;
  }

  return (
    <div className="flex flex-col gap-6 p-[24px_26px_28px]">
      <div>
        <h1 className="text-2xl font-semibold text-text-strong">Persona Briefings</h1>
        <p className="mt-1 text-sm text-text-muted">
          The same assessment, framed for the people who rely on it.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {PERSONAS.map((persona) => {
          const Icon = persona.icon;
          const isActive = active === persona.id;
          return (
            <button
              key={persona.id}
              type="button"
              onClick={() => setActive(persona.id)}
              className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "border-violet-500/50 bg-primary-tint text-primary-on-tint"
                  : "border-border-card bg-surface-card text-text-body hover:bg-surface-subtle"
              }`}
            >
              <Icon className="h-4 w-4" />
              {persona.label}
            </button>
          );
        })}
      </div>

      <p className="text-sm text-text-muted">
        {PERSONAS.find((persona) => persona.id === active)?.description}
      </p>

      {active === "owner" && <OwnerBriefing report={report} />}
      {active === "technical" && <TechnicalBriefing report={report} />}
      {active === "assessor" && <AssessorBriefing report={report} />}
      {active === "msp" && <MspBriefing report={report} />}
      {active === "insurer" && <InsurerBriefing report={report} />}
    </div>
  );
}

function OwnerBriefing({ report }: { report: CrisReport }) {
  const executivePack = report.executive_pack ?? {};
  const topRisks = executivePack.top_risks ?? [];
  const quickWins = executivePack.quick_wins ?? {};
  const ceReadiness = executivePack.cyber_essentials_readiness ?? {};
  const insuranceReadiness = executivePack.insurance_readiness ?? {};

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card title="Overall risk">
          <div className="flex items-center gap-4">
            <ProgressRing value={100 - report.overall_risk_score} />
            <div>
              <div className="text-2xl font-semibold text-text-strong">
                {report.overall_risk_score.toFixed(1)} / 100
              </div>
              <div className="text-xs text-text-muted">Higher means more risk.</div>
            </div>
          </div>
        </Card>
        <Card title="Cyber Essentials readiness">
          <div className="flex items-center gap-4">
            <ProgressRing value={ceReadiness.overall_readiness_score ?? 0} />
            <div className="text-sm text-text-body">
              {ceReadiness.pillar_count ?? 0} pillars assessed
            </div>
          </div>
        </Card>
        <Card title="Cyber insurance readiness">
          <div className="flex items-center gap-4">
            <ProgressRing value={insuranceReadiness.readiness_score ?? 0} />
            <div className="text-sm text-text-body">
              {insuranceReadiness.met_count ?? 0} of {insuranceReadiness.question_count ?? 0} questions met
            </div>
          </div>
        </Card>
      </div>

      {executivePack.board_message && (
        <Card title="Board message">
          <p className="text-sm leading-relaxed text-text-body">{executivePack.board_message}</p>
        </Card>
      )}

      <Card title="Top priorities for the business">
        <div className="flex flex-col divide-y divide-border-row">
          {topRisks.slice(0, 5).map((risk) => (
            <div key={risk.control_id} className="flex items-center justify-between gap-4 py-3">
              <div>
                <div className="font-medium text-text-strong">{risk.title}</div>
                <div className="text-xs text-text-muted">
                  {risk.control_id} · {risk.organization}
                </div>
                {risk.remediation_summary && (
                  <div className="mt-1 text-xs text-text-muted">{risk.remediation_summary}</div>
                )}
              </div>
              <div className="text-sm font-semibold text-text-strong">{risk.score?.toFixed?.(1)}</div>
            </div>
          ))}
          {topRisks.length === 0 && (
            <p className="py-3 text-sm text-text-muted">No prioritized risks available.</p>
          )}
        </div>
      </Card>

      {quickWins.free_fix_count !== undefined && (
        <Card title="Quick wins">
          <p className="text-sm text-text-body">
            {quickWins.free_fix_count} free-to-fix issue
            {quickWins.free_fix_count === 1 ? "" : "s"} representing a combined risk score of{" "}
            {quickWins.free_fix_risk_total?.toFixed?.(1)}.
          </p>
          <Link
            to="/findings"
            className="mt-3 inline-block text-sm font-medium text-primary hover:text-primary-on-tint"
          >
            View findings →
          </Link>
        </Card>
      )}
    </div>
  );
}

function TechnicalBriefing({ report }: { report: CrisReport }) {
  const activeRisks = report.prioritized_risks.filter((risk) => {
    const status = (risk.lifecycle as { status?: string } | undefined)?.status;
    return status === undefined || !["suppressed", "resolved"].includes(status);
  });
  const urgent = activeRisks
    .filter((risk) => ["Immediate", "High"].includes(risk.priority))
    .sort((a, b) => b.score - a.score)
    .slice(0, 8);

  const costTierCounts = activeRisks.reduce<Record<string, number>>((acc, risk) => {
    const tier = risk.remediation_cost_tier ?? "unknown";
    acc[tier] = (acc[tier] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Remediation effort breakdown">
          <div className="flex flex-col gap-2">
            {Object.entries(costTierCounts).map(([tier, count]) => (
              <div key={tier} className="flex items-center justify-between text-sm">
                <span className="capitalize text-text-body">{tier}</span>
                <span className="text-text-muted">{count}</span>
              </div>
            ))}
          </div>
        </Card>
        <Card title="Explore further">
          <div className="flex flex-col gap-2 text-sm">
            <Link to="/findings" className="text-primary hover:text-primary-on-tint">
              Full findings table with sort/filter →
            </Link>
            <Link to="/attack-paths" className="text-primary hover:text-primary-on-tint">
              Attack paths and blast radius →
            </Link>
            <Link to="/resources" className="text-primary hover:text-primary-on-tint">
              Normalized resource inventory →
            </Link>
          </div>
        </Card>
      </div>

      <Card title="Highest-priority active findings">
        <div className="flex flex-col divide-y divide-border-row">
          {urgent.map((risk) => (
            <div key={risk.finding_id} className="flex items-center justify-between gap-4 py-3">
              <div className="min-w-0">
                <div className="truncate font-medium text-text-strong">{risk.title}</div>
                <div className="text-xs text-text-muted">
                  {risk.control_id} · {risk.resource_scope}
                </div>
                {risk.remediation_summary && (
                  <div className="mt-1 text-xs text-text-muted">{risk.remediation_summary}</div>
                )}
              </div>
              <div className="flex items-center gap-3">
                <SeverityBadge severity={risk.severity} />
                <div className="text-sm font-semibold text-text-strong">{risk.score.toFixed(1)}</div>
              </div>
            </div>
          ))}
          {urgent.length === 0 && (
            <p className="py-3 text-sm text-text-muted">No immediate or high-priority findings.</p>
          )}
        </div>
      </Card>
    </div>
  );
}

function AssessorBriefing({ report }: { report: CrisReport }) {
  const trustBadge = report.report_trust_badge ?? {};
  const assurance = report.assessment_assurance;
  const evidenceSufficiency = report.assessment_runner?.evidence_sufficiency;
  const signals = assurance?.signals ?? [];

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Report trust badge">
          <div className="flex items-center gap-3">
            <span className="rounded-full border border-border-strong px-2 py-0.5 text-xs uppercase tracking-wide text-text-body">
              {trustBadge.level ?? "unknown"}
            </span>
            <span className="text-sm text-text-body">{trustBadge.label}</span>
          </div>
          {trustBadge.statement && (
            <p className="mt-3 text-sm text-text-muted">{trustBadge.statement}</p>
          )}
          {Array.isArray(trustBadge.caveats) && trustBadge.caveats.length > 0 && (
            <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-text-muted">
              {trustBadge.caveats.map((caveat: string) => (
                <li key={caveat}>{caveat}</li>
              ))}
            </ul>
          )}
        </Card>
        <Card title="Assessment assurance">
          <div className="flex items-center gap-4">
            <ProgressRing value={assurance?.assurance_score ?? 0} />
            <div className="text-sm text-text-body capitalize">
              {assurance?.assurance_level ?? "unknown"} assurance
            </div>
          </div>
          {assurance?.risk_score_impact && (
            <p className="mt-3 text-xs text-text-muted">{assurance?.risk_score_impact}</p>
          )}
        </Card>
      </div>

      <Card title="Assurance signals">
        <div className="flex flex-col divide-y divide-border-row">
          {signals.map((signal) => (
            <div key={signal.signal_id} className="flex items-center justify-between gap-4 py-3">
              <div>
                <div className="font-medium text-text-strong">{signal.label}</div>
                <div className="text-xs text-text-muted">{signal.explanation}</div>
              </div>
              <span
                className={`rounded-full border px-2 py-0.5 text-xs ${
                  signal.passed
                    ? "border-status-good-border bg-status-good-bg text-status-good-text"
                    : "border-sev-critical-border bg-sev-critical-bg text-sev-critical-text"
                }`}
              >
                {signal.passed ? "Passed" : "Gap"}
              </span>
            </div>
          ))}
          {signals.length === 0 && (
            <p className="py-3 text-sm text-text-muted">No assurance signals available.</p>
          )}
        </div>
      </Card>

      <Card title="Evidence sufficiency">
        <div className="flex flex-col gap-2 text-sm text-text-body">
          <div>
            Sufficient evidence ratio:{" "}
            {evidenceSufficiency?.sufficient_ratio !== undefined
              ? `${Math.round(evidenceSufficiency?.sufficient_ratio * 100)}%`
              : "—"}
          </div>
          {evidenceSufficiency?.sufficiency_counts && (
            <div className="flex flex-wrap gap-3 text-xs text-text-muted">
              {Object.entries(evidenceSufficiency?.sufficiency_counts as Record<string, number>).map(
                ([key, value]) => (
                  <span key={key} className="rounded-full border border-border-strong px-2 py-0.5">
                    {key}: {value}
                  </span>
                )
              )}
            </div>
          )}
        </div>
        <Link
          to="/compliance"
          className="mt-3 inline-block text-sm font-medium text-primary hover:text-primary-on-tint"
        >
          Review compliance mappings →
        </Link>
      </Card>
    </div>
  );
}

function MspBriefing({ report }: { report: CrisReport }) {
  const organizations = report.organizations ?? [];

  const findingsByOrg = report.prioritized_risks.reduce<Record<string, PrioritizedRisk[]>>(
    (acc, risk) => {
      const key = risk.organization ?? "Unknown";
      if (!acc[key]) acc[key] = [];
      acc[key].push(risk);
      return acc;
    },
    {}
  );

  return (
    <div className="flex flex-col gap-4">
      <Card title="Tenant portfolio">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {organizations.map((org) => {
            const risks = findingsByOrg[org.organization_name] ?? [];
            const criticalCount = risks.filter((r) => r.severity.toLowerCase() === "critical").length;
            const highCount = risks.filter((r) => r.severity.toLowerCase() === "high").length;
            const avgScore = risks.length
              ? risks.reduce((sum, r) => sum + r.score, 0) / risks.length
              : 0;
            return (
              <div
                key={org.organization_id}
                className="rounded-lg border border-border-card bg-surface-card p-4"
              >
                <div className="font-medium text-text-strong">{org.organization_name}</div>
                <div className="text-xs text-text-muted">
                  {org.sector} · {org.provider}
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                  <span className="rounded-full border border-border-strong px-2 py-0.5 text-text-body">
                    {risks.length} findings
                  </span>
                  {criticalCount > 0 && (
                    <span className="rounded-full border border-sev-critical-border bg-sev-critical-bg px-2 py-0.5 text-sev-critical-text">
                      {criticalCount} critical
                    </span>
                  )}
                  {highCount > 0 && (
                    <span className="rounded-full border border-sev-high-border bg-sev-high-bg px-2 py-0.5 text-sev-high-text">
                      {highCount} high
                    </span>
                  )}
                  <span className="rounded-full border border-border-strong px-2 py-0.5 text-text-body">
                    avg score {avgScore.toFixed(0)}
                  </span>
                </div>
              </div>
            );
          })}
          {organizations.length === 0 && (
            <p className="text-sm text-text-muted">No organizations found in resource context.</p>
          )}
        </div>
      </Card>

      <Card title="Cross-tenant operations">
        <div className="flex flex-col gap-2 text-sm">
          <Link to="/attack-paths" className="text-primary hover:text-primary-on-tint">
            Inspect per-tenant attack paths →
          </Link>
          <Link to="/assessment" className="text-primary hover:text-primary-on-tint">
            Launch a new assessment for a managed tenant →
          </Link>
        </div>
      </Card>
    </div>
  );
}

function InsurerBriefing({ report }: { report: CrisReport }) {
  const insuranceEvidence = report.cyber_insurance_evidence ?? {};
  const readiness = insuranceEvidence.readiness_summary ?? {};
  const questions = insuranceEvidence.questions ?? [];

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Underwriting readiness">
          <div className="flex items-center gap-4">
            <ProgressRing value={readiness.readiness_score ?? 0} />
            <div className="text-sm text-text-body">
              {readiness.met_count ?? 0} met · {readiness.partial_count ?? 0} partial ·{" "}
              {readiness.not_met_count ?? 0} not met
            </div>
          </div>
        </Card>
        <Card title="Disclaimer">
          <p className="text-xs text-text-muted">
            {insuranceEvidence.disclaimer ??
              "This evidence pack supports underwriting discussions and is not a substitute for a formal proposal form."}
          </p>
        </Card>
      </div>

      <Card title="Underwriting questions">
        <div className="flex flex-col divide-y divide-border-row">
          {questions.map((question) => (
            <div key={question.question_id} className="flex items-start justify-between gap-4 py-3">
              <div className="min-w-0">
                <div className="text-sm font-medium text-text-strong">{question.question}</div>
                <div className="mt-1 text-xs text-text-muted">{question.evidence_statement}</div>
                {question.recommended_next_step && (
                  <div className="mt-1 text-xs text-text-muted">
                    Next step: {question.recommended_next_step}
                  </div>
                )}
              </div>
              <span
                className={`shrink-0 rounded-full border px-2 py-0.5 text-xs ${
                  STATUS_COLORS[question.status] ?? STATUS_COLORS.unknown
                }`}
              >
                {String(question.status).replaceAll("_", " ")}
              </span>
            </div>
          ))}
          {questions.length === 0 && (
            <p className="py-3 text-sm text-text-muted">No underwriting questions available.</p>
          )}
        </div>
      </Card>
    </div>
  );
}
