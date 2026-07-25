import { useState } from "react";
import { ExternalLink, EyeOff, FileLock2, ShieldCheck } from "lucide-react";
import { artifactUrl } from "../api/client";
import { useAssessmentReport } from "../context/AssessmentContext";
import { Card, EmptyState, Spinner, StatCard } from "../components/ui";

const VERIFICATION_COLORS: Record<string, string> = {
  verified: "bg-status-good-bg text-status-good-text border-status-good-border",
  caveated: "bg-sev-medium-bg text-sev-medium-text border-sev-medium-border",
  unverified: "bg-surface-rail text-text-body border-border-strong",
};

const PROOF_COLORS: Record<string, string> = {
  strong: "bg-status-good-bg text-status-good-text border-status-good-border",
  caveated: "bg-sev-medium-bg text-sev-medium-text border-sev-medium-border",
  weak: "bg-sev-critical-bg text-sev-critical-text border-sev-critical-border",
};

export function DisclosureRoom() {
  const { data: report, isLoading, error } = useAssessmentReport();

  const data = (report ?? {}) as Record<string, any>;
  const disclosure = data.selective_disclosure as Record<string, any> | undefined;
  const rooms: Record<string, any>[] = disclosure?.rooms ?? [];
  const evidenceRoomHtml = data.report_artifacts?.selective_disclosure?.evidence_room_html as
    | string
    | undefined;

  const [profileId, setProfileId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-8 text-text-muted">
        <Spinner /> Loading disclosure rooms…
      </div>
    );
  }

  if (error) {
    return <div className="p-8"><EmptyState message={`Failed to load report: ${(error as Error).message}`} /></div>;
  }

  if (!report || rooms.length === 0) {
    return <div className="p-8"><EmptyState message="No selective disclosure rooms found in the latest report." /></div>;
  }

  const activeRoom = rooms.find((room) => room.profile_id === profileId) ?? rooms[0];

  return (
    <div className="flex flex-col gap-6 p-[24px_26px_28px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text-strong">Disclosure Room</h1>
          <p className="mt-1 text-sm text-text-muted">
            Audience-specific evidence packages — what is shared, what is redacted, and what is
            withheld, for each disclosure profile.
          </p>
        </div>
        {evidenceRoomHtml && (
          <a
            href={artifactUrl(evidenceRoomHtml)}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 rounded-md border border-border-strong bg-surface-subtle px-3 py-2 text-sm text-text-strong hover:border-violet-500 hover:text-text-strong"
          >
            <ExternalLink className="h-4 w-4" /> Open evidence room export
          </a>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3 lg:grid-cols-5">
        {rooms.map((room) => (
          <button
            key={room.profile_id}
            type="button"
            onClick={() => setProfileId(room.profile_id)}
            className={`rounded-xl border p-4 text-left transition-colors ${
              activeRoom.profile_id === room.profile_id
                ? "border-violet-500 bg-primary-tint"
                : "border-border-card bg-surface-card hover:border-border-strong"
            }`}
          >
            <div className="font-medium text-text-strong">{room.profile_name}</div>
            <div className="mt-1 text-xs text-text-muted">{room.audience}</div>
            <div className="mt-1 text-xs uppercase tracking-wide text-text-muted">
              {room.disclosure_level}
            </div>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <StatCard
          label="Included claims"
          value={activeRoom.included_claim_count ?? 0}
          icon={ShieldCheck}
          accent="text-primary bg-primary-tint"
        />
        <StatCard
          label="Shared evidence items"
          value={activeRoom.shared_evidence_count ?? 0}
          icon={FileLock2}
          accent="text-sev-low-text bg-sev-low-bg"
        />
        <StatCard
          label="Redactions"
          value={activeRoom.redaction_count ?? 0}
          icon={EyeOff}
          accent="text-sev-medium-text bg-sev-medium-bg"
        />
        <StatCard
          label="Withheld items"
          value={activeRoom.withheld_count ?? 0}
          icon={EyeOff}
          accent="text-sev-critical-text bg-sev-critical-bg"
        />
      </div>

      {activeRoom.deterministic_score_impact && (
        <div className="rounded-md border border-status-good-border bg-status-good-bg p-3 text-sm text-status-good-text">
          {activeRoom.deterministic_score_impact}
        </div>
      )}

      {activeRoom.integrity && (
        <Card title="Room integrity">
          <div className="grid grid-cols-1 gap-3 text-xs text-text-muted md:grid-cols-2">
            <div>
              <div className="mb-1 font-semibold uppercase tracking-wide text-text-muted">
                Room SHA-256
              </div>
              <div className="break-all font-mono">{activeRoom.integrity.room_sha256}</div>
            </div>
            <div>
              <div className="mb-1 font-semibold uppercase tracking-wide text-text-muted">
                RBOM report SHA-256
              </div>
              <div className="break-all font-mono">
                {activeRoom.integrity.rbom_report_sha256}
              </div>
            </div>
          </div>
        </Card>
      )}

      {(activeRoom.claims ?? []).length > 0 && (
        <Card title={`Claims (${activeRoom.claims.length})`}>
          <div className="overflow-hidden rounded-lg border border-border-card">
            <table className="w-full text-left text-sm">
              <thead className="bg-surface-subtle text-xs uppercase tracking-wide text-text-muted">
                <tr>
                  <th className="px-4 py-2">Claim</th>
                  <th className="px-4 py-2">Type</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2 text-right">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-row">
                {activeRoom.claims.slice(0, 50).map((claim: Record<string, any>) => {
                  const classes =
                    VERIFICATION_COLORS[claim.verification_status] ??
                    "bg-surface-rail text-text-body border-border-strong";
                  return (
                    <tr key={claim.claim_id}>
                      <td className="px-4 py-2 text-text-strong">{claim.statement}</td>
                      <td className="px-4 py-2 text-text-muted">{claim.claim_type}</td>
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
          {activeRoom.claims.length > 50 && (
            <p className="mt-2 text-xs text-text-muted">
              Showing first 50 of {activeRoom.claims.length} claims.
            </p>
          )}
        </Card>
      )}

      {(activeRoom.shared_evidence ?? []).length > 0 && (
        <Card title={`Shared evidence (${activeRoom.shared_evidence.length})`}>
          <div className="flex flex-col gap-2">
            {activeRoom.shared_evidence.slice(0, 30).map((item: Record<string, any>) => {
              const classes =
                PROOF_COLORS[item.proof_strength] ?? "bg-surface-rail text-text-body border-border-strong";
              return (
                <div
                  key={item.finding_id}
                  className="rounded-md border border-border-card p-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-sm text-text-strong">{item.title}</div>
                    <span className={`rounded-full border px-2 py-0.5 text-xs ${classes}`}>
                      {item.proof_strength}
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-text-muted">
                    {item.control_id} · {item.priority} · score {item.score}
                  </div>
                  {item.resource_scope && (
                    <div className="mt-1 text-xs text-text-muted">{item.resource_scope}</div>
                  )}
                  {(item.evidence ?? []).length > 0 && (
                    <ul className="mt-2 list-inside list-disc text-xs text-text-muted">
                      {item.evidence.map((line: string, index: number) => (
                        <li key={index}>{line}</li>
                      ))}
                    </ul>
                  )}
                </div>
              );
            })}
          </div>
          {activeRoom.shared_evidence.length > 30 && (
            <p className="mt-2 text-xs text-text-muted">
              Showing first 30 of {activeRoom.shared_evidence.length} shared evidence items.
            </p>
          )}
        </Card>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {(activeRoom.redactions ?? []).length > 0 && (
          <Card title={`Redactions (${activeRoom.redactions.length})`}>
            <div className="flex flex-col gap-2">
              {activeRoom.redactions.slice(0, 20).map((item: Record<string, any>) => (
                <div key={item.redaction_id} className="rounded-md border border-border-card p-3 text-xs">
                  <div className="font-mono text-text-muted">{item.field_path}</div>
                  <div className="mt-1 text-text-body">{item.reason}</div>
                  <div className="mt-1 text-text-muted capitalize">
                    {String(item.redaction_type).replaceAll("_", " ")}
                  </div>
                </div>
              ))}
            </div>
            {activeRoom.redactions.length > 20 && (
              <p className="mt-2 text-xs text-text-muted">
                Showing first 20 of {activeRoom.redactions.length} redactions.
              </p>
            )}
          </Card>
        )}

        {(activeRoom.withheld_items ?? []).length > 0 && (
          <Card title={`Withheld items (${activeRoom.withheld_items.length})`}>
            <div className="flex flex-col gap-2">
              {activeRoom.withheld_items.slice(0, 20).map((item: Record<string, any>) => (
                <div key={item.item_id} className="rounded-md border border-border-card p-3 text-xs">
                  <div className="text-text-muted">{item.source_section}</div>
                  <div className="mt-1 text-text-body">{item.reason}</div>
                  {item.replacement_summary && (
                    <div className="mt-1 text-text-muted">{item.replacement_summary}</div>
                  )}
                </div>
              ))}
            </div>
            {activeRoom.withheld_items.length > 20 && (
              <p className="mt-2 text-xs text-text-muted">
                Showing first 20 of {activeRoom.withheld_items.length} withheld items.
              </p>
            )}
          </Card>
        )}
      </div>
    </div>
  );
}
