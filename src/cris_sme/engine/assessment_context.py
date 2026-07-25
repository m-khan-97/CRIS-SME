# Normalized asset/evidence context for CRIS-SME assessment findings.
from __future__ import annotations

import hashlib
from pydantic import BaseModel, Field

from cris_sme.engine.graph_context import build_asset_graph
from cris_sme.engine.lineage import build_stable_finding_id, now_iso_utc
from cris_sme.models.cloud_profile import CloudProfile
from cris_sme.models.finding import Finding, FindingCategory
from cris_sme.models.platform import (
    Asset,
    AssetRelationship,
    EvidenceRecord,
    FindingAssetLink,
    ObservationClass,
)


class AssessmentResourceContext(BaseModel):
    """Normalized resource/evidence context for an assessment result."""

    context_model: str = "cris_sme_resource_evidence_context_v1"
    assets: list[Asset] = Field(default_factory=list)
    relationships: list[AssetRelationship] = Field(default_factory=list)
    evidence_records: list[EvidenceRecord] = Field(default_factory=list)
    finding_asset_links: list[FindingAssetLink] = Field(default_factory=list)


ASSET_TYPE_BY_CATEGORY: dict[FindingCategory, str] = {
    FindingCategory.IAM: "identity_plane",
    FindingCategory.NETWORK: "network_surface",
    FindingCategory.DATA: "data_plane",
    FindingCategory.MONITORING: "monitoring_plane",
    FindingCategory.COMPUTE: "compute_plane",
    FindingCategory.GOVERNANCE: "tenant",
    FindingCategory.IOT: "data_plane",
}


def build_assessment_resource_context(
    profiles: list[CloudProfile],
    findings: list[Finding],
    *,
    observed_at: str | None = None,
) -> AssessmentResourceContext:
    """Build normalized assets, evidence records, and finding-resource links."""
    timestamp = observed_at or now_iso_utc()
    graph = build_asset_graph(profiles)
    assets_by_org_and_type = _assets_by_org_and_type(graph.assets)
    evidence_records: list[EvidenceRecord] = []
    finding_asset_links: list[FindingAssetLink] = []

    for finding in findings:
        finding_id = build_stable_finding_id(finding)
        provider = str(finding.metadata.get("provider", "azure"))
        organization_id = str(finding.metadata.get("organization_id", "unknown"))
        asset_ids = _asset_ids_for_finding(
            finding,
            organization_id=organization_id,
            assets_by_org_and_type=assets_by_org_and_type,
        )
        evidence_ids = _evidence_ids_for_finding(finding_id, finding)

        finding.asset_ids = asset_ids
        finding.evidence_ids = evidence_ids
        finding.metadata["asset_ids"] = list(asset_ids)
        finding.metadata["evidence_ids"] = list(evidence_ids)

        evidence_records.extend(
            _evidence_records_for_finding(
                finding=finding,
                finding_id=finding_id,
                evidence_ids=evidence_ids,
                provider=provider,
                observed_at=timestamp,
            )
        )
        finding_asset_links.extend(
            _asset_links_for_finding(
                finding=finding,
                finding_id=finding_id,
                asset_ids=asset_ids,
                evidence_ids=evidence_ids,
            )
        )

    return AssessmentResourceContext(
        assets=graph.assets,
        relationships=graph.relationships,
        evidence_records=evidence_records,
        finding_asset_links=finding_asset_links,
    )


def _assets_by_org_and_type(assets: list[Asset]) -> dict[tuple[str, str], list[Asset]]:
    indexed: dict[tuple[str, str], list[Asset]] = {}
    for asset in assets:
        organization_id = asset.asset_id.rsplit(":", maxsplit=1)[-1]
        indexed.setdefault((organization_id, asset.asset_type), []).append(asset)
    return indexed


def _asset_ids_for_finding(
    finding: Finding,
    *,
    organization_id: str,
    assets_by_org_and_type: dict[tuple[str, str], list[Asset]],
) -> list[str]:
    asset_type = ASSET_TYPE_BY_CATEGORY.get(finding.category, "tenant")
    assets = assets_by_org_and_type.get((organization_id, asset_type))
    if not assets and asset_type != "tenant":
        assets = assets_by_org_and_type.get((organization_id, "tenant"))
    return [asset.asset_id for asset in assets or []]


def _evidence_ids_for_finding(finding_id: str, finding: Finding) -> list[str]:
    if not finding.evidence:
        return [f"evd_{finding_id}_inferred"]
    return [
        f"evd_{finding_id}_{index + 1:02d}"
        for index, _evidence_statement in enumerate(finding.evidence)
    ]


def _evidence_records_for_finding(
    *,
    finding: Finding,
    finding_id: str,
    evidence_ids: list[str],
    provider: str,
    observed_at: str,
) -> list[EvidenceRecord]:
    evidence_statements = finding.evidence or [
        "Control decision has no direct evidence statement and is retained as inferred."
    ]
    records: list[EvidenceRecord] = []
    for evidence_id, statement in zip(evidence_ids, evidence_statements, strict=False):
        records.append(
            EvidenceRecord(
                evidence_id=evidence_id,
                provider=provider,
                collector=str(finding.metadata.get("generated_by", "control_evaluator")),
                record_type=f"control_evidence/{finding.control_id}",
                observation_class=(
                    ObservationClass.OBSERVED
                    if finding.evidence
                    else ObservationClass.INFERRED
                ),
                observed_at=observed_at,
                source_ref=f"finding:{finding_id}",
                freshness_hours=_freshness_hours_for_finding(finding),
                payload={
                    "finding_id": finding_id,
                    "control_id": finding.control_id,
                    "resource_scope": finding.resource_scope,
                    "statement": statement,
                },
            )
        )
    return records


def _asset_links_for_finding(
    *,
    finding: Finding,
    finding_id: str,
    asset_ids: list[str],
    evidence_ids: list[str],
) -> list[FindingAssetLink]:
    links: list[FindingAssetLink] = []
    for asset_id in asset_ids:
        link_id = _stable_link_id(finding_id, asset_id)
        links.append(
            FindingAssetLink(
                link_id=link_id,
                finding_id=finding_id,
                control_id=finding.control_id,
                asset_id=asset_id,
                link_type="affects",
                evidence_ids=list(evidence_ids),
                confidence=finding.confidence,
                metadata={
                    "category": finding.category.value,
                    "resource_scope": finding.resource_scope,
                },
            )
        )
    return links


def _freshness_hours_for_finding(finding: Finding) -> float | None:
    raw_value = finding.metadata.get("freshness_hours")
    if isinstance(raw_value, (int, float)):
        return float(raw_value)
    return None


def _stable_link_id(finding_id: str, asset_id: str) -> str:
    digest = hashlib.sha1(f"{finding_id}|{asset_id}".encode("utf-8")).hexdigest()
    return f"fal_{digest[:14]}"
