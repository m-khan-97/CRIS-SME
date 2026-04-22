# Lightweight asset-relationship context graph and risk-chain reasoning for CRIS-SME.
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cris_sme.engine.scoring import ScoredFinding
from cris_sme.models.cloud_profile import CloudProfile
from cris_sme.models.platform import Asset, AssetRelationship


@dataclass(slots=True)
class _GraphBuildResult:
    assets: list[Asset]
    relationships: list[AssetRelationship]


def build_graph_context_summary(
    profiles: list[CloudProfile],
    prioritized_findings: list[ScoredFinding],
) -> dict[str, Any]:
    """Build context-aware exposure summaries from normalized assets and findings."""
    graph = _build_asset_graph(profiles)
    control_ids = {item.finding.control_id for item in prioritized_findings}
    toxic_combinations = _detect_toxic_combinations(control_ids)
    exposure_chains = _build_exposure_chains(toxic_combinations)
    blast_radius = _estimate_blast_radius(profiles, prioritized_findings)

    return {
        "graph_model": "cris_sme_lightweight_asset_context_v1",
        "asset_count": len(graph.assets),
        "relationship_count": len(graph.relationships),
        "blast_radius": blast_radius,
        "toxic_combinations": toxic_combinations,
        "top_exposure_chains": exposure_chains,
        "assets": [
            {
                "asset_id": asset.asset_id,
                "asset_type": asset.asset_type,
                "name": asset.name,
                "scope": asset.scope,
                "criticality": asset.criticality,
                "internet_exposed": asset.internet_exposed,
            }
            for asset in graph.assets[:40]
        ],
        "relationships": [
            {
                "relationship_id": edge.relationship_id,
                "from_asset_id": edge.from_asset_id,
                "to_asset_id": edge.to_asset_id,
                "relationship_type": edge.relationship_type,
                "confidence": edge.confidence,
            }
            for edge in graph.relationships[:80]
        ],
        "coverage_note": (
            "This is a lightweight context graph to improve prioritization signals such as "
            "blast radius and toxic combinations. It is not a full attack-path simulator."
        ),
    }


def _build_asset_graph(profiles: list[CloudProfile]) -> _GraphBuildResult:
    assets: list[Asset] = []
    relationships: list[AssetRelationship] = []

    for profile in profiles:
        tenant_asset_id = f"tenant:{profile.provider}:{profile.organization_id}"
        identity_asset_id = f"identity:{profile.provider}:{profile.organization_id}"
        network_asset_id = f"network:{profile.provider}:{profile.organization_id}"
        data_asset_id = f"data:{profile.provider}:{profile.organization_id}"
        compute_asset_id = f"compute:{profile.provider}:{profile.organization_id}"
        monitoring_asset_id = f"monitoring:{profile.provider}:{profile.organization_id}"

        assets.extend(
            [
                Asset(
                    asset_id=tenant_asset_id,
                    provider=profile.provider,
                    asset_type="tenant",
                    name=profile.organization_name,
                    scope=profile.tenant_scope,
                    criticality="high",
                ),
                Asset(
                    asset_id=identity_asset_id,
                    provider=profile.provider,
                    asset_type="identity_plane",
                    name=f"{profile.organization_name} Identity",
                    scope=profile.tenant_scope,
                    criticality="high",
                ),
                Asset(
                    asset_id=network_asset_id,
                    provider=profile.provider,
                    asset_type="network_surface",
                    name=f"{profile.organization_name} Network Surface",
                    scope=profile.tenant_scope,
                    criticality="high",
                    internet_exposed=(
                        profile.network.internet_exposed_rdp_assets > 0
                        or profile.network.internet_exposed_ssh_assets > 0
                    ),
                ),
                Asset(
                    asset_id=data_asset_id,
                    provider=profile.provider,
                    asset_type="data_plane",
                    name=f"{profile.organization_name} Data Services",
                    scope=profile.tenant_scope,
                    criticality="high",
                    internet_exposed=(
                        profile.data.public_storage_assets > 0
                        or profile.network.public_storage_endpoints > 0
                    ),
                ),
                Asset(
                    asset_id=compute_asset_id,
                    provider=profile.provider,
                    asset_type="compute_plane",
                    name=f"{profile.organization_name} Compute",
                    scope=profile.tenant_scope,
                    criticality="medium",
                    internet_exposed=(
                        profile.network.internet_exposed_rdp_assets > 0
                        or profile.network.internet_exposed_ssh_assets > 0
                    ),
                ),
                Asset(
                    asset_id=monitoring_asset_id,
                    provider=profile.provider,
                    asset_type="monitoring_plane",
                    name=f"{profile.organization_name} Monitoring",
                    scope=profile.tenant_scope,
                    criticality="medium",
                ),
            ]
        )
        relationships.extend(
            [
                _edge(tenant_asset_id, identity_asset_id, "contains_identity"),
                _edge(tenant_asset_id, network_asset_id, "contains_network"),
                _edge(tenant_asset_id, data_asset_id, "contains_data"),
                _edge(tenant_asset_id, compute_asset_id, "contains_compute"),
                _edge(tenant_asset_id, monitoring_asset_id, "contains_monitoring"),
                _edge(identity_asset_id, compute_asset_id, "administers"),
                _edge(network_asset_id, compute_asset_id, "exposes"),
                _edge(compute_asset_id, data_asset_id, "accesses"),
                _edge(monitoring_asset_id, compute_asset_id, "observes"),
                _edge(monitoring_asset_id, data_asset_id, "observes"),
            ]
        )

    return _GraphBuildResult(
        assets=_deduplicate_assets(assets),
        relationships=_deduplicate_relationships(relationships),
    )


def _detect_toxic_combinations(control_ids: set[str]) -> list[dict[str, Any]]:
    combinations: list[dict[str, Any]] = []
    if {"NET-001", "IAM-001"} <= control_ids or {"NET-001", "IAM-002"} <= control_ids:
        combinations.append(
            {
                "combination_id": "toxic_public_admin_plus_identity",
                "title": "Public administrative exposure with privileged identity weakness",
                "impact": "high",
                "control_ids": sorted(control_ids.intersection({"NET-001", "IAM-001", "IAM-002"})),
                "narrative": (
                    "Internet-reachable administrative surfaces combined with identity-control gaps "
                    "can amplify unauthorized access and privilege abuse risk."
                ),
            }
        )
    if {"NET-001", "MON-004"} <= control_ids or {"NET-001", "MON-001"} <= control_ids:
        combinations.append(
            {
                "combination_id": "toxic_exposure_plus_detection_gap",
                "title": "Exposed administrative path with weak detection/response readiness",
                "impact": "high",
                "control_ids": sorted(control_ids.intersection({"NET-001", "MON-001", "MON-004"})),
                "narrative": (
                    "Exposure risk is harder to contain when monitoring retention or incident "
                    "response runbooks are weak."
                ),
            }
        )
    if (
        {"DATA-001", "DATA-004"} <= control_ids
        or {"NET-003", "DATA-002"} <= control_ids
    ):
        combinations.append(
            {
                "combination_id": "toxic_data_exposure_plus_weak_protection",
                "title": "Externally reachable data paths with weak protection controls",
                "impact": "high",
                "control_ids": sorted(
                    control_ids.intersection({"DATA-001", "DATA-002", "DATA-004", "NET-003"})
                ),
                "narrative": (
                    "Public data exposure combined with weak encryption or key governance "
                    "materially raises confidentiality and regulatory risk."
                ),
            }
        )
    if {"CMP-005", "NET-001"} <= control_ids:
        combinations.append(
            {
                "combination_id": "toxic_password_ssh_plus_exposure",
                "title": "Password-based SSH on exposed workloads",
                "impact": "medium",
                "control_ids": ["CMP-005", "NET-001"],
                "narrative": (
                    "Password-authenticated admin access over exposed channels increases brute-force "
                    "and credential-stuffing risk."
                ),
            }
        )
    return combinations


def _build_exposure_chains(
    toxic_combinations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    chains: list[dict[str, Any]] = []
    for item in toxic_combinations:
        control_ids = item.get("control_ids", [])
        if not isinstance(control_ids, list):
            control_ids = []
        chains.append(
            {
                "chain_id": f"chain_{item.get('combination_id', 'unknown')}",
                "title": item.get("title", "Risk chain"),
                "path": [
                    "internet_exposure",
                    "identity_or_workload_entry",
                    "lateral_or_data_impact",
                ],
                "supporting_controls": control_ids,
                "risk_signal": item.get("impact", "medium"),
            }
        )
    return chains


def _estimate_blast_radius(
    profiles: list[CloudProfile],
    prioritized_findings: list[ScoredFinding],
) -> dict[str, Any]:
    internet_exposed_assets = sum(
        profile.network.internet_exposed_rdp_assets
        + profile.network.internet_exposed_ssh_assets
        + profile.network.public_storage_endpoints
        for profile in profiles
    )
    privileged_issues = sum(
        1
        for item in prioritized_findings
        if item.finding.control_id.startswith("IAM-")
    )
    high_urgency = sum(
        1
        for item in prioritized_findings
        if item.priority in {"Immediate", "High"}
    )
    score = min(
        100.0,
        (internet_exposed_assets * 10.0)
        + (privileged_issues * 4.5)
        + (high_urgency * 2.0),
    )
    if score >= 70:
        band = "high"
    elif score >= 40:
        band = "medium"
    else:
        band = "low"

    return {
        "score": round(score, 2),
        "band": band,
        "internet_exposed_asset_count": int(internet_exposed_assets),
        "privileged_issue_count": int(privileged_issues),
        "high_urgency_finding_count": int(high_urgency),
        "explanation": (
            "Blast-radius estimate combines internet exposure anchors, privileged-control "
            "weaknesses, and urgent findings to highlight potential spread/impact context."
        ),
    }


def _edge(from_asset_id: str, to_asset_id: str, relationship_type: str) -> AssetRelationship:
    relationship_id = f"{from_asset_id}->{to_asset_id}:{relationship_type}"
    return AssetRelationship(
        relationship_id=relationship_id,
        from_asset_id=from_asset_id,
        to_asset_id=to_asset_id,
        relationship_type=relationship_type,
    )


def _deduplicate_assets(assets: list[Asset]) -> list[Asset]:
    by_id = {asset.asset_id: asset for asset in assets}
    return list(by_id.values())


def _deduplicate_relationships(
    relationships: list[AssetRelationship],
) -> list[AssetRelationship]:
    by_id = {relationship.relationship_id: relationship for relationship in relationships}
    return list(by_id.values())
