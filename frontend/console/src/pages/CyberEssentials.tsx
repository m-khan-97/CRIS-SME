import { useEffect, useMemo, useState } from "react";
import { ClipboardCheck, Download, ShieldCheck } from "lucide-react";
import { useAssessmentReport } from "../context/AssessmentContext";
import { Card, Drawer, EmptyState, ProgressRing, Spinner, StatCard } from "../components/ui";

const LEDGER_STORAGE_KEY = "cris_sme_ce_human_review_ledger_v1";
const PAGE_SIZE = 15;

const STATE_LABELS: Record<string, string> = {
  pending: "Pending",
  accepted: "Accepted",
  overridden: "Overridden",
  needs_evidence: "Needs evidence",
};

const STATE_COLORS: Record<string, string> = {
  pending: "bg-surface-rail text-text-body border-border-strong",
  accepted: "bg-status-good-bg text-status-good-text border-status-good-border",
  overridden: "bg-sev-medium-bg text-sev-medium-text border-sev-medium-border",
  needs_evidence: "bg-sev-low-bg text-sev-low-text border-sev-low-border",
};

interface LedgerEntry {
  state: string;
  reviewer: string;
  reviewer_note: string;
  override_reason: string;
  reviewed_at: string;
}

type Ledger = Record<string, LedgerEntry>;

function loadLedger(): Ledger {
  try {
    const raw = localStorage.getItem(LEDGER_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Ledger) : {};
  } catch {
    return {};
  }
}

async function sha256Hex(text: string): Promise<string> {
  const buffer = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buffer)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function download(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

type TabId = "readiness" | "review";

export function CyberEssentials() {
  const { data: report, isLoading, error } = useAssessmentReport();

  const [tab, setTab] = useState<TabId>("readiness");
  const [ledger, setLedger] = useState<Ledger>(() => loadLedger());
  const [sectionFilter, setSectionFilter] = useState("all");
  const [stateFilter, setStateFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [activeEntry, setActiveEntry] = useState<Record<string, any> | null>(null);

  useEffect(() => {
    localStorage.setItem(LEDGER_STORAGE_KEY, JSON.stringify(ledger));
  }, [ledger]);

  const data = (report ?? {}) as Record<string, any>;
  const readiness = data.cyber_essentials_readiness as Record<string, any> | undefined;
  const selfAssessment = data.cyber_essentials_self_assessment as Record<string, any> | undefined;
  const evaluation = data.cyber_essentials_evaluation_metrics as Record<string, any> | undefined;
  const reviewConsole = data.cyber_essentials_review_console as Record<string, any> | undefined;

  const entries: Record<string, any>[] = reviewConsole?.entries ?? [];
  const allowedStates: string[] = reviewConsole?.review_policy?.allowed_review_states ?? [
    "pending",
    "accepted",
    "overridden",
    "needs_evidence",
  ];
  const defaultState: string = reviewConsole?.review_policy?.default_state ?? "pending";

  const sections = useMemo(
    () => [...new Set(entries.map((entry) => String(entry.section)))].sort(),
    [entries]
  );

  const decisionFor = (questionId: string) =>
    ledger[questionId]?.state ?? defaultState;

  const filteredEntries = useMemo(
    () =>
      entries.filter((entry) => {
        if (sectionFilter !== "all" && entry.section !== sectionFilter) return false;
        if (stateFilter !== "all" && decisionFor(entry.question_id) !== stateFilter) return false;
        return true;
      }),
    [entries, sectionFilter, stateFilter, ledger]
  );

  const totalPages = Math.max(1, Math.ceil(filteredEntries.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const paged = filteredEntries.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const reviewedCount = Object.values(ledger).filter((entry) => entry.state !== "pending").length;

  const setDecision = (questionId: string, patch: Partial<LedgerEntry>) => {
    setLedger((prev) => ({
      ...prev,
      [questionId]: {
        state: prev[questionId]?.state ?? defaultState,
        reviewer: prev[questionId]?.reviewer ?? "",
        reviewer_note: prev[questionId]?.reviewer_note ?? "",
        override_reason: prev[questionId]?.override_reason ?? "",
        reviewed_at: new Date().toISOString(),
        ...patch,
      },
    }));
  };

  const exportLedger = async (format: "json" | "csv") => {
    const records = entries.map((entry) => {
      const decision = ledger[entry.question_id];
      return {
        question_id: entry.question_id,
        section: entry.section,
        proposed_status: entry.proposed_status,
        proposed_answer: entry.proposed_answer,
        review_state: decision?.state ?? defaultState,
        reviewer: decision?.reviewer ?? "",
        reviewer_note: decision?.reviewer_note ?? "",
        override_reason: decision?.override_reason ?? "",
        reviewed_at: decision?.reviewed_at ?? "",
      };
    });

    if (format === "json") {
      const payload = {
        ledger_name: "CRIS-SME CE Human Review Ledger",
        source_console_schema_version: reviewConsole?.console_schema_version,
        question_count: records.length,
        generated_at: new Date().toISOString(),
        records,
      };
      const body = JSON.stringify(payload);
      const canonical_ledger_sha256 = await sha256Hex(body);
      download(
        "cris_sme_ce_human_review_ledger.json",
        JSON.stringify({ ...payload, canonical_ledger_sha256 }, null, 2),
        "application/json"
      );
    } else {
      const header = Object.keys(records[0] ?? {}).join(",");
      const rows = records.map((record) =>
        Object.values(record)
          .map((value) => `"${String(value).replaceAll('"', '""')}"`)
          .join(",")
      );
      download("cris_sme_ce_human_review_ledger.csv", [header, ...rows].join("\n"), "text/csv");
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-8 text-text-muted">
        <Spinner /> Loading Cyber Essentials data…
      </div>
    );
  }

  if (error) {
    return <div className="p-8"><EmptyState message={`Failed to load report: ${(error as Error).message}`} /></div>;
  }

  if (!report || !readiness) {
    return <div className="p-8"><EmptyState message="No Cyber Essentials data found in the latest report." /></div>;
  }

  return (
    <div className="flex flex-col gap-6 p-[24px_26px_28px]">
      <div>
        <h1 className="text-2xl font-semibold text-text-strong">Cyber Essentials</h1>
        <p className="mt-1 text-sm text-text-muted">
          {selfAssessment?.certification_boundary ??
            "This pack pre-populates candidate Cyber Essentials answers from existing CRIS-SME findings for human review. It does not certify compliance."}
        </p>
      </div>

      <div className="flex gap-2 border-b border-border-card">
        {[
          { id: "readiness" as const, label: "Readiness", icon: ShieldCheck },
          { id: "review" as const, label: "Review workbench", icon: ClipboardCheck },
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

      {tab === "readiness" && (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <div className="flex items-center gap-4">
                <ProgressRing value={readiness.overall_readiness_score ?? 0} />
                <div>
                  <div className="font-medium text-text-strong">Overall readiness</div>
                  <div className="text-xs text-text-muted">{readiness.pillar_count} pillars</div>
                </div>
              </div>
            </Card>
            {evaluation?.observability_metrics && (
              <>
                <StatCard
                  label="Cloud-supported questions"
                  value={`${evaluation.observability_metrics.cloud_supported_rate}%`}
                  hint={`${evaluation.observability_metrics.cloud_supported_count} of ${evaluation.question_count}`}
                />
                <StatCard
                  label="Direct vs inferred"
                  value={`${evaluation.observability_metrics.direct_cloud_count} / ${evaluation.observability_metrics.inferred_cloud_count}`}
                  hint="Direct cloud evidence / inferred cloud evidence"
                />
                <StatCard
                  label="Requires non-cloud evidence"
                  value={evaluation.observability_metrics.requires_non_cloud_evidence_count}
                  hint="Endpoint, policy, or manual evidence required"
                />
              </>
            )}
          </div>

          <Card title="Pillars">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {(readiness.pillars ?? []).map((pillar: Record<string, any>) => (
                <div key={pillar.pillar_id} className="rounded-md border border-border-card p-3">
                  <div className="flex items-center gap-3">
                    <ProgressRing value={pillar.readiness_score ?? 0} size={48} />
                    <div>
                      <div className="text-sm font-medium text-text-strong">{pillar.pillar_name}</div>
                      <div className="text-xs text-text-muted capitalize">{pillar.status}</div>
                    </div>
                  </div>
                  <div className="mt-2 text-xs text-text-muted">
                    {pillar.controls_met} / {pillar.total_controls} controls met
                  </div>
                </div>
              ))}
            </div>
          </Card>

          {selfAssessment?.coverage_summary && (
            <Card title="Self-assessment coverage">
              <p className="mb-2 text-xs text-text-muted">
                {selfAssessment.question_count} questions ({selfAssessment.technical_question_count}{" "}
                technical)
              </p>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <div>
                  <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">
                    Evidence class
                  </div>
                  {Object.entries(selfAssessment.coverage_summary.evidence_class_counts ?? {}).map(
                    ([key, count]) => (
                      <div key={key} className="flex justify-between text-sm text-text-body">
                        <span className="capitalize">{key.replaceAll("_", " ")}</span>
                        <span className="text-text-muted">{count as number}</span>
                      </div>
                    )
                  )}
                </div>
                <div>
                  <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">
                    Proposed status
                  </div>
                  {Object.entries(selfAssessment.coverage_summary.proposed_status_counts ?? {}).map(
                    ([key, count]) => (
                      <div key={key} className="flex justify-between text-sm text-text-body">
                        <span className="capitalize">{key.replaceAll("_", " ")}</span>
                        <span className="text-text-muted">{count as number}</span>
                      </div>
                    )
                  )}
                </div>
              </div>
            </Card>
          )}
        </>
      )}

      {tab === "review" && (
        <>
          {entries.length === 0 ? (
            <EmptyState message="No Cyber Essentials review console data available." />
          ) : (
            <>
              <Card>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="text-sm text-text-body">
                    {reviewedCount} of {entries.length} questions reviewed (decisions stored locally
                    in this browser)
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => exportLedger("json")}
                      className="flex items-center gap-2 rounded-md border border-border-strong bg-surface-subtle px-3 py-2 text-sm text-text-strong hover:border-violet-500 hover:text-text-strong"
                    >
                      <Download className="h-4 w-4" /> Export JSON
                    </button>
                    <button
                      type="button"
                      onClick={() => exportLedger("csv")}
                      className="flex items-center gap-2 rounded-md border border-border-strong bg-surface-subtle px-3 py-2 text-sm text-text-strong hover:border-violet-500 hover:text-text-strong"
                    >
                      <Download className="h-4 w-4" /> Export CSV
                    </button>
                  </div>
                </div>
                <p className="mt-2 text-xs text-text-muted">
                  {reviewConsole?.review_policy?.score_boundary ??
                    "Reviewer decisions change the CE review ledger only. They do not change CRIS-SME deterministic findings, priorities, or scores."}
                </p>
              </Card>

              <div className="flex flex-wrap gap-3">
                <select
                  className="rounded-md border border-border-strong bg-surface-card px-3 py-2 text-sm text-text-strong"
                  value={sectionFilter}
                  onChange={(event) => {
                    setSectionFilter(event.target.value);
                    setPage(1);
                  }}
                >
                  <option value="all">All sections</option>
                  {sections.map((section) => (
                    <option key={section} value={section}>
                      {section.replaceAll("_", " ")}
                    </option>
                  ))}
                </select>
                <select
                  className="rounded-md border border-border-strong bg-surface-card px-3 py-2 text-sm text-text-strong"
                  value={stateFilter}
                  onChange={(event) => {
                    setStateFilter(event.target.value);
                    setPage(1);
                  }}
                >
                  <option value="all">All review states</option>
                  {allowedStates.map((state) => (
                    <option key={state} value={state}>
                      {STATE_LABELS[state] ?? state}
                    </option>
                  ))}
                </select>
              </div>

              <div className="overflow-hidden rounded-lg border border-border-card">
                <table className="w-full text-left text-sm">
                  <thead className="bg-surface-subtle text-xs uppercase tracking-wide text-text-muted">
                    <tr>
                      <th className="px-4 py-2">Question</th>
                      <th className="px-4 py-2">Section</th>
                      <th className="px-4 py-2">Proposed status</th>
                      <th className="px-4 py-2">Review state</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-row">
                    {paged.map((entry) => {
                      const state = decisionFor(entry.question_id);
                      const classes = STATE_COLORS[state] ?? STATE_COLORS.pending;
                      return (
                        <tr
                          key={entry.question_id}
                          className="cursor-pointer hover:bg-surface-card"
                          onClick={() => setActiveEntry(entry)}
                        >
                          <td className="px-4 py-2 text-text-strong">
                            <div className="font-mono text-xs text-text-muted">{entry.question_id}</div>
                            <div>{entry.short_paraphrase}</div>
                          </td>
                          <td className="px-4 py-2 text-text-muted capitalize">
                            {String(entry.section).replaceAll("_", " ")}
                          </td>
                          <td className="px-4 py-2 text-text-muted capitalize">
                            {String(entry.proposed_status).replaceAll("_", " ")}
                          </td>
                          <td className="px-4 py-2">
                            <span className={`rounded-full border px-2 py-0.5 text-xs ${classes}`}>
                              {STATE_LABELS[state] ?? state}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {filteredEntries.length > 0 && (
                <div className="flex items-center justify-between text-xs text-text-muted">
                  <span>
                    Showing {(currentPage - 1) * PAGE_SIZE + 1}–
                    {Math.min(currentPage * PAGE_SIZE, filteredEntries.length)} of{" "}
                    {filteredEntries.length}
                  </span>
                  <div className="flex gap-2">
                    <button
                      className="rounded-md border border-border-strong px-2 py-1 disabled:opacity-40"
                      disabled={currentPage <= 1}
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                    >
                      Previous
                    </button>
                    <span className="px-2 py-1">
                      Page {currentPage} of {totalPages}
                    </span>
                    <button
                      className="rounded-md border border-border-strong px-2 py-1 disabled:opacity-40"
                      disabled={currentPage >= totalPages}
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          )}

          <Drawer
            title={activeEntry?.question_id ?? ""}
            open={!!activeEntry}
            onClose={() => setActiveEntry(null)}
          >
            {activeEntry && (
              <CeReviewDetail
                entry={activeEntry}
                decision={ledger[activeEntry.question_id]}
                allowedStates={allowedStates}
                onChange={(patch) => setDecision(activeEntry.question_id, patch)}
              />
            )}
          </Drawer>
        </>
      )}
    </div>
  );
}

function CeReviewDetail({
  entry,
  decision,
  allowedStates,
  onChange,
}: {
  entry: Record<string, any>;
  decision: LedgerEntry | undefined;
  allowedStates: string[];
  onChange: (patch: Partial<LedgerEntry>) => void;
}) {
  const state = decision?.state ?? "pending";
  return (
    <div className="flex flex-col gap-4 text-sm">
      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-text-muted">
          Question
        </div>
        <p className="mt-1 text-text-strong">{entry.short_paraphrase}</p>
      </div>
      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-text-muted">
          Proposed answer
        </div>
        <p className="mt-1 text-text-strong">{entry.proposed_answer}</p>
        <p className="mt-1 text-xs text-text-muted">{entry.answer_basis}</p>
      </div>
      {entry.caveat && (
        <div className="rounded-md border border-sev-medium-border bg-sev-medium-bg p-3 text-xs text-sev-medium-text">
          {entry.caveat}
        </div>
      )}
      {(entry.supporting_control_ids ?? []).length > 0 && (
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-text-muted">
            Supporting controls
          </div>
          <div className="mt-1 flex flex-wrap gap-1">
            {entry.supporting_control_ids.map((id: string) => (
              <span
                key={id}
                className="rounded-full border border-border-strong bg-surface-subtle px-2 py-0.5 font-mono text-xs text-text-muted"
              >
                {id}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="border-t border-border-card pt-4">
        <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">
          Reviewer decision
        </div>
        <select
          className="w-full rounded-md border border-border-strong bg-surface-card px-3 py-2 text-sm text-text-strong"
          value={state}
          onChange={(event) => onChange({ state: event.target.value })}
        >
          {allowedStates.map((option) => (
            <option key={option} value={option}>
              {STATE_LABELS[option] ?? option}
            </option>
          ))}
        </select>
        <input
          className="mt-2 w-full rounded-md border border-border-strong bg-surface-card px-3 py-2 text-sm text-text-strong"
          placeholder="Reviewer name"
          value={decision?.reviewer ?? ""}
          onChange={(event) => onChange({ reviewer: event.target.value })}
        />
        <textarea
          className="mt-2 w-full rounded-md border border-border-strong bg-surface-card px-3 py-2 text-sm text-text-strong"
          placeholder="Reviewer note"
          rows={3}
          value={decision?.reviewer_note ?? ""}
          onChange={(event) => onChange({ reviewer_note: event.target.value })}
        />
        {state === "overridden" && (
          <textarea
            className="mt-2 w-full rounded-md border border-border-strong bg-surface-card px-3 py-2 text-sm text-text-strong"
            placeholder="Override reason"
            rows={2}
            value={decision?.override_reason ?? ""}
            onChange={(event) => onChange({ override_reason: event.target.value })}
          />
        )}
        {decision?.reviewed_at && (
          <p className="mt-2 text-xs text-text-muted">
            Last updated {new Date(decision.reviewed_at).toLocaleString()}
          </p>
        )}
      </div>
    </div>
  );
}
