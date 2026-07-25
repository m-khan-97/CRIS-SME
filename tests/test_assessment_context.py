# Tests for normalized CRIS-SME asset/evidence context generation.
from cris_sme.controls.iam_controls import evaluate_iam_controls
from cris_sme.controls.network_controls import evaluate_network_controls
from cris_sme.engine.assessment_context import build_assessment_resource_context
from cris_sme.engine.lineage import build_stable_finding_id
from tests.test_reporting import make_profile


def test_assessment_resource_context_links_findings_to_assets_and_evidence() -> None:
    profiles = [make_profile()]
    findings = [
        *evaluate_iam_controls(profiles),
        *evaluate_network_controls(profiles),
    ]

    context = build_assessment_resource_context(
        profiles,
        findings,
        observed_at="2026-06-15T00:00:00Z",
    )

    assert context.context_model == "cris_sme_resource_evidence_context_v1"
    assert context.assets
    assert context.relationships
    assert context.evidence_records
    assert context.finding_asset_links

    first_finding = findings[0]
    first_finding_id = build_stable_finding_id(first_finding)

    assert first_finding.asset_ids
    assert first_finding.evidence_ids
    assert all(
        evidence_id.startswith(f"evd_{first_finding_id}")
        for evidence_id in first_finding.evidence_ids
    )
    assert any(
        link.finding_id == first_finding_id for link in context.finding_asset_links
    )
    assert any(
        record.source_ref == f"finding:{first_finding_id}"
        for record in context.evidence_records
    )


def test_assessment_resource_context_uses_category_specific_assets() -> None:
    profiles = [make_profile()]
    findings = [
        *evaluate_iam_controls(profiles),
        *evaluate_network_controls(profiles),
    ]

    build_assessment_resource_context(profiles, findings)
    linked_by_control = {
        finding.control_id: finding.asset_ids
        for finding in findings
        if finding.control_id in {"IAM-001", "NET-001"}
    }

    assert linked_by_control["IAM-001"][0].startswith("identity:azure:")
    assert linked_by_control["NET-001"][0].startswith("network:azure:")
