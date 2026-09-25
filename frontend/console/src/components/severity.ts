export type SeverityLevel = "critical" | "high" | "medium" | "low";

export function normalizeSeverity(value: string): SeverityLevel {
  const normalized = value.trim().toLowerCase();
  if (normalized === "critical" || normalized === "high" || normalized === "medium" || normalized === "low") {
    return normalized;
  }
  return "low";
}
