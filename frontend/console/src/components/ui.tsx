import type { ComponentType, ReactNode } from "react";
import { Cell, Pie, PieChart } from "recharts";
import { useCountUp } from "../hooks/useCountUp";

export function Card({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-2xl border border-border-card bg-surface-card p-[18px_20px] shadow-card ${className}`}
    >
      {title && (
        <h2 className="mb-3.5 border-b border-border-divider pb-3.5 text-[13.5px] font-bold text-text-strong">
          {title}
        </h2>
      )}
      {children}
    </div>
  );
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: "bg-sev-critical-bg text-sev-critical-text border-sev-critical-border",
  high: "bg-sev-high-bg text-sev-high-text border-sev-high-border",
  medium: "bg-sev-medium-bg text-sev-medium-text border-sev-medium-border",
  low: "bg-sev-low-bg text-sev-low-text border-sev-low-border",
};

export function SeverityBadge({ severity }: { severity: string }) {
  const key = severity.toLowerCase();
  const classes = SEVERITY_COLORS[key] ?? "bg-surface-rail text-text-body border-border-strong";
  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${classes}`}>
      {severity}
    </span>
  );
}

const STATUS_COLORS: Record<string, string> = {
  completed: "bg-status-good-bg text-status-good-text border-status-good-border",
  running: "bg-primary-tint text-primary-on-tint border-primary-tint-border",
  queued: "bg-surface-rail text-text-body border-border-strong",
  failed: "bg-sev-critical-bg text-sev-critical-text border-sev-critical-border",
  started: "bg-primary-tint text-primary-on-tint border-primary-tint-border",
};

export function StatusBadge({ status }: { status: string }) {
  const classes = STATUS_COLORS[status] ?? "bg-surface-rail text-text-body border-border-strong";
  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${classes}`}>
      {status}
    </span>
  );
}

export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  accent = "text-primary bg-primary-tint",
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  icon?: ComponentType<{ className?: string }>;
  accent?: string;
}) {
  const isNumeric = typeof value === "number";
  const animated = useCountUp(isNumeric ? value : 0);
  const displayValue = isNumeric ? Math.round(animated) : value;

  return (
    <div className="rounded-xl border border-border-card bg-surface-card p-5">
      <div className="flex items-start justify-between">
        <div className="text-[10.5px] font-bold uppercase tracking-[.08em] text-text-muted">
          {label}
        </div>
        {Icon && (
          <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${accent}`}>
            <Icon className="h-4 w-4" />
          </div>
        )}
      </div>
      <div className="mt-2 text-[28px] font-extrabold tracking-[-.02em] text-text-strong">
        {displayValue}
      </div>
      {hint && <div className="mt-1 text-xs font-medium text-text-muted">{hint}</div>}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-dashed border-border-strong p-10 text-center text-[13px] font-medium text-text-muted">
      {message}
    </div>
  );
}

const SEVERITY_HEX: Record<string, string> = {
  critical: "#e5484d",
  high: "#f76808",
  medium: "#f5a623",
  low: "#3b82f6",
};

export function SeverityDonut({ counts }: { counts: Record<string, number> }) {
  const order = ["critical", "high", "medium", "low"];
  const entries = order
    .map((severity) => ({ severity, count: counts[severity] ?? 0 }))
    .filter((entry) => entry.count > 0);

  const total = entries.reduce((sum, entry) => sum + entry.count, 0);

  if (total === 0) {
    return <EmptyState message="No severity data available." />;
  }

  return (
    <div className="flex items-center gap-6">
      <div className="relative h-40 w-40 shrink-0">
        <PieChart width={160} height={160}>
          <Pie
            data={entries}
            dataKey="count"
            nameKey="severity"
            cx="50%"
            cy="50%"
            innerRadius={48}
            outerRadius={72}
            paddingAngle={2}
            stroke="none"
          >
            {entries.map((entry) => (
              <Cell key={entry.severity} fill={SEVERITY_HEX[entry.severity]} />
            ))}
          </Pie>
        </PieChart>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <div className="text-2xl font-extrabold text-text-strong">{total}</div>
          <div className="text-xs font-medium text-text-muted">findings</div>
        </div>
      </div>
      <div className="flex flex-col gap-2">
        {entries.map((entry) => (
          <div key={entry.severity} className="flex items-center gap-2 text-sm">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: SEVERITY_HEX[entry.severity] }}
            />
            <span className="capitalize text-text-body">{entry.severity}</span>
            <span className="text-text-muted">{entry.count}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ProgressRing({
  value,
  size = 56,
  label,
}: {
  value: number;
  size?: number;
  label?: string;
}) {
  const animated = useCountUp(value, 800);
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, value));
  const animatedClamped = Math.max(0, Math.min(100, animated));
  const offset = circumference - (animatedClamped / 100) * circumference;

  // Color reflects the target value, not the in-flight animated one, so it
  // doesn't flicker through every band as the ring sweeps up from zero.
  // Uses the theme tokens (not fixed hex) so it brightens correctly in dark mode.
  const color =
    clamped >= 75
      ? "var(--color-status-good)"
      : clamped >= 40
        ? "var(--color-sev-medium)"
        : "var(--color-sev-critical)";

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-border-divider)"
          strokeWidth={4}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={4}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center text-xs font-bold text-text-strong">
        {label ?? `${Math.round(animatedClamped)}%`}
      </div>
    </div>
  );
}

export function Drawer({
  title,
  open,
  onClose,
  children,
}: {
  title: string;
  open: boolean;
  onClose: () => void;
  children: ReactNode;
}) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div
        className="absolute inset-0 bg-black/30"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative z-10 flex h-full w-full max-w-lg flex-col border-l border-border-card bg-surface-card shadow-xl">
        <div className="flex items-center justify-between border-b border-border-card px-5 py-4">
          <h2 className="text-[14px] font-bold text-text-strong">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md px-2 py-1 text-[13px] font-semibold text-text-muted hover:bg-surface-subtle hover:text-text-strong"
          >
            Close
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
      </div>
    </div>
  );
}

export function Spinner() {
  return (
    <div
      className="h-4 w-4 animate-spin rounded-full border-2 border-border-strong border-t-primary"
      role="status"
      aria-label="Loading"
    />
  );
}
