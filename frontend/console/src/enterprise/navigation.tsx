import { NavLink, Route, Routes, Navigate, useLocation, useNavigate } from "react-router-dom";
import type { Role } from "./api";

const tabs = [
  ["/", "Assessments"], ["/overview", "Overview"], ["/connections", "Cloud connections"],
  ["/findings", "Findings"], ["/resources", "Resources"], ["/attack-paths", "Attack paths"],
  ["/compliance", "Compliance"], ["/cyber-essentials", "Cyber Essentials"], ["/iomt", "Healthcare IoT"],
  ["/remediation", "Remediation"], ["/personas", "Personas"], ["/evidence", "Evidence"],
  ["/trust", "Trust center"], ["/disclosure", "Disclosure"], ["/governance", "Governance"],
  ["/trend", "Trends"], ["/native-validation", "Native validation"],
  ["/reports", "Reports"], ["/members", "Members"], ["/audit", "Audit"], ["/operations", "Operations"],
];

export function WorkspaceNav({ role }: { role: Role }) {
  const navigate = useNavigate();
  const location = useLocation();
  const visible = tabs.filter(([to]) => to === "/members" ? ["owner", "admin"].includes(role) : ["/audit", "/operations"].includes(to) ? ["owner", "admin", "auditor"].includes(role) : true);
  return <nav aria-label="Workspace" className="border-b border-border-card bg-surface-card px-4 py-2">
    <select aria-label="Navigation" className="md:hidden" value={visible.some(([to]) => to === location.pathname) ? location.pathname : "/"} onChange={e => navigate(e.target.value)}>
      {visible.map(([to, label]) => <option value={to} key={to}>{label}</option>)}
    </select>
    <div className="hidden flex-wrap gap-1 md:flex">{visible.map(([to, label]) => <NavLink key={to} to={to} end className={({ isActive }) => `rounded px-3 py-2 text-sm ${isActive ? "bg-primary text-white" : "text-text-body hover:bg-surface-subtle"}`}>{label}</NavLink>)}</div>
  </nav>;
}

export function EnterpriseFallback() { return <Routes><Route path="*" element={<Navigate to="/" replace />} /></Routes>; }
