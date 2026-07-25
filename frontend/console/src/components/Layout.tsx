import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  LayoutGrid,
  PlayCircle,
  ListChecks,
  Boxes,
  ShieldCheck,
  Globe2,
  Workflow,
  Users,
  Award,
  Wrench,
  GitBranch,
  ClipboardCheck,
  EyeOff,
  FileText,
  LineChart,
  Gavel,
  GitCompare,
  Plus,
  HeartPulse,
  Moon,
  Sun,
  FlaskConical,
  History,
} from "lucide-react";
import { getHealth } from "../api/client";
import { useAssessment } from "../context/AssessmentContext";
import { useTheme } from "../hooks/useTheme";

interface NavItemDef {
  to: string;
  label: string;
  end?: boolean;
  icon: typeof LayoutGrid;
}

interface NavGroup {
  label: string;
  items: NavItemDef[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Platform",
    items: [
      { to: "/", label: "Command Center", end: true, icon: LayoutGrid },
      { to: "/assessment", label: "New Assessment", icon: PlayCircle },
      { to: "/findings", label: "Findings", icon: ListChecks },
      { to: "/resources", label: "Resources", icon: Boxes },
      { to: "/attack-paths", label: "Attack Paths", icon: Workflow },
      { to: "/public-exposure", label: "Public Exposure", icon: Globe2 },
    ],
  },
  {
    label: "Compliance & Governance",
    items: [
      { to: "/personas", label: "Personas", icon: Users },
      { to: "/compliance", label: "Compliance", icon: ShieldCheck },
      { to: "/cyber-essentials", label: "Cyber Essentials", icon: ClipboardCheck },
      { to: "/iomt", label: "Healthcare IoT", icon: HeartPulse },
      { to: "/trend", label: "Trend & History", icon: LineChart },
      { to: "/governance", label: "Exceptions & Governance", icon: Gavel },
      { to: "/native-validation", label: "Native Validation", icon: GitCompare },
    ],
  },
  {
    label: "Evidence & Trust",
    items: [
      { to: "/trust", label: "Trust Center", icon: Award },
      { to: "/evidence", label: "Evidence & Provenance", icon: GitBranch },
      { to: "/disclosure", label: "Disclosure Room", icon: EyeOff },
    ],
  },
  {
    label: "Actions",
    items: [
      { to: "/remediation", label: "Remediation", icon: Wrench },
      { to: "/reports", label: "Reports & Artifacts", icon: FileText },
    ],
  },
];

const ALL_NAV_ITEMS = NAV_GROUPS.flatMap((group) => group.items);

const IS_DEMO = import.meta.env.VITE_DEMO_MODE === "true";

export function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const activeItem =
    ALL_NAV_ITEMS.find((item) =>
      item.end ? location.pathname === item.to : location.pathname.startsWith(item.to)
    ) ?? ALL_NAV_ITEMS[0];

  const health = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchInterval: 30_000,
    retry: 1,
  });

  const { theme, toggleTheme } = useTheme();
  const {
    assessments,
    selectedAssessment,
    selectedReportId,
    setSelectedReportId,
    historyLoading,
  } = useAssessment();
  const connected = health.data?.status === "ok";
  const subtitle = selectedAssessment
    ? `${selectedAssessment.organization_name} · ${selectedAssessment.provider.toUpperCase()} · ${new Date(selectedAssessment.generated_at).toLocaleString()}`
    : undefined;

  return (
    <div className="flex min-h-screen bg-surface-app font-ui text-text-body">
      <aside className="flex w-[236px] shrink-0 flex-col bg-[linear-gradient(190deg,var(--color-sidebar-bg-top),var(--color-sidebar-bg-bottom))]">
        <div className="flex items-center gap-2.5 border-b border-white/[0.06] px-[18px] py-[18px] pt-5">
          <div className="grid h-[34px] w-[34px] shrink-0 place-items-center rounded-md bg-gradient-to-br from-indigo-500 to-primary shadow-brandmark">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 2.6l7.2 2.7v5.3c0 4.6-3 8.2-7.2 9.8-4.2-1.6-7.2-5.2-7.2-9.8V5.3L12 2.6z"
                stroke="#fff"
                strokeWidth="1.7"
                strokeLinejoin="round"
              />
              <path
                d="M8.7 12.1l2.3 2.3 4.3-4.6"
                stroke="#fff"
                strokeWidth="1.7"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          <div className="leading-tight">
            <div className="text-[14px] font-extrabold tracking-tight text-white">
              CRIS<span className="font-semibold text-sidebar-icon-active">·SME</span>
            </div>
            <div className="text-[10.5px] font-medium tracking-wide text-sidebar-brand-sub">
              Assurance Console
            </div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-3.5">
          {NAV_GROUPS.map((group) => (
            <div key={group.label}>
              <div className="px-2 pb-1.5 pt-3.5 text-[10px] font-bold uppercase tracking-[.12em] text-sidebar-section-label first:pt-2">
                {group.label}
              </div>
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) =>
                      `mb-0.5 flex items-center gap-2.5 rounded-md px-[11px] py-[9px] text-[13px] font-medium transition-colors ${
                        isActive
                          ? "border border-sidebar-item-active-border bg-sidebar-item-active-bg font-semibold text-white"
                          : "text-sidebar-item hover:bg-white/5 hover:text-white"
                      }`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <Icon
                          className={`h-4 w-4 ${isActive ? "text-sidebar-icon-active" : ""}`}
                          strokeWidth={1.6}
                        />
                        {item.label}
                      </>
                    )}
                  </NavLink>
                );
              })}
            </div>
          ))}
        </nav>

        {IS_DEMO ? (
          <div className="m-3 rounded-[11px] border border-amber-400/20 bg-amber-400/[0.08] px-3.5 py-[13px]">
            <div className="mb-1.5 flex items-center gap-1.5">
              <FlaskConical className="h-3.5 w-3.5 text-amber-300" strokeWidth={1.7} />
              <span className="text-[11px] font-semibold text-amber-200">Demo mode</span>
            </div>
            <div className="text-[11px] leading-[1.5] text-sidebar-brand-sub">
              Showing anonymised sample data for Contoso Healthcare Ltd.
            </div>
          </div>
        ) : (
          <div className="m-3 rounded-[11px] border border-white/[0.07] bg-white/[0.04] px-3.5 py-[13px]">
            <div className="mb-1.5 flex items-center gap-1.5">
              <span
                className={`h-[7px] w-[7px] rounded-full ${
                  connected
                    ? "bg-emerald-400 shadow-[0_0_8px_#22c55e]"
                    : health.isLoading
                      ? "bg-slate-500"
                      : "bg-sev-critical"
                }`}
              />
              <span className="text-[11px] font-semibold text-slate-200">
                {connected ? "Local runner · connected" : health.isLoading ? "Connecting…" : "Local runner · unavailable"}
              </span>
            </div>
            <div className="text-[11px] leading-[1.5] text-sidebar-brand-sub">
              Read-only evidence collection · no remote services.
            </div>
          </div>
        )}
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="flex h-[60px] shrink-0 items-center justify-between gap-[18px] border-b border-border-card bg-surface-card px-[26px]">
          <div>
            <div className="text-[15px] font-bold tracking-tight text-text-strong">
              {activeItem.label}
            </div>
            {subtitle && (
              <div className="text-[11.5px] font-medium text-text-muted">{subtitle}</div>
            )}
          </div>
          <div className="flex items-center gap-2.5">
            {IS_DEMO ? (
              <span className="flex h-7 items-center gap-1.5 rounded-full border border-amber-400/30 bg-amber-400/10 px-3 text-[11.5px] font-semibold text-amber-500 dark:text-amber-300">
                <FlaskConical className="h-3.5 w-3.5" strokeWidth={1.8} />
                Demo · Contoso Healthcare Ltd
              </span>
            ) : selectedAssessment ? (
              <label className="flex h-10 min-w-[320px] max-w-[440px] items-center gap-2 rounded-md border border-border-strong bg-surface-subtle px-2.5">
                <History className="h-4 w-4 shrink-0 text-primary" strokeWidth={1.8} />
                <span className="sr-only">Active assessment</span>
                <select
                  value={selectedReportId}
                  onChange={(event) => setSelectedReportId(event.target.value)}
                  title="Select assessment history"
                  className="min-w-0 flex-1 bg-transparent text-[12px] font-semibold text-text-strong outline-none"
                >
                  {assessments.map((assessment) => (
                    <option key={assessment.report_id} value={assessment.report_id}>
                      {assessment.organization_name} · {new Date(assessment.generated_at).toLocaleString()} · {assessment.provider.toUpperCase()}
                    </option>
                  ))}
                </select>
                <span className="shrink-0 border-l border-border-card pl-2 font-mono text-[10px] text-text-muted">
                  {selectedAssessment.run_id.replace(/^run_/, "").slice(0, 8)}
                </span>
              </label>
            ) : (
              <div className="text-[12px] font-medium text-text-muted">
                {historyLoading ? "Loading assessments…" : "No assessments available"}
              </div>
            )}
            {!IS_DEMO && (
              <button
                type="button"
                onClick={() => navigate("/assessment")}
                className="flex h-9 items-center gap-1.5 rounded-md bg-primary px-3.5 text-[12.5px] font-bold text-white shadow-primary transition-colors hover:bg-primary-hover"
              >
                <Plus className="h-3.5 w-3.5" strokeWidth={1.8} />
                New assessment
              </button>
            )}
            <span className="mx-1 h-[18px] w-px bg-border-card" />
            <button
              type="button"
              onClick={toggleTheme}
              title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              className="flex h-9 w-9 items-center justify-center rounded-md border border-border-strong bg-surface-subtle text-text-body transition-colors hover:bg-surface-rail hover:text-text-strong"
            >
              {theme === "dark" ? (
                <Sun className="h-4 w-4" strokeWidth={1.8} />
              ) : (
                <Moon className="h-4 w-4" strokeWidth={1.8} />
              )}
            </button>
            {!IS_DEMO && (
              <>
                <span className="mx-1 h-[18px] w-px bg-border-card" />
                <div className="flex items-center gap-2 text-[11.5px] font-medium text-text-muted">
                  <span
                    className={`h-[7px] w-[7px] rounded-full ${
                      connected ? "bg-emerald-500" : health.isLoading ? "bg-slate-400" : "bg-sev-critical"
                    }`}
                  />
                  {connected ? "Connected" : health.isLoading ? "Connecting…" : "Unavailable"}
                </div>
              </>
            )}
          </div>
        </header>
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
