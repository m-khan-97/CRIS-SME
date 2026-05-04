# Decision provenance graph generation for CRIS-SME assessment artifacts.
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cris_sme.models.platform import (
    DecisionProvenanceEdge,
    DecisionProvenanceGraph,
    DecisionProvenanceNode,
    DecisionProvenancePath,
)


def build_decision_provenance_graph(report: dict[str, Any]) -> DecisionProvenanceGraph:
    """Build a graph connecting evidence, controls, findings, scores, assurance, and decisions."""
    nodes: list[DecisionProvenanceNode] = []
    edges: list[DecisionProvenanceEdge] = []
    paths: list[DecisionProvenancePath] = []
    node_ids: set[str] = set()
    edge_ids: set[str] = set()

    def add_node(node: DecisionProvenanceNode) -> None:
        if node.node_id in node_ids:
            return
        node_ids.add(node.node_id)
        nodes.append(node)

    def add_edge(edge: DecisionProvenanceEdge) -> None:
        if edge.edge_id in edge_ids:
            return
        if edge.source_node_id not in node_ids or edge.target_node_id not in node_ids:
            return
        edge_ids.add(edge.edge_id)
        edges.append(edge)

    snapshot = report.get("evidence_snapshot", {})
    snapshot_id = str(snapshot.get("snapshot_id", "snapshot_current")) if isinstance(snapshot, dict) else "snapshot_current"
    snapshot_node_id = f"snapshot:{snapshot_id}"
    add_node(
        DecisionProvenanceNode(
            node_id=snapshot_node_id,
            node_type="evidence_snapshot",
            label="Evidence Snapshot",
            summary="Normalized evidence captured for deterministic replay.",
            metadata=_compact_dict(snapshot, ("snapshot_id", "collector_mode", "policy_pack_version", "profile_sha256", "finding_sha256")),
        )
    )

    policy_pack = _policy_pack(report)
    policy_node_id = f"policy_pack:{policy_pack}"
    add_node(
        DecisionProvenanceNode(
            node_id=policy_node_id,
            node_type="policy_pack",
            label=f"Policy Pack {policy_pack}",
            summary="Control policy pack used for deterministic evaluation.",
            metadata={"policy_pack_version": policy_pack},
        )
    )
    add_edge(_edge(snapshot_node_id, policy_node_id, "evaluated_against", "Evidence is evaluated against this policy pack."))

    assurance_node_id = "assurance:assessment"
    assurance = report.get("assessment_assurance", {})
    add_node(
        DecisionProvenanceNode(
            node_id=assurance_node_id,
            node_type="assessment_assurance",
            label="Assessment Assurance",
            summary="Trustworthiness score for the assessment artifact.",
            metadata=_compact_dict(assurance, ("assurance_score", "assurance_level", "risk_score_impact")),
        )
    )
    add_edge(_edge(snapshot_node_id, assurance_node_id, "supports_assurance", "Evidence snapshot contributes to assessment assurance."))

    replay_node_id = "replay:assessment"
    replay = _nested_dict(report, "assessment_replay", "replay")
    add_node(
        DecisionProvenanceNode(
            node_id=replay_node_id,
            node_type="assessment_replay",
            label="Assessment Replay",
            summary="Replay verification for deterministic decision reproduction.",
            metadata=_compact_dict(replay, ("snapshot_id", "replayable", "deterministic_match", "overall_risk_delta")),
        )
    )
    add_edge(_edge(snapshot_node_id, replay_node_id, "replayed_by", "Snapshot is replayed without recollecting cloud data."))
    add_edge(_edge(replay_node_id, assurance_node_id, "informs_assurance", "Replay result informs assessment assurance."))

    rbom = report.get("risk_bill_of_materials", {})
    rbom_node_id = "rbom:assessment"
    add_node(
        DecisionProvenanceNode(
            node_id=rbom_node_id,
            node_type="risk_bill_of_materials",
            label="Risk Bill of Materials",
            summary="Integrity manifest for report and downstream artifacts.",
            metadata=_compact_dict(rbom, ("run_id", "canonical_report_sha256", "integrity_algorithm")),
        )
    )
    add_edge(_edge(rbom_node_id, assurance_node_id, "informs_assurance", "RBOM integrity metadata informs assessment assurance."))

    trust_badge = report.get("report_trust_badge", {})
    badge_node_id = "trust_badge:report"
    add_node(
        DecisionProvenanceNode(
            node_id=badge_node_id,
            node_type="report_trust_badge",
            label="Report Trust Badge",
            summary="Stakeholder-facing assurance label for the report.",
            metadata=_compact_dict(trust_badge, ("label", "level", "assurance_score", "risk_score_impact")),
        )
    )
    add_edge(_edge(assurance_node_id, badge_node_id, "summarized_as", "Assessment assurance is summarized as a report trust badge."))

    drift = report.get("control_drift_attribution", {})
    drift_node_id = "drift:control"
    add_node(
        DecisionProvenanceNode(
            node_id=drift_node_id,
            node_type="control_drift_attribution",
            label="Control Drift Attribution",
            summary="Explains control-level score movement between reports.",
            metadata=_compact_dict(drift, ("comparable", "primary_attribution", "overall_risk_delta")),
        )
    )
    add_edge(_edge(snapshot_node_id, drift_node_id, "compared_for_drift", "Current evidence participates in control drift attribution."))

    review_items = _index_review_items(report.get("decision_review_queue", {}))
    contracts = _index_contracts(report.get("provider_evidence_contracts", {}))
    for risk in _risks(report)[:75]:
        finding_id = str(risk.get("finding_id", "finding_unknown"))
        control_id = str(risk.get("control_id", "control_unknown"))
        control_node_id = f"control:{control_id}"
        finding_node_id = f"finding:{finding_id}"
        score_node_id = f"score:{finding_id}"
        sufficiency_node_id = f"evidence_sufficiency:{finding_id}"
        contract_node_id = f"provider_contract:{risk.get('provider', 'azure')}:{control_id}"

        add_node(
            DecisionProvenanceNode(
                node_id=control_node_id,
                node_type="control",
                label=control_id,
                summary=str(risk.get("title", control_id)),
                metadata={"category": risk.get("category"), "rule_version": risk.get("rule_version")},
            )
        )
        add_node(
            DecisionProvenanceNode(
                node_id=finding_node_id,
                node_type="finding",
                label=finding_id,
                summary=str(risk.get("title", finding_id)),
                metadata=_compact_dict(risk, ("finding_id", "control_id", "provider", "priority", "resource_scope")),
            )
        )
        add_node(
            DecisionProvenanceNode(
                node_id=score_node_id,
                node_type="score",
                label=f"Score {risk.get('score', 0)}",
                summary="Deterministic finding score and priority.",
                metadata=_compact_dict(risk, ("score", "priority", "score_breakdown")),
            )
        )
        quality = risk.get("evidence_quality", {})
        add_node(
            DecisionProvenanceNode(
                node_id=sufficiency_node_id,
                node_type="evidence_sufficiency",
                label=f"Evidence {quality.get('sufficiency', 'unknown') if isinstance(quality, dict) else 'unknown'}",
                summary="Evidence sufficiency assessment for the finding decision.",
                metadata=quality if isinstance(quality, dict) else {},
            )
        )
        contract = contracts.get((str(risk.get("provider", "azure")), control_id), {})
        add_node(
            DecisionProvenanceNode(
                node_id=contract_node_id,
                node_type="provider_evidence_contract",
                label=f"{risk.get('provider', 'azure')} {control_id} Contract",
                summary="Provider evidence contract for the control.",
                metadata=_compact_dict(contract, ("contract_id", "support_status", "freshness_hours", "activation_gate")),
            )
        )

        add_edge(_edge(policy_node_id, control_node_id, "defines_control", "Policy pack defines this control."))
        add_edge(_edge(snapshot_node_id, finding_node_id, "produces_finding", "Evidence snapshot produced this finding decision."))
        add_edge(_edge(control_node_id, finding_node_id, "evaluates_to", "Control evaluation produced this finding."))
        add_edge(_edge(contract_node_id, sufficiency_node_id, "sets_evidence_expectation", "Provider contract sets evidence expectations."))
        add_edge(_edge(finding_node_id, sufficiency_node_id, "has_evidence_sufficiency", "Finding includes evidence sufficiency classification."))
        add_edge(_edge(finding_node_id, score_node_id, "scored_as", "Finding is scored by deterministic scoring."))
        add_edge(_edge(score_node_id, drift_node_id, "participates_in_drift", "Finding score participates in drift attribution."))

        review_node_id = None
        review = review_items.get(finding_id)
        if review:
            review_node_id = f"decision_review:{review.get('review_id')}"
            add_node(
                DecisionProvenanceNode(
                    node_id=review_node_id,
                    node_type="decision_review_item",
                    label=str(review.get("recommended_decision", "Decision Review")),
                    summary=str(review.get("rationale", "Governance decision review item.")),
                    metadata=_compact_dict(review, ("review_id", "decision_type", "priority", "owner_hint")),
                )
            )
            add_edge(_edge(score_node_id, review_node_id, "requires_decision", "Scored finding requires governance review."))

        path_nodes = [
            snapshot_node_id,
            policy_node_id,
            control_node_id,
            contract_node_id,
            finding_node_id,
            sufficiency_node_id,
            score_node_id,
        ]
        if review_node_id:
            path_nodes.append(review_node_id)
        path_nodes.extend([assurance_node_id, badge_node_id])
        paths.append(
            DecisionProvenancePath(
                path_id=_stable_id("path", finding_id, control_id),
                finding_id=finding_id,
                control_id=control_id,
                node_ids=path_nodes,
                summary=f"{control_id} decision path links evidence, policy, finding, score, assurance, and review state.",
            )
        )

    return DecisionProvenanceGraph(
        node_count=len(nodes),
        edge_count=len(edges),
        path_count=len(paths),
        node_type_counts=_count_by(nodes, "node_type"),
        edge_type_counts=_count_by(edges, "relationship"),
        nodes=nodes,
        edges=edges,
        top_decision_paths=paths[:30],
    )


def write_decision_provenance_graph(
    graph: DecisionProvenanceGraph,
    output_path: str | Path,
) -> Path:
    """Write a Decision Provenance Graph JSON artifact."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(graph.model_dump(mode="json"), indent=2), encoding="utf-8")
    return path


def _risks(report: dict[str, Any]) -> list[dict[str, Any]]:
    risks = report.get("prioritized_risks", [])
    return [item for item in risks if isinstance(item, dict)] if isinstance(risks, list) else []


def _index_contracts(raw_catalog: object) -> dict[tuple[str, str], dict[str, Any]]:
    if not isinstance(raw_catalog, dict):
        return {}
    contracts = raw_catalog.get("contracts", [])
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    if isinstance(contracts, list):
        for contract in contracts:
            if isinstance(contract, dict):
                indexed[(str(contract.get("provider")), str(contract.get("control_id")))] = contract
    return indexed


def _index_review_items(raw_queue: object) -> dict[str, dict[str, Any]]:
    if not isinstance(raw_queue, dict):
        return {}
    items = raw_queue.get("items", [])
    indexed: dict[str, dict[str, Any]] = {}
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            finding_id = item.get("finding_id")
            if finding_id:
                indexed[str(finding_id)] = item
    return indexed


def _policy_pack(report: dict[str, Any]) -> str:
    metadata = report.get("run_metadata", {})
    if isinstance(metadata, dict):
        policy_pack = metadata.get("policy_pack", {})
        if isinstance(policy_pack, dict):
            return str(policy_pack.get("policy_pack_version", "unknown"))
    snapshot = report.get("evidence_snapshot", {})
    if isinstance(snapshot, dict):
        return str(snapshot.get("policy_pack_version", "unknown"))
    return "unknown"


def _nested_dict(payload: dict[str, Any], *keys: str) -> dict[str, Any]:
    current: object = payload
    for key in keys:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return current if isinstance(current, dict) else {}


def _compact_dict(raw: object, keys: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    return {key: raw.get(key) for key in keys if key in raw}


def _edge(source: str, target: str, relationship: str, explanation: str) -> DecisionProvenanceEdge:
    return DecisionProvenanceEdge(
        edge_id=_stable_id("edge", source, target, relationship),
        source_node_id=source,
        target_node_id=target,
        relationship=relationship,
        explanation=explanation,
    )


def _stable_id(*parts: str) -> str:
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:18]


def _count_by(items: list[object], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(getattr(item, field))
        counts[value] = counts.get(value, 0) + 1
    return counts
