import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ArrowDown, ArrowUp, ArrowUpDown, Download, Search } from "lucide-react";
import { artifactUrl } from "../api/client";
import { useAssessmentReport } from "../context/AssessmentContext";
import type { PrioritizedRisk } from "../api/types";
import { EmptyState, Spinner } from "../components/ui";
import {
  DataTable,
  LifecycleBadge,
  SeverityTag,
  type DataTableColumn,
} from "../components/clarion";
import { normalizeSeverity } from "../components/severity";

type SortKey = "score" | "title" | "category" | "severity" | "control_id";

const SEVERITY_RANK: Record<string, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
};

const SEVERITY_CHIP_CLASSES: Record<string, string> = {
  all: "bg-primary text-white",
  critical: "bg-sev-critical-bg text-sev-critical-text",
  high: "bg-sev-high-bg text-sev-high-text",
  medium: "bg-sev-medium-bg text-sev-medium-text",
  low: "bg-sev-low-bg text-sev-low-text",
};

type FindingRow = PrioritizedRisk & { id: string };

export function Findings() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { data: report, isLoading, error } = useAssessmentReport();

  const [severityFilter, setSeverityFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState(searchParams.get("category") ?? "all");
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const risks = report?.prioritized_risks ?? [];

  const categories = useMemo(
    () => [...new Set(risks.map((risk) => risk.category))].sort(),
    [risks]
  );

  const categoryAndSearchFiltered = useMemo(
    () =>
      risks
        .filter((risk) => categoryFilter === "all" || risk.category === categoryFilter)
        .filter((risk) =>
          search.trim() === ""
            ? true
            : `${risk.title} ${risk.control_id} ${risk.resource_scope}`
                .toLowerCase()
                .includes(search.toLowerCase())
        ),
    [risks, categoryFilter, search]
  );

  const severityCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const risk of categoryAndSearchFiltered) {
      const level = normalizeSeverity(risk.severity);
      counts[level] = (counts[level] ?? 0) + 1;
    }
    return counts;
  }, [categoryAndSearchFiltered]);

  const sorted = useMemo(() => {
    const filtered = categoryAndSearchFiltered.filter(
      (risk) => severityFilter === "all" || normalizeSeverity(risk.severity) === severityFilter
    );
    const direction = sortDir === "asc" ? 1 : -1;
    return filtered.sort((a, b) => {
      switch (sortKey) {
        case "score":
          return (a.score - b.score) * direction;
        case "severity":
          return (
            ((SEVERITY_RANK[a.severity.toLowerCase()] ?? 0) -
              (SEVERITY_RANK[b.severity.toLowerCase()] ?? 0)) *
            direction
          );
        case "title":
          return a.title.localeCompare(b.title) * direction;
        case "category":
          return a.category.localeCompare(b.category) * direction;
        case "control_id":
          return a.control_id.localeCompare(b.control_id) * direction;
        default:
          return 0;
      }
    });
  }, [categoryAndSearchFiltered, severityFilter, sortKey, sortDir]);

  const rows: FindingRow[] = sorted.map((risk) => ({ ...risk, id: risk.finding_id }));
  const selected = rows.find((row) => row.id === selectedId) ?? rows[0];

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(key);
      setSortDir(key === "title" || key === "category" || key === "control_id" ? "asc" : "desc");
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-8 text-text-muted">
        <Spinner /> Loading findings…
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <EmptyState message={`Failed to load report: ${(error as Error).message}`} />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="p-8">
        <EmptyState message="No assessment report found yet." />
      </div>
    );
  }

  const findingsCsv = (report as Record<string, any>).report_artifacts?.csv_exports
    ?.findings_csv as string | undefined;

  const columns: DataTableColumn<FindingRow>[] = [
    {
      key: "control",
      header: "Control",
      width: "78px",
      render: (row) => <SortLabel label={row.control_id} mono color="text-text-muted" />,
    },
    {
      key: "sev",
      header: "Sev",
      width: "60px",
      render: (row) => <SeverityTag level={normalizeSeverity(row.severity)} />,
    },
    {
      key: "finding",
      header: "Finding",
      render: (row) => (
        <span className="min-w-0">
          <span className="block truncate text-[12.5px] font-semibold text-text-strong">
            {row.title}
          </span>
          <span className="block truncate text-[11px] font-medium text-text-muted">
            {row.resource_scope}
          </span>
        </span>
      ),
    },
    {
      key: "score",
      header: "Score",
      align: "right",
      width: "50px",
      render: (row) => <span className="text-[16px] font-extrabold text-text-strong">{Math.round(row.score)}</span>,
    },
  ];

  return (
    <div className="flex flex-col">
      {/* Topbar-style header (page-specific) */}
      <div className="flex items-center justify-between gap-4 border-b border-border-card bg-surface-card px-[26px] py-[13px]">
        <div className="text-[11.5px] font-medium text-text-muted">
          {sorted.length} of {risks.length} prioritized findings
        </div>
        <div className="flex items-center gap-2.5">
          <label className="flex h-9 items-center gap-2 rounded-md border border-border-strong bg-surface-subtle px-3">
            <Search className="h-3.5 w-3.5 text-text-muted" strokeWidth={1.8} />
            <input
              className="w-48 bg-transparent text-[12.5px] font-medium text-text-body placeholder:text-text-muted focus:outline-none"
              placeholder="Control, title, asset…"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
          <select
            className="h-9 rounded-md border border-border-strong bg-surface-card px-3 text-[12.5px] font-medium text-text-body focus:outline-none"
            value={categoryFilter}
            onChange={(event) => setCategoryFilter(event.target.value)}
          >
            <option value="all">All categories</option>
            {categories.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
          {findingsCsv && (
            <a
              href={artifactUrl(findingsCsv)}
              className="flex h-9 items-center gap-1.5 rounded-md border border-border-strong bg-surface-card px-3.5 text-[12.5px] font-semibold text-text-body hover:bg-surface-subtle"
            >
              <Download className="h-3.5 w-3.5 text-primary" strokeWidth={1.7} />
              Export
            </a>
          )}
        </div>
      </div>

      {/* Filter chip bar */}
      <div className="flex flex-wrap items-center gap-2 border-b border-border-card bg-surface-card px-[26px] py-[13px]">
        <Chip
          label={`All · ${categoryAndSearchFiltered.length}`}
          active={severityFilter === "all"}
          tone="all"
          onClick={() => setSeverityFilter("all")}
        />
        {(["critical", "high", "medium", "low"] as const).map((level) => (
          <Chip
            key={level}
            label={`${level[0].toUpperCase()}${level.slice(1)} · ${severityCounts[level] ?? 0}`}
            active={severityFilter === level}
            tone={level}
            onClick={() => setSeverityFilter(level)}
          />
        ))}
        <span className="ml-auto text-[11.5px] font-medium text-text-muted">
          Sorted by {sortKey} {sortDir === "desc" ? "▾" : "▴"}
        </span>
      </div>

      {/* Two-pane workbench */}
      <div className="grid grid-cols-1 gap-[18px] p-[20px_26px_26px] lg:grid-cols-[minmax(0,1.32fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap gap-1.5 text-[11px] font-medium text-text-muted">
            {(
              [
                ["control_id", "Control"],
                ["title", "Title"],
                ["category", "Category"],
                ["severity", "Severity"],
                ["score", "Score"],
              ] as [SortKey, string][]
            ).map(([key, label]) => (
              <SortableChip
                key={key}
                label={label}
                active={sortKey === key}
                dir={sortDir}
                onClick={() => toggleSort(key)}
              />
            ))}
          </div>
          <DataTable
            columns={columns}
            rows={rows}
            selectedId={selected?.id}
            onRowClick={(row) => setSelectedId(row.id)}
          />
          {rows.length === 0 && <EmptyState message="No findings match the current filters." />}
        </div>

        <FindingDetail risk={selected} onPlanRemediation={() => navigate("/remediation")} />
      </div>
    </div>
  );
}

function Chip({
  label,
  active,
  tone,
  onClick,
}: {
  label: string;
  active: boolean;
  tone: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-lg px-[13px] py-1.5 text-[11.5px] font-semibold transition-opacity ${
        SEVERITY_CHIP_CLASSES[tone] ?? SEVERITY_CHIP_CLASSES.all
      } ${active ? "" : "opacity-45 hover:opacity-75"}`}
    >
      {label}
    </button>
  );
}

function SortLabel({
  label,
  mono,
  color,
}: {
  label: string;
  mono?: boolean;
  color?: string;
}) {
  return (
    <span className={`text-[11px] font-semibold ${mono ? "font-mono" : ""} ${color ?? ""}`}>{label}</span>
  );
}

function SortableChip({
  label,
  active,
  dir,
  onClick,
}: {
  label: string;
  active: boolean;
  dir: "asc" | "desc";
  onClick: () => void;
}) {
  const Icon = active ? (dir === "asc" ? ArrowUp : ArrowDown) : ArrowUpDown;
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1 rounded-md px-2 py-1 transition-colors hover:bg-surface-subtle ${
        active ? "text-primary" : "text-text-muted"
      }`}
    >
      {label}
      <Icon className="h-3 w-3" />
    </button>
  );
}

function FindingDetail({
  risk,
  onPlanRemediation,
}: {
  risk: FindingRow | undefined;
  onPlanRemediation: () => void;
}) {
  if (!risk) {
    return (
      <aside className="flex flex-col rounded-2xl border border-border-card bg-surface-card p-[20px_22px]">
        <EmptyState message="Select a finding to see its detail." />
      </aside>
    );
  }

  const level = normalizeSeverity(risk.severity);
  const breakdown = (risk as Record<string, any>).score_breakdown as Record<string, any> | undefined;
  const confidence = (risk as Record<string, any>).confidence_calibration as Record<string, any> | undefined;
  const lifecycle = (risk as Record<string, any>).lifecycle as Record<string, any> | undefined;
  const evidenceIds = (risk as Record<string, any>).evidence_ids as string[] | undefined;

  return (
    <aside className="flex flex-col rounded-2xl border border-border-card bg-surface-card p-[20px_22px]">
      <div className="mb-1 flex items-center gap-2">
        <span className="font-mono text-[12px] font-semibold text-primary">{risk.control_id}</span>
        <SeverityTag level={level} />
        {lifecycle?.status && (
          <span className="ml-auto">
            <LifecycleBadge status={lifecycle.status} />
          </span>
        )}
      </div>
      <h3 className="m-0 mb-1 mt-1.5 text-[18px] font-extrabold tracking-[-.01em] text-text-strong">
        {risk.title}
      </h3>
      <p className="m-0 mb-4 text-[12.5px] font-medium leading-[1.6] text-text-body">
        {risk.evidence?.[0] ?? `Resource scope: ${risk.resource_scope}`}
      </p>

      {breakdown && (
        <>
          <SectionLabel>Score breakdown</SectionLabel>
          <div className="mb-[18px] grid grid-cols-3 gap-[9px]">
            <ScoreBox label="Base severity" value={breakdown.base_severity} />
            <ScoreBox
              label="Confidence"
              value={confidence?.calibrated_confidence ?? breakdown.confidence_factor}
            />
            <ScoreBox label="Final score" value={Math.round(risk.score)} accent />
          </div>
        </>
      )}

      {risk.evidence?.length > 0 && (
        <>
          <SectionLabel>Evidence</SectionLabel>
          <div className="mb-4 flex flex-col gap-[7px] border-l-2 border-primary-tint-border py-0.5 pl-3">
            {risk.evidence.map((item, index) => (
              <div key={index} className="text-[12px] font-medium leading-[1.5] text-text-body">
                {item}
                {evidenceIds?.[index] && (
                  <div className="font-mono text-[11px] text-text-muted">{evidenceIds[index]}</div>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      {risk.evidence_quality?.missing_requirements?.length > 0 && (
        <>
          <SectionLabel>Missing requirements</SectionLabel>
          <ul className="mb-4 list-inside list-disc text-[12px] font-medium text-text-body">
            {risk.evidence_quality.missing_requirements.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </>
      )}

      {risk.remediation_summary && (
        <>
          <SectionLabel>Remediation</SectionLabel>
          <div className="mb-[18px] rounded-[10px] border border-border-divider bg-surface-subtle p-[13px_14px]">
            <div className="mb-1 text-[12.5px] font-semibold text-text-strong">
              {risk.remediation_summary}
            </div>
            {risk.remediation_cost_tier && (
              <div className="text-[12px] font-medium leading-[1.55] text-text-body">
                Estimated cost tier: <b className="text-status-good-text">{risk.remediation_cost_tier}</b>
              </div>
            )}
          </div>
        </>
      )}

      <div className="mt-auto flex gap-2">
        <button
          type="button"
          onClick={onPlanRemediation}
          className="flex h-[38px] flex-1 items-center justify-center rounded-md bg-primary text-[12.5px] font-bold text-white shadow-primary hover:bg-primary-hover"
        >
          Plan remediation
        </button>
      </div>
    </aside>
  );
}

function SectionLabel({ children }: { children: string }) {
  return (
    <div className="mb-2 text-[10px] font-bold uppercase tracking-[.09em] text-text-muted">{children}</div>
  );
}

function ScoreBox({ label, value, accent }: { label: string; value: unknown; accent?: boolean }) {
  let display: string = "—";
  if (typeof value === "number") {
    display = value % 1 === 0 ? String(value) : value.toFixed(2);
  } else if (typeof value === "string") {
    display = value;
  }

  return (
    <div
      className={`rounded-[10px] border p-[11px] text-center ${
        accent ? "border-primary-tint-border bg-primary-tint" : "border-border-divider bg-surface-subtle"
      }`}
    >
      <div
        className={`text-[9px] font-bold uppercase tracking-[.06em] ${
          accent ? "text-violet" : "text-text-muted"
        }`}
      >
        {label}
      </div>
      <div className={`mt-1 text-[18px] font-extrabold ${accent ? "text-primary" : "text-text-strong"}`}>
        {display}
      </div>
    </div>
  );
}
