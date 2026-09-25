import { createElement, useMemo, useState } from "react";
import {
  Background,
  Handle,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Globe2 } from "lucide-react";
import { useAssessmentReport } from "../context/AssessmentContext";
import type { AssetRelationship, CrisAsset, PrioritizedRisk } from "../api/types";
import { Drawer, EmptyState, SeverityBadge, Spinner } from "../components/ui";
import { iconForAssetType } from "../components/assetIcons";

const SEVERITY_RANK: Record<string, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
};

const SEVERITY_RING: Record<string, string> = {
  critical: "ring-2 ring-red-500",
  high: "ring-2 ring-orange-500",
  medium: "ring-2 ring-amber-500",
  low: "ring-2 ring-emerald-500",
};

function organizationOf(assetId: string): string {
  const parts = assetId.split(":");
  return parts[parts.length - 1] ?? assetId;
}

function layoutAssets(assets: CrisAsset[], relationships: AssetRelationship[]) {
  const ids = assets.map((asset) => asset.asset_id);
  const idSet = new Set(ids);
  const incoming = new Map<string, number>(ids.map((id) => [id, 0]));
  const depth = new Map<string, number>(ids.map((id) => [id, 0]));

  const relevantRels = relationships.filter(
    (rel) => idSet.has(rel.from_asset_id) && idSet.has(rel.to_asset_id)
  );

  for (const rel of relevantRels) {
    incoming.set(rel.to_asset_id, (incoming.get(rel.to_asset_id) ?? 0) + 1);
  }

  for (let i = 0; i < ids.length; i += 1) {
    let changed = false;
    for (const rel of relevantRels) {
      const candidate = (depth.get(rel.from_asset_id) ?? 0) + 1;
      if (candidate > (depth.get(rel.to_asset_id) ?? 0)) {
        depth.set(rel.to_asset_id, candidate);
        changed = true;
      }
    }
    if (!changed) break;
  }

  const byDepth = new Map<number, string[]>();
  for (const id of ids) {
    const d = depth.get(id) ?? 0;
    if (!byDepth.has(d)) byDepth.set(d, []);
    byDepth.get(d)!.push(id);
  }

  const positions = new Map<string, { x: number; y: number }>();
  const xGap = 300;
  const yGap = 120;
  for (const [d, idsAtDepth] of byDepth) {
    idsAtDepth.forEach((id, index) => {
      positions.set(id, { x: d * xGap, y: index * yGap });
    });
  }

  return positions;
}

function AssetNode({ data }: NodeProps) {
  const asset = data.asset as CrisAsset;
  const severity = data.severity as string | undefined;
  const ringClass = severity ? SEVERITY_RING[severity] ?? "" : "";

  return (
    <div
      className={`flex min-w-[180px] items-center gap-2 rounded-lg border border-border-strong bg-surface-subtle px-3 py-2 shadow-sm ${ringClass}`}
    >
      <Handle type="target" position={Position.Left} className="!bg-text-faint" />
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-surface-rail text-text-body">
        {createElement(iconForAssetType(asset.asset_type), { className: "h-4 w-4" })}
      </div>
      <div className="min-w-0">
        <div className="truncate text-xs font-medium text-text-strong">{asset.name}</div>
        <div className="text-[10px] text-text-muted">{asset.asset_type}</div>
      </div>
      {asset.internet_exposed && (
        <Globe2 className="h-3.5 w-3.5 shrink-0 text-sev-critical-text" />
      )}
      <Handle type="source" position={Position.Right} className="!bg-text-faint" />
    </div>
  );
}

const nodeTypes = { asset: AssetNode };

export function AttackPaths() {
  const { data: report, isLoading, error } = useAssessmentReport();

  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);

  const allAssets = useMemo(() => report?.resource_context?.assets ?? [], [report]);
  const allRelationships = useMemo(() => report?.resource_context?.relationships ?? [], [report]);
  const risks = useMemo(() => report?.prioritized_risks ?? [], [report]);

  const organizations = useMemo(() => {
    const ids = new Set(allAssets.map((asset) => organizationOf(asset.asset_id)));
    return [...ids].sort();
  }, [allAssets]);

  const [orgFilter, setOrgFilter] = useState<string>("");
  const activeOrg = orgFilter || organizations[0] || "";

  const assets = useMemo(
    () => allAssets.filter((asset) => organizationOf(asset.asset_id) === activeOrg),
    [allAssets, activeOrg]
  );
  const relationships = useMemo(() => {
    const ids = new Set(assets.map((asset) => asset.asset_id));
    return allRelationships.filter(
      (rel) => ids.has(rel.from_asset_id) && ids.has(rel.to_asset_id)
    );
  }, [allRelationships, assets]);

  const findingsByAsset = useMemo(() => {
    const map = new Map<string, PrioritizedRisk[]>();
    for (const risk of risks) {
      for (const assetId of risk.asset_ids ?? []) {
        if (!map.has(assetId)) map.set(assetId, []);
        map.get(assetId)!.push(risk);
      }
    }
    return map;
  }, [risks]);

  const positions = useMemo(() => layoutAssets(assets, relationships), [assets, relationships]);

  const nodes: Node[] = useMemo(
    () =>
      assets.map((asset) => {
        const findings = findingsByAsset.get(asset.asset_id) ?? [];
        const topSeverity = findings
          .map((f) => f.severity.toLowerCase())
          .sort((a, b) => (SEVERITY_RANK[b] ?? 0) - (SEVERITY_RANK[a] ?? 0))[0];
        return {
          id: asset.asset_id,
          type: "asset",
          position: positions.get(asset.asset_id) ?? { x: 0, y: 0 },
          data: { asset, severity: topSeverity },
        };
      }),
    [assets, positions, findingsByAsset]
  );

  const edges: Edge[] = useMemo(
    () =>
      relationships.map((rel) => {
        const isStructural = rel.relationship_type.startsWith("contains_");
        return {
          id: rel.relationship_id,
          source: rel.from_asset_id,
          target: rel.to_asset_id,
          label: isStructural ? undefined : rel.relationship_type.replaceAll("_", " "),
          labelStyle: { fill: "#cbd5e1", fontSize: 10 },
          labelBgStyle: { fill: "#0f172a", fillOpacity: 0.9 },
          labelBgPadding: [4, 2] as [number, number],
          style: {
            stroke: isStructural ? "var(--color-text-faint)" : "var(--color-text-muted)",
            strokeDasharray: isStructural ? "4 4" : undefined,
          },
          animated: rel.relationship_type === "exposes" || rel.relationship_type === "accesses",
        };
      }),
    [relationships]
  );

  const selectedAsset = assets.find((asset) => asset.asset_id === selectedAssetId) ?? null;

  const blastRadius = useMemo(() => {
    if (!selectedAssetId) return [];
    const adjacency = new Map<string, { id: string; via: string }[]>();
    for (const rel of relationships) {
      if (!adjacency.has(rel.from_asset_id)) adjacency.set(rel.from_asset_id, []);
      if (!adjacency.has(rel.to_asset_id)) adjacency.set(rel.to_asset_id, []);
      adjacency.get(rel.from_asset_id)!.push({ id: rel.to_asset_id, via: rel.relationship_type });
      adjacency
        .get(rel.to_asset_id)!
        .push({ id: rel.from_asset_id, via: `${rel.relationship_type} (reverse)` });
    }

    const visited = new Map<string, { hops: number; via: string }>();
    let frontier = [selectedAssetId];
    visited.set(selectedAssetId, { hops: 0, via: "" });
    for (let hop = 1; hop <= 2; hop += 1) {
      const next: string[] = [];
      for (const id of frontier) {
        for (const neighbor of adjacency.get(id) ?? []) {
          if (!visited.has(neighbor.id)) {
            visited.set(neighbor.id, { hops: hop, via: neighbor.via });
            next.push(neighbor.id);
          }
        }
      }
      frontier = next;
    }
    visited.delete(selectedAssetId);
    return [...visited.entries()]
      .map(([id, info]) => ({ asset: assets.find((a) => a.asset_id === id), ...info }))
      .filter((entry) => entry.asset)
      .sort((a, b) => a.hops - b.hops);
  }, [selectedAssetId, relationships, assets]);

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-8 text-text-muted">
        <Spinner /> Loading attack path data…
      </div>
    );
  }

  if (error) {
    return <div className="p-8"><EmptyState message={`Failed to load report: ${(error as Error).message}`} /></div>;
  }

  if (!report || allAssets.length === 0) {
    return (
      <div className="p-8"><EmptyState message="No resource context available yet. Run an assessment with resource context enabled to populate the attack path view." /></div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-4 p-[24px_26px_28px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-text-strong">Attack Paths</h1>
          <p className="mt-1 text-sm text-text-muted">
            Asset relationships and blast radius for {activeOrg}. Click a node for
            details and exposure analysis.
          </p>
        </div>
        <select
          className="rounded-md border border-border-strong bg-surface-card px-3 py-2 text-sm text-text-strong"
          value={activeOrg}
          onChange={(event) => setOrgFilter(event.target.value)}
        >
          {organizations.map((org) => (
            <option key={org} value={org}>
              {org}
            </option>
          ))}
        </select>
      </div>

      <div className="h-[560px] overflow-hidden rounded-xl border border-border-card bg-surface-card">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          onNodeClick={(_, node) => setSelectedAssetId(node.id)}
          fitView
          proOptions={{ hideAttribution: true }}
        >
          <Background color="var(--color-border-strong)" gap={24} />
        </ReactFlow>
      </div>

      <Drawer
        title={selectedAsset?.name ?? ""}
        open={!!selectedAsset}
        onClose={() => setSelectedAssetId(null)}
      >
        {selectedAsset && (
          <div className="flex flex-col gap-4 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border border-border-strong px-2 py-0.5 text-xs text-text-body">
                {selectedAsset.asset_type}
              </span>
              <span className="rounded-full border border-border-strong px-2 py-0.5 text-xs text-text-body">
                {selectedAsset.criticality}
              </span>
              {selectedAsset.internet_exposed && (
                <span className="flex items-center gap-1 rounded-full border border-sev-critical-border bg-sev-critical-bg px-2 py-0.5 text-xs text-sev-critical-text">
                  <Globe2 className="h-3 w-3" />
                  internet exposed
                </span>
              )}
            </div>
            <div className="font-mono text-xs text-text-muted">
              {selectedAsset.asset_id}
            </div>

            <div>
              <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">
                Linked findings
              </div>
              {(findingsByAsset.get(selectedAsset.asset_id) ?? []).length === 0 ? (
                <p className="text-xs text-text-muted">No findings reference this asset.</p>
              ) : (
                <div className="flex flex-col gap-2">
                  {(findingsByAsset.get(selectedAsset.asset_id) ?? []).map((risk) => (
                    <div
                      key={risk.finding_id}
                      className="flex items-center justify-between gap-2 rounded-md border border-border-card px-2 py-1.5"
                    >
                      <div className="min-w-0">
                        <div className="truncate text-text-strong">{risk.title}</div>
                        <div className="font-mono text-[10px] text-text-muted">
                          {risk.control_id}
                        </div>
                      </div>
                      <SeverityBadge severity={risk.severity} />
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div>
              <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-text-muted">
                Blast radius (within 2 hops)
              </div>
              {blastRadius.length === 0 ? (
                <p className="text-xs text-text-muted">
                  No connected assets within 2 hops.
                </p>
              ) : (
                <div className="flex flex-col gap-2">
                  {blastRadius.map((entry) => (
                    <div
                      key={entry.asset!.asset_id}
                      className="flex items-center justify-between gap-2 rounded-md border border-border-card px-2 py-1.5"
                    >
                      <div className="min-w-0">
                        <div className="truncate text-text-strong">
                          {entry.asset!.name}
                        </div>
                        <div className="text-[10px] text-text-muted">
                          via {entry.via.replaceAll("_", " ")}
                        </div>
                      </div>
                      <span className="rounded-full border border-border-strong px-2 py-0.5 text-xs text-text-muted">
                        {entry.hops} hop{entry.hops === 1 ? "" : "s"}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}
