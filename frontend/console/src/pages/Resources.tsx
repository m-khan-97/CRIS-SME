import { useMemo, useState } from "react";
import { Globe2, ShieldAlert } from "lucide-react";
import { useAssessmentReport } from "../context/AssessmentContext";
import { Card, EmptyState, Spinner } from "../components/ui";
import { iconForAssetType } from "../components/assetIcons";

const CRITICALITY_COLORS: Record<string, string> = {
  critical: "text-sev-critical-text border-sev-critical-border bg-sev-critical-bg",
  high: "text-sev-high-text border-sev-high-border bg-sev-high-bg",
  medium: "text-sev-medium-text border-sev-medium-border bg-sev-medium-bg",
  low: "text-status-good-text border-status-good-border bg-status-good-bg",
};

export function Resources() {
  const { data: report, isLoading, error } = useAssessmentReport();

  const [typeFilter, setTypeFilter] = useState("all");

  const assets = useMemo(() => report?.resource_context?.assets ?? [], [report]);
  const relationships = useMemo(() => report?.resource_context?.relationships ?? [], [report]);

  const relationshipCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const rel of relationships) {
      counts[rel.from_asset_id] = (counts[rel.from_asset_id] ?? 0) + 1;
      counts[rel.to_asset_id] = (counts[rel.to_asset_id] ?? 0) + 1;
    }
    return counts;
  }, [relationships]);

  const assetTypes = useMemo(
    () => [...new Set(assets.map((asset) => asset.asset_type))].sort(),
    [assets]
  );

  const filteredAssets = useMemo(
    () =>
      assets.filter(
        (asset) => typeFilter === "all" || asset.asset_type === typeFilter
      ),
    [assets, typeFilter]
  );

  const exposedCount = assets.filter((asset) => asset.internet_exposed).length;

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-8 text-text-muted">
        <Spinner /> Loading resource context…
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
        <h1 className="text-2xl font-semibold text-text-strong">Resources</h1>
        <p className="mt-1 text-sm text-text-muted">
          {assets.length} normalized assets · {relationships.length} relationships
          {exposedCount > 0 && (
            <span className="ml-2 inline-flex items-center gap-1 text-sev-critical-text">
              <ShieldAlert className="h-3.5 w-3.5" />
              {exposedCount} internet exposed
            </span>
          )}
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <select
          className="rounded-md border border-border-strong bg-surface-card px-3 py-2 text-sm text-text-strong"
          value={typeFilter}
          onChange={(event) => setTypeFilter(event.target.value)}
        >
          <option value="all">All asset types</option>
          {assetTypes.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredAssets.map((asset) => {
          const Icon = iconForAssetType(asset.asset_type);
          const criticality = asset.criticality?.toLowerCase();
          const links = relationshipCounts[asset.asset_id] ?? 0;
          return (
            <Card key={asset.asset_id}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-start gap-3">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface-rail text-text-body">
                    <Icon className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="font-medium text-text-strong">{asset.name}</div>
                    <div className="text-xs text-text-muted">{asset.asset_type}</div>
                  </div>
                </div>
                {asset.internet_exposed && (
                  <span className="flex items-center gap-1 rounded-full border border-sev-critical-border bg-sev-critical-bg px-2 py-0.5 text-xs text-sev-critical-text">
                    <Globe2 className="h-3 w-3" />
                    exposed
                  </span>
                )}
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-text-muted">
                <span className="rounded-full border border-border-strong px-2 py-0.5">
                  {asset.scope}
                </span>
                {criticality && (
                  <span
                    className={`rounded-full border px-2 py-0.5 ${
                      CRITICALITY_COLORS[criticality] ??
                      "border-border-strong text-text-body"
                    }`}
                  >
                    {asset.criticality}
                  </span>
                )}
                {links > 0 && (
                  <span className="rounded-full border border-border-strong px-2 py-0.5">
                    {links} link{links === 1 ? "" : "s"}
                  </span>
                )}
              </div>
              <div className="mt-2 truncate font-mono text-xs text-text-muted">
                {asset.asset_id}
              </div>
            </Card>
          );
        })}
      </div>
      {filteredAssets.length === 0 && (
        <EmptyState message="No assets match the current filter." />
      )}
    </div>
  );
}
