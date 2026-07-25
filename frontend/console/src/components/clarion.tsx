import type { ButtonHTMLAttributes, ComponentType, ReactNode } from "react";
import { useCountUp } from "../hooks/useCountUp";

/**
 * "Clarion" design system components — ported from the design handoff
 * (tokens.css / tokens.md). Tailwind utility classes reference the semantic
 * theme tokens registered in src/index.css (`@theme`), not raw hex values.
 */

// -- Button -------------------------------------------------------------

type ButtonVariant = "primary" | "secondary" | "ghost";

export function Button({
  variant = "secondary",
  icon: Icon,
  className = "",
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  icon?: ComponentType<{ className?: string; strokeWidth?: number }>;
}) {
  const base =
    "inline-flex h-9 items-center gap-1.5 rounded-md px-3.5 text-[12.5px] font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50";
  const variantClasses: Record<ButtonVariant, string> = {
    primary: "bg-primary text-white shadow-primary hover:bg-primary-hover",
    secondary:
      "border border-border-strong bg-surface-card text-text-body hover:bg-surface-subtle",
    ghost: "border border-border-strong bg-surface-card text-text-body hover:bg-surface-subtle",
  };

  return (
    <button className={`${base} ${variantClasses[variant]} ${className}`} {...rest}>
      {Icon && <Icon className="h-3.5 w-3.5" strokeWidth={1.8} />}
      {children}
    </button>
  );
}

// -- KpiCard --------------------------------------------------------------

type KpiAccent = "critical" | "high" | "medium" | "good" | undefined;

const ACCENT_RAIL: Record<string, string> = {
  critical: "shadow-[inset_3px_0_0_var(--color-sev-critical)]",
  high: "shadow-[inset_3px_0_0_var(--color-sev-high)]",
  medium: "shadow-[inset_3px_0_0_var(--color-sev-medium)]",
  good: "shadow-[inset_3px_0_0_var(--color-status-good)]",
};

const DELTA_TONE: Record<string, string> = {
  good: "text-status-good-text",
  warning: "text-sev-critical-text",
  neutral: "text-text-body",
};

export function KpiCard({
  label,
  value,
  delta,
  deltaTone = "neutral",
  accent,
}: {
  label: string;
  value: ReactNode;
  delta?: ReactNode;
  deltaTone?: "good" | "warning" | "neutral";
  accent?: KpiAccent;
}) {
  const isNumeric = typeof value === "number";
  const animated = useCountUp(isNumeric ? value : 0);
  const displayValue = isNumeric ? Math.round(animated) : value;

  return (
    <div
      className={`rounded-xl border border-border-card bg-surface-card p-[16px_18px] ${
        accent ? ACCENT_RAIL[accent] : ""
      }`}
    >
      <div className="text-[10.5px] font-bold uppercase tracking-[.08em] text-text-muted">
        {label}
      </div>
      <div className="my-1 text-[30px] font-extrabold leading-none tracking-[-.02em] text-text-strong">
        {displayValue}
      </div>
      {delta && <div className={`text-[12px] font-semibold ${DELTA_TONE[deltaTone]}`}>{delta}</div>}
    </div>
  );
}

// -- SeverityTag ------------------------------------------------------------

export type SeverityLevel = "critical" | "high" | "medium" | "low";

const SEVERITY_LABEL: Record<SeverityLevel, string> = {
  critical: "CRIT",
  high: "HIGH",
  medium: "MED",
  low: "LOW",
};

const SEVERITY_CLASSES: Record<SeverityLevel, string> = {
  critical: "text-sev-critical-text bg-sev-critical-bg",
  high: "text-sev-high-text bg-sev-high-bg",
  medium: "text-sev-medium-text bg-sev-medium-bg",
  low: "text-sev-low-text bg-sev-low-bg",
};

export function normalizeSeverity(value: string): SeverityLevel {
  const normalized = value.trim().toLowerCase();
  if (normalized === "critical" || normalized === "high" || normalized === "medium" || normalized === "low") {
    return normalized;
  }
  return "low";
}

export function SeverityTag({ level }: { level: SeverityLevel }) {
  return (
    <span
      className={`rounded-[5px] px-[7px] py-[3px] text-[9.5px] font-bold ${SEVERITY_CLASSES[level]}`}
    >
      {SEVERITY_LABEL[level]}
    </span>
  );
}

// -- LifecycleBadge ---------------------------------------------------------
// Finding/exception lifecycle status — distinct from the run-status
// StatusBadge in ui.tsx (queued/running/completed/failed).

const LIFECYCLE_CLASSES: Record<string, string> = {
  open: "bg-surface-rail text-text-body",
  in_progress: "bg-sev-high-bg text-sev-high-text",
  accepted: "bg-sev-medium-bg text-sev-medium-text",
  resolved: "bg-status-good-bg text-status-good-text",
};

export function LifecycleBadge({ status }: { status: string }) {
  const key = status.trim().toLowerCase().replace(/\s+/g, "_");
  const classes = LIFECYCLE_CLASSES[key] ?? "bg-surface-rail text-text-body";
  return (
    <span className={`rounded-[5px] px-[7px] py-[3px] text-[9.5px] font-bold capitalize ${classes}`}>
      {status}
    </span>
  );
}

// -- Meter --------------------------------------------------------------

function meterColor(ratio: number): string {
  if (ratio >= 0.75) return "var(--color-sev-critical)";
  if (ratio >= 0.5) return "var(--color-sev-high)";
  if (ratio >= 0.25) return "var(--color-sev-medium)";
  return "var(--color-status-good)";
}

export function Meter({
  value,
  max = 100,
  color,
  height = 8,
}: {
  value: number;
  max?: number;
  color?: string;
  height?: number;
}) {
  const animated = useCountUp(value, 800);
  const targetRatio = max > 0 ? Math.min(Math.max(value / max, 0), 1) : 0;
  const animatedRatio = max > 0 ? Math.min(Math.max(animated / max, 0), 1) : 0;
  const fill = color ?? meterColor(targetRatio);
  return (
    <span
      className="block overflow-hidden rounded-full bg-surface-rail"
      style={{ height }}
    >
      <span
        className="block h-full rounded-full"
        style={{ width: `${animatedRatio * 100}%`, background: fill }}
      />
    </span>
  );
}

// -- Panel ----------------------------------------------------------------

export function Panel({
  title,
  meta,
  children,
  className = "",
}: {
  title?: string;
  meta?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-2xl border border-border-card bg-surface-card p-[18px_20px] ${className}`}>
      {(title || meta) && (
        <div className="mb-3.5 flex items-baseline justify-between border-b border-border-divider pb-3.5">
          {title && <div className="text-[13.5px] font-bold text-text-strong">{title}</div>}
          {meta && <div className="text-[11.5px] font-medium text-text-muted">{meta}</div>}
        </div>
      )}
      {children}
    </div>
  );
}

// -- DataTable --------------------------------------------------------------

export interface DataTableColumn<T> {
  key: string;
  header: string;
  align?: "left" | "right";
  width?: string;
  render: (row: T) => ReactNode;
}

export function DataTable<T extends { id: string | number }>({
  columns,
  rows,
  onRowClick,
  selectedId,
}: {
  columns: DataTableColumn<T>[];
  rows: T[];
  onRowClick?: (row: T) => void;
  selectedId?: string | number;
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-border-card bg-surface-card">
      <table className="w-full text-left">
        <thead>
          <tr className="bg-surface-subtle">
            {columns.map((column) => (
              <th
                key={column.key}
                className={`px-4 py-[13px] text-[9.5px] font-bold uppercase tracking-[.07em] text-text-muted ${
                  column.align === "right" ? "text-right" : "text-left"
                }`}
                style={column.width ? { width: column.width } : undefined}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const selected = selectedId !== undefined && row.id === selectedId;
            return (
              <tr
                key={row.id}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={`border-t border-border-row ${onRowClick ? "cursor-pointer hover:bg-surface-subtle" : ""} ${
                  selected ? "border-l-[3px] border-l-primary bg-primary-tint" : ""
                }`}
              >
                {columns.map((column) => (
                  <td
                    key={column.key}
                    className={`px-4 py-[13px] text-[12.5px] text-text-body ${
                      column.align === "right" ? "text-right" : "text-left"
                    }`}
                  >
                    {column.render(row)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
      {rows.length === 0 && (
        <div className="p-8 text-center text-[12.5px] text-text-muted">No rows to display.</div>
      )}
    </div>
  );
}

// -- ScoreRing --------------------------------------------------------------

export function ScoreRing({
  value,
  max = 100,
  size = 168,
  color,
  caption = "Risk / 100",
}: {
  value: number;
  max?: number;
  size?: number;
  color?: string;
  caption?: string;
}) {
  const animated = useCountUp(value, 900);
  const radius = (size - 26) / 2;
  const circumference = 2 * Math.PI * radius;
  const targetRatio = max > 0 ? Math.min(Math.max(value / max, 0), 1) : 0;
  const animatedRatio = max > 0 ? Math.min(Math.max(animated / max, 0), 1) : 0;
  const offset = circumference * (1 - animatedRatio);
  // Color is derived from the *target* ratio, not the in-flight animated
  // one -- otherwise a high score would flicker through every severity
  // band's color as the ring sweeps up from zero.
  const strokeColor = color ?? meterColor(targetRatio);

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-border-divider)"
          strokeWidth={13}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={strokeColor}
          strokeWidth={13}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="text-[46px] font-extrabold leading-none tracking-[-.02em] text-text-strong">
          {Math.round(animated)}
        </div>
        <div className="mt-0.5 text-[10.5px] font-semibold uppercase tracking-[.08em] text-text-muted">
          {caption}
        </div>
      </div>
    </div>
  );
}
