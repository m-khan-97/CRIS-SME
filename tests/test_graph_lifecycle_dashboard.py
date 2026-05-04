# Unit tests for graph-context reasoning, finding lifecycle, and dashboard exports.
from pathlib import Path

from cris_sme.controls.compute_controls import evaluate_compute_controls
from cris_sme.controls.data_controls import evaluate_data_controls
from cris_sme.controls.governance_controls import evaluate_governance_controls
from cris_sme.controls.iam_controls import evaluate_iam_controls
from cris_sme.controls.monitoring_controls import evaluate_monitoring_controls
from cris_sme.controls.network_controls import evaluate_network_controls
from cris_sme.engine.graph_context import build_graph_context_summary
from cris_sme.engine.decision_ledger import build_decision_ledger
from cris_sme.engine.lifecycle import enrich_report_finding_lifecycle
from cris_sme.engine.rbom import (
    build_risk_bill_of_materials,
    canonical_report_sha256,
    sign_risk_bill_of_materials,
    verify_risk_bill_of_materials,
    write_risk_bill_of_materials_signature,
    write_risk_bill_of_materials,
)
from cris_sme.engine.scoring import score_findings
from cris_sme.models.cloud_profile import (
    CloudProfile,
    ComputeProfile,
    DataProfile,
    GovernanceProfile,
    IamProfile,
    MonitoringProfile,
    NetworkProfile,
)
from cris_sme.reporting.dashboard import (
    build_dashboard_html,
    build_dashboard_payload,
    write_dashboard_html,
    write_dashboard_payload,
)


def _profile() -> CloudProfile:
    return CloudProfile(
        organization_id="sme-dash-001",
        organization_name="Dashboard Test SME",
        provider="azure",
        sector="Financial Services",
        tenant_scope="Tenant root / Entra ID",
        iam=IamProfile(
            privileged_accounts=3,
            privileged_accounts_without_mfa=2,
            overprivileged_accounts=1,
            stale_service_principals=1,
            rbac_review_age_days=180,
            conditional_access_enforced_for_admins=False,
        ),
        network=NetworkProfile(
            internet_exposed_rdp_assets=1,
            internet_exposed_ssh_assets=1,
            permissive_nsg_rules=2,
            public_storage_endpoints=1,
            private_endpoints_required=2,
            private_endpoints_configured=1,
        ),
        data=DataProfile(
            public_storage_assets=1,
            unencrypted_data_stores=1,
            backup_coverage_ratio=0.6,
            retention_policy_coverage_ratio=0.65,
            key_vault_mfa_enabled=False,
            key_vault_purge_protection_enabled=False,
        ),
        monitoring=MonitoringProfile(
            activity_log_retention_days=30,
            critical_alert_coverage_ratio=0.4,
            defender_coverage_ratio=0.5,
            centralized_logging_enabled=False,
            incident_response_runbooks_enabled=False,
        ),
        compute=ComputeProfile(
            unpatched_critical_vms=1,
            endpoint_protection_coverage_ratio=0.5,
            hardened_baseline_coverage_ratio=0.5,
            workload_backup_agent_coverage_ratio=0.5,
            linux_password_auth_enabled_vms=1,
        ),
        governance=GovernanceProfile(
            tagging_coverage_ratio=0.6,
            budget_alerts_enabled=False,
            policy_assignment_coverage_ratio=0.6,
            orphaned_resource_count=4,
        ),
        metadata={"profile_source": "test"},
    )


def _scoring():
    profiles = [_profile()]
    findings = [
        *evaluate_iam_controls(profiles),
        *evaluate_network_controls(profiles),
        *evaluate_data_controls(profiles),
        *evaluate_monitoring_controls(profiles),
        *evaluate_compute_controls(profiles),
        *evaluate_governance_controls(profiles),
    ]
    return profiles, findings, score_findings(findings)


def test_build_graph_context_summary_detects_toxic_combinations() -> None:
    profiles, _findings, scoring_result = _scoring()

    context = build_graph_context_summary(profiles, scoring_result.prioritized_findings)

    assert context["asset_count"] >= 1
    assert context["relationship_count"] >= 1
    assert context["blast_radius"]["score"] > 0
    assert context["toxic_combinations"]


def test_enrich_report_finding_lifecycle_sets_first_seen_from_history() -> None:
    _profiles, _findings, scoring_result = _scoring()
    report = {
        "generated_at": "2026-04-22T12:00:00Z",
        "prioritized_risks": [
            {
                "control_id": item.finding.control_id,
                "provider": item.finding.metadata.get("provider", "azure"),
                "organization": item.finding.metadata.get("organization_name"),
                "resource_scope": item.finding.resource_scope,
                "score": item.score,
            }
            for item in scoring_result.prioritized_findings[:2]
        ],
    }
    previous = [
        {
            "generated_at": "2026-04-21T12:00:00Z",
            "prioritized_risks": [
                {
                    "control_id": scoring_result.prioritized_findings[0].finding.control_id,
                    "provider": scoring_result.prioritized_findings[0].finding.metadata.get("provider", "azure"),
                    "organization": scoring_result.prioritized_findings[0].finding.metadata.get("organization_name"),
                    "resource_scope": scoring_result.prioritized_findings[0].finding.resource_scope,
                    "score": scoring_result.prioritized_findings[0].score,
                }
            ],
        }
    ]

    summary = enrich_report_finding_lifecycle(report, previous, exception_registry=[])

    assert summary["new_findings"] >= 1
    assert report["prioritized_risks"][0]["lifecycle"]["first_seen"] == "2026-04-21T12:00:00Z"
    assert report["prioritized_risks"][0]["lifecycle"]["is_new"] is False


def test_build_decision_ledger_records_opened_recurred_changed_and_resolved() -> None:
    current_report = {
        "generated_at": "2026-04-22T12:00:00Z",
        "collector_mode": "mock",
        "overall_risk_score": 42.0,
        "evaluation_context": {"non_compliant_findings": 2},
        "run_metadata": {"run_id": "run_current_001"},
        "prioritized_risks": [
            {
                "finding_id": "fdg_recurred",
                "control_id": "IAM-001",
                "provider": "azure",
                "organization": "Ledger SME",
                "resource_scope": "tenant",
                "score": 60.0,
                "priority": "High",
                "lifecycle": {"status": "open"},
                "evidence_quality": {"sufficiency": "sufficient"},
                "finding_trace": {"evidence_refs": ["evidence:fdg_recurred:1"]},
            },
            {
                "finding_id": "fdg_opened",
                "control_id": "NET-001",
                "provider": "azure",
                "organization": "Ledger SME",
                "resource_scope": "subscription",
                "score": 80.0,
                "priority": "Immediate",
                "lifecycle": {"status": "open"},
                "evidence_quality": {"sufficiency": "partial"},
                "finding_trace": {"evidence_refs": ["evidence:fdg_opened:1"]},
            },
        ],
    }
    previous_report = {
        "generated_at": "2026-04-21T12:00:00Z",
        "collector_mode": "mock",
        "run_metadata": {"run_id": "run_previous_001"},
        "prioritized_risks": [
            {
                "finding_id": "fdg_recurred",
                "control_id": "IAM-001",
                "provider": "azure",
                "organization": "Ledger SME",
                "resource_scope": "tenant",
                "score": 50.0,
                "priority": "High",
                "lifecycle": {"status": "open"},
            },
            {
                "finding_id": "fdg_resolved",
                "control_id": "DATA-001",
                "provider": "azure",
                "organization": "Ledger SME",
                "resource_scope": "storage",
                "score": 70.0,
                "priority": "High",
                "lifecycle": {"status": "open"},
            },
        ],
    }

    ledger = build_decision_ledger(current_report, [previous_report])
    event_types = {event.event_type.value for event in ledger.events}

    assert ledger.current_run_id == "run_current_001"
    assert ledger.previous_run_id == "run_previous_001"
    assert "assessment_recorded" in event_types
    assert "finding_opened" in event_types
    assert "finding_recurred" in event_types
    assert "score_changed" in event_types
    assert "finding_resolved" in event_types
    assert any(event.evidence_refs for event in ledger.events)


def test_build_decision_ledger_defaults_to_same_evaluation_mode() -> None:
    current_report = {
        "generated_at": "2026-04-23T12:00:00Z",
        "collector_mode": "mock",
        "evaluation_dataset": {"source_types": ["synthetic"]},
        "run_metadata": {"run_id": "run_mock_current"},
        "prioritized_risks": [
            {
                "finding_id": "fdg_same_mode",
                "control_id": "IAM-001",
                "provider": "azure",
                "organization": "Ledger SME",
                "resource_scope": "tenant",
                "score": 40.0,
                "lifecycle": {"status": "open"},
            }
        ],
    }
    older_same_mode = {
        "generated_at": "2026-04-21T12:00:00Z",
        "collector_mode": "mock",
        "evaluation_dataset": {"source_types": ["synthetic"]},
        "run_metadata": {"run_id": "run_mock_previous"},
        "prioritized_risks": [
            {
                "finding_id": "fdg_same_mode",
                "control_id": "IAM-001",
                "provider": "azure",
                "organization": "Ledger SME",
                "resource_scope": "tenant",
                "score": 35.0,
                "lifecycle": {"status": "open"},
            }
        ],
    }
    newer_different_mode = {
        "generated_at": "2026-04-22T12:00:00Z",
        "collector_mode": "azure",
        "evaluation_dataset": {"source_types": ["live_real"]},
        "run_metadata": {"run_id": "run_live_newer"},
        "prioritized_risks": [],
    }

    ledger = build_decision_ledger(
        current_report,
        [older_same_mode, newer_different_mode],
    )

    assert ledger.comparison_basis == "same_evaluation_mode"
    assert ledger.current_evaluation_mode == "synthetic_baseline"
    assert ledger.previous_evaluation_mode == "synthetic_baseline"
    assert ledger.previous_run_id == "run_mock_previous"
    assert {event.event_type.value for event in ledger.events} >= {
        "finding_recurred",
        "score_changed",
    }


def test_build_risk_bill_of_materials_hashes_report_and_artifacts(tmp_path: Path) -> None:
    artifact_path = tmp_path / "report.html"
    artifact_path.write_text("<html>risk</html>", encoding="utf-8")
    report = {
        "generated_at": "2026-04-23T12:00:00Z",
        "collector_mode": "mock",
        "report_schema_version": "2.0.0",
        "run_metadata": {
            "run_id": "run_rbom_001",
            "engine_version": "2.0.0",
            "providers_in_scope": ["azure"],
            "policy_pack": {"policy_pack_version": "2026.04.0"},
        },
        "prioritized_risks": [
            {
                "finding_id": "fdg_rbom",
                "control_id": "NET-001",
                "evidence_quality": {"sufficiency": "partial"},
                "finding_trace": {"evidence_refs": ["evidence:fdg_rbom:1"]},
            }
        ],
        "decision_ledger": {
            "events": [
                {"event_type": "assessment_recorded"},
                {"event_type": "finding_opened"},
            ]
        },
    }

    rbom = build_risk_bill_of_materials(
        report,
        artifact_paths={"html_report": artifact_path},
    )
    rbom_path = write_risk_bill_of_materials(
        rbom,
        tmp_path / "cris_sme_risk_bill_of_materials.json",
    )

    assert rbom_path.exists()
    assert rbom.run_id == "run_rbom_001"
    assert rbom.policy_pack_version == "2026.04.0"
    assert rbom.control_ids == ["NET-001"]
    assert rbom.finding_ids == ["fdg_rbom"]
    assert rbom.evidence_refs == ["evidence:fdg_rbom:1"]
    assert rbom.evidence_sufficiency_counts == {"partial": 1}
    assert rbom.decision_ledger_event_counts["finding_opened"] == 1
    assert rbom.artifacts[0].artifact_name == "html_report"
    assert len(rbom.artifacts[0].sha256) == 64


def test_canonical_report_hash_excludes_rbom_self_reference() -> None:
    report = {
        "generated_at": "2026-04-23T12:00:00Z",
        "run_metadata": {"run_id": "run_hash_001"},
        "report_artifacts": {"json_report": "report.json"},
    }
    baseline = canonical_report_sha256(report)
    report["risk_bill_of_materials"] = {"canonical_report_sha256": "different"}
    report["report_artifacts"]["risk_bill_of_materials"] = "rbom.json"

    assert canonical_report_sha256(report) == baseline


def test_verify_risk_bill_of_materials_passes_and_detects_tampering(tmp_path: Path) -> None:
    artifact_path = tmp_path / "artifact.txt"
    artifact_path.write_text("original", encoding="utf-8")
    report = {
        "generated_at": "2026-04-23T12:00:00Z",
        "collector_mode": "mock",
        "report_schema_version": "2.0.0",
        "run_metadata": {
            "run_id": "run_verify_001",
            "engine_version": "2.0.0",
            "providers_in_scope": ["azure"],
            "policy_pack": {"policy_pack_version": "2026.04.0"},
        },
        "prioritized_risks": [],
    }
    rbom = build_risk_bill_of_materials(
        report,
        artifact_paths={"text_artifact": artifact_path},
    )
    report["risk_bill_of_materials"] = rbom.model_dump(mode="json")
    report_path = tmp_path / "report.json"
    rbom_path = tmp_path / "rbom.json"
    report_path.write_text(__import__("json").dumps(report), encoding="utf-8")
    write_risk_bill_of_materials(rbom, rbom_path)

    result = verify_risk_bill_of_materials(
        report_path=report_path,
        rbom_path=rbom_path,
        base_dir=tmp_path,
    )
    assert result.verified is True
    assert result.checked_artifact_count == 1

    artifact_path.write_text("tampered", encoding="utf-8")
    tampered = verify_risk_bill_of_materials(
        report_path=report_path,
        rbom_path=rbom_path,
        base_dir=tmp_path,
    )
    assert tampered.verified is False
    assert tampered.mismatched_artifacts == ["text_artifact"]


def test_verify_risk_bill_of_materials_checks_detached_signature(tmp_path: Path) -> None:
    report = {
        "generated_at": "2026-04-23T12:00:00Z",
        "collector_mode": "mock",
        "report_schema_version": "2.0.0",
        "run_metadata": {
            "run_id": "run_signature_001",
            "engine_version": "2.0.0",
            "providers_in_scope": ["azure"],
            "policy_pack": {"policy_pack_version": "2026.04.0"},
        },
        "prioritized_risks": [],
    }
    rbom = build_risk_bill_of_materials(report)
    signature = sign_risk_bill_of_materials(
        rbom,
        signing_key="test-secret",
        key_id="test-key",
        signed_at="2026-04-23T12:01:00Z",
    )
    report["risk_bill_of_materials"] = rbom.model_dump(mode="json")
    report_path = tmp_path / "report.json"
    rbom_path = tmp_path / "rbom.json"
    signature_path = tmp_path / "rbom.signature.json"
    report_path.write_text(__import__("json").dumps(report), encoding="utf-8")
    write_risk_bill_of_materials(rbom, rbom_path)
    write_risk_bill_of_materials_signature(signature, signature_path)

    verified = verify_risk_bill_of_materials(
        report_path=report_path,
        rbom_path=rbom_path,
        signature_path=signature_path,
        signing_key="test-secret",
        base_dir=tmp_path,
    )
    assert verified.verified is True
    assert verified.signature_verified is True
    assert verified.signature_key_id == "test-key"

    wrong_key = verify_risk_bill_of_materials(
        report_path=report_path,
        rbom_path=rbom_path,
        signature_path=signature_path,
        signing_key="wrong-secret",
        base_dir=tmp_path,
    )
    assert wrong_key.verified is False
    assert wrong_key.signature_verified is False
    assert "RBOM signature mismatch." in wrong_key.errors


def test_dashboard_payload_and_html_are_written(tmp_path: Path) -> None:
    _profiles, _findings, scoring_result = _scoring()
    report = {
        "generated_at": "2026-04-22T12:00:00Z",
        "collector_mode": "mock",
        "overall_risk_score": scoring_result.overall_risk_score,
        "evaluation_context": {
            "evaluated_profiles": 1,
        },
        "prioritized_risks": [
            {
                "control_id": item.finding.control_id,
                "title": item.finding.title,
                "category": item.finding.category.value,
                "priority": item.priority,
                "score": item.score,
                "organization": item.finding.metadata.get("organization_name"),
                "evidence": item.finding.evidence,
                "confidence_calibration": {
                    "observed_confidence": item.breakdown.observed_confidence,
                    "calibrated_confidence": item.breakdown.calibrated_confidence,
                },
                "lifecycle": {"status": "open"},
                "evidence_quality": {"observation_class": "observed"},
            }
            for item in scoring_result.prioritized_findings[:5]
        ],
        "category_scores": scoring_result.category_scores,
        "history_comparison": {"overall_trend": []},
        "compliance": {"frameworks_covered": ["ISO 27001"]},
        "cyber_essentials_readiness": {"overall_readiness_score": 60.0},
        "collector_coverage": [],
        "graph_context": {
            "blast_radius": {"score": 55.0, "band": "medium"},
            "toxic_combinations": [],
            "top_exposure_chains": [],
            "assets": [],
            "relationships": [],
        },
        "budget_aware_remediation": {"budget_profiles": []},
        "action_plan_30_day": {"phases": []},
    }

    payload = build_dashboard_payload(report, [])
    payload_path = write_dashboard_payload(payload, tmp_path)
    html = build_dashboard_html(payload)
    html_path = write_dashboard_html(html, tmp_path / "dashboard.html")

    assert payload_path.exists()
    assert html_path.exists()
    assert "Risk Decision Console" in html
