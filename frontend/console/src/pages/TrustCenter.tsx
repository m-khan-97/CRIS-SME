import { useMemo, useState } from "react";
import { ShieldCheck, ShieldAlert, CheckCircle2, XCircle, FileCheck2 } from "lucide-react";
import { useAssessmentReport } from "../context/AssessmentContext";
import { Card, EmptyState, ProgressRing, Spinner, StatCard } from "../components/ui";

const CONCLUSION_COLORS: Record<string, string> = {
  supported: "bg-status-good-bg text-status-good-text border-status-good-border",
  caveated: "bg-sev-medium-bg text-sev-medium-text border-sev-medium-border",
  unsupported: "bg-sev-critical-bg text-sev-critical-text border-sev-critical-border",
};

const VERIFICATION_COLORS: Record<string, string> = {
  verified: "bg-status-good-bg text-status-good-text border-status-good-border",
  caveated: "bg-sev-medium-bg text-sev-medium-text border-sev-medium-border",
  unverified: "bg-surface-rail text-text-body border-border-strong",
};

function ConclusionBadge({ value }: { value: string }) {
  const classes = CONCLUSION_COLORS[value] ?? "bg-surface-rail text-text-body border-border-strong";
  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs font-medium capitalize ${classes}`}>
      {value}
    </span>
  );
}

function BoolFact({ label, value }: { label: string; value: boolean }) {
  return (
    <div className="flex items-center justify-between rounded-md border border-border-card px-3 py-2 text-sm">
      <span className="text-text-body">{label}</span>
      {value ? (
        <CheckCircle2 className="h-4 w-4 text-status-good-text" />
      ) : (
        <XCircle className="h-4 w-4 text-sev-critical-text" />
      )}
    </div>
  );
}

export function TrustCenter() {
  const { data: report, isLoading, error } = useAssessmentReport();

  const [claimFilter, setClaimFilter] = useState("all");

  const badge = report?.report_trust_badge;
  const assuranceCase = report?.assurance_case;
  const assessmentAssurance = report?.assessment_assurance;
  const narrative = report?.claim_bound_narrative;
  const claimPack = report?.claim_verification_pack;
  const rbom = report?.risk_bill_of_materials;
  const ledger = report?.decision_ledger;

  const claims = useMemo(() => claimPack?.claims ?? [], [claimPack]);
  const claimStatuses = useMemo(
    () => [...new Set(claims.map((claim) => String(claim.verification_status)))].sort(),
    [claims]
  );
  const filteredClaims = useMemo(
    () =>
      claims.filter((claim) =>
        claimFilter === "all" ? true : claim.verification_status === claimFilter
      ),
    [claims, claimFilter]
  );

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-8 text-text-muted">
        <Spinner /> Loading trust and assurance data…
      </div>
    );
  }

  if (error) {
    return <div className="p-8"><EmptyState message={`Failed to load report: ${(error as Error).message}`} /></div>;
  }

  if (!report || !badge) {
    return <div className="p-8"><EmptyState message="No trust badge data found in the latest report." /></div>;
  }

  return (
    <div className="flex flex-col gap-6 p-[24px_26px_28px]">
      <div>
        <h1 className="text-2xl font-semibold text-text-strong">Trust &amp; Assurance Center</h1>
        <p className="mt-1 text-sm text-text-muted">
          What CRIS-SME can prove about this assessment, and where the evidence is incomplete.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <div className="flex items-center gap-4">
            <ProgressRing value={badge.assurance_score ?? 0} label={`${badge.assurance_score ?? 0}`} />
            <div>
              <div className="flex items-center gap-2 font-medium text-text-strong">
                {(badge.level ?? "").toLowerCase() === "limited" ? (
                  <ShieldAlert className="h-4 w-4 text-sev-medium-text" />
                ) : (
                  <ShieldCheck className="h-4 w-4 text-status-good-text" />
                )}
                {badge.label ?? "Report Trust Badge"}
              </div>
              <div className="mt-1 text-xs uppercase tracking-wide text-text-muted">
                {badge.level ?? "unknown"} assurance level
              </div>
            </div>
          </div>
        </Card>
        <StatCard
          label="High-priority evidence gaps"
          value={badge.high_priority_evidence_gaps ?? 0}
          hint="Gaps flagged as high impact on assurance"
          icon={ShieldAlert}
          accent="text-sev-medium-text bg-sev-medium-bg"
        />
        <StatCard
          label="Assessment assurance"
          value={`${assessmentAssurance?.assurance_score ?? "—"}`}
          hint={`Level: ${assessmentAssurance?.assurance_level ?? "unknown"}`}
          icon={FileCheck2}
          accent="text-sev-low-text bg-sev-low-bg"
        />
        <StatCard
          label="Decision ledger events"
          value={ledger?.event_count ?? 0}
          hint={`Run ${ledger?.current_run_id ?? "—"}`}
          icon={ShieldCheck}
          accent="text-primary bg-primary-tint"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card title="Integrity facts">
          <div className="flex flex-col gap-2">
            <BoolFact label="Replay verified" value={!!badge.replay_verified} />
            <BoolFact label="Risk Bill of Materials present" value={!!badge.rbom_present} />
            <BoolFact
              label="Provider conformance passed"
              value={!!badge.provider_conformance_passed}
            />
          </div>
          {rbom && (
            <div className="mt-4 text-xs text-text-muted">
              <div className="mb-1 font-semibold uppercase tracking-wide text-text-muted">
                Canonical report SHA-256
              </div>
              <div className="break-all font-mono">{rbom.canonical_report_sha256}</div>
              <div className="mt-2">
                Engine {rbom.engine_version} · Scoring model {rbom.scoring_model} · Policy pack{" "}
                {rbom.policy_pack_version}
              </div>
            </div>
          )}
        </Card>

        {assessmentAssurance && (
          <Card title="Assessment assurance signals">
            <div className="flex flex-col gap-2 text-sm">
              {(assessmentAssurance.signals ?? []).map((signal) => (
                <div
                  key={signal.signal_id}
                  className="flex items-center justify-between gap-2 rounded-md border border-border-card px-3 py-2"
                >
                  <div className="min-w-0">
                    <div className="truncate text-text-strong">{signal.label}</div>
                    {signal.explanation && (
                      <div className="text-xs text-text-muted">{signal.explanation}</div>
                    )}
                  </div>
                  {signal.passed ? (
                    <span className="flex items-center gap-1 rounded-full border border-status-good-border bg-status-good-bg px-2 py-0.5 text-xs text-status-good-text">
                      <CheckCircle2 className="h-3 w-3" /> Passed
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 rounded-full border border-sev-medium-border bg-sev-medium-bg px-2 py-0.5 text-xs text-sev-medium-text">
                      <ShieldAlert className="h-3 w-3" /> Gap
                    </span>
                  )}
                </div>
              ))}
              {(assessmentAssurance.signals ?? []).length === 0 && (
                <p className="text-xs text-text-muted">No assurance signals recorded.</p>
              )}
            </div>
            {(assessmentAssurance.gaps ?? []).length > 0 && (
              <div className="mt-3">
                <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-muted">
                  Open gaps
                </div>
                <ul className="list-inside list-disc text-xs text-text-muted">
                  {assessmentAssurance.gaps.map((gap: string) => (
                    <li key={gap}>{gap}</li>
                  ))}
                </ul>
              </div>
            )}
          </Card>
        )}
      </div>

      {assuranceCase && (
        <Card title="Assurance case">
          <p className="mb-3 text-sm text-text-muted">
            Overall conclusion: <ConclusionBadge value={assuranceCase.overall_conclusion} /> ·{" "}
            {assuranceCase.supported_argument_count} supported,{" "}
            {assuranceCase.caveated_argument_count} caveated of {assuranceCase.argument_count}{" "}
            arguments
          </p>
          <div className="flex flex-col gap-3">
            {(assuranceCase.arguments ?? []).map((argument) => (
              <div key={argument.argument_id} className="rounded-md border border-border-card p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="text-sm text-text-strong">{argument.top_claim}</div>
                  <ConclusionBadge value={argument.conclusion} />
                </div>
                <p className="mt-2 text-xs text-text-muted">{argument.reasoning}</p>
                {(argument.caveats ?? []).length > 0 && (
                  <ul className="mt-2 list-inside list-disc text-xs text-sev-medium-text">
                    {argument.caveats.map((caveat: string) => (
                      <li key={caveat}>{caveat}</li>
                    ))}
                  </ul>
                )}
                <div className="mt-2 text-xs text-text-muted">
                  Confidence {Math.round((argument.confidence ?? 0) * 100)}%
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {narrative && (
        <Card title="Claim-bound narrative">
          <div className="flex flex-col gap-4">
            {(narrative.sections ?? []).map((section) => (
              <div key={section.section_id}>
                <div className="text-sm font-medium text-text-strong">{section.heading}</div>
                <p className="mt-1 text-sm text-text-muted">{section.text}</p>
                {(section.caveats ?? []).length > 0 && (
                  <ul className="mt-1 list-inside list-disc text-xs text-sev-medium-text">
                    {section.caveats.map((caveat: string) => (
                      <li key={caveat}>{caveat}</li>
                    ))}
                  </ul>
                )}
                <div className="mt-1 text-xs text-text-muted">
                  Cites {(section.cited_claim_ids ?? []).length} claim
                  {(section.cited_claim_ids ?? []).length === 1 ? "" : "s"}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {claimPack && (
        <Card title="Claim verification pack">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-text-muted">
              {claimPack.claim_count} claims · {claimPack.verified_claim_count} verified ·{" "}
              {claimPack.caveated_claim_count} caveated
            </p>
            <select
              className="rounded-md border border-border-strong bg-surface-card px-3 py-2 text-sm text-text-strong"
              value={claimFilter}
              onChange={(event) => setClaimFilter(event.target.value)}
            >
              <option value="all">All statuses</option>
              {claimStatuses.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </div>
          <div className="overflow-hidden rounded-lg border border-border-card">
            <table className="w-full text-left text-sm">
              <thead className="bg-surface-subtle text-xs uppercase tracking-wide text-text-muted">
                <tr>
                  <th className="px-4 py-2">Claim</th>
                  <th className="px-4 py-2">Type</th>
                  <th className="px-4 py-2">Audience</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2 text-right">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-row">
                {filteredClaims.slice(0, 50).map((claim) => {
                  const classes =
                    VERIFICATION_COLORS[claim.verification_status] ??
                    "bg-surface-rail text-text-body border-border-strong";
                  return (
                    <tr key={claim.claim_id}>
                      <td className="px-4 py-2 text-text-strong">{claim.statement}</td>
                      <td className="px-4 py-2 text-text-muted">{claim.claim_type}</td>
                      <td className="px-4 py-2 text-text-muted">{claim.audience}</td>
                      <td className="px-4 py-2">
                        <span className={`rounded-full border px-2 py-0.5 text-xs ${classes}`}>
                          {claim.verification_status}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-right text-text-body">
                        {Math.round((claim.confidence ?? 0) * 100)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
