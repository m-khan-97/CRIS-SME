# Unit tests for Healthcare IoT / IoMT control evaluation.
from cris_sme.controls.iot_controls import evaluate_iot_controls
from cris_sme.engine.assessment_replay import evaluate_profiles
from cris_sme.engine.lineage import build_collector_coverage
from cris_sme.engine.scoring import score_findings
from cris_sme.models.cloud_profile import (
    CloudProfile,
    ComputeProfile,
    DataProfile,
    GovernanceProfile,
    IamProfile,
    IotProfile,
    MonitoringProfile,
    NetworkProfile,
)
from cris_sme.models.finding import FindingCategory, FindingSeverity
from cris_sme.reporting.json_report import build_json_report


def make_profile(*, iot: IotProfile | None = None) -> CloudProfile:
    return CloudProfile(
        organization_id="iomt-001",
        organization_name="IoMT Research Hospital",
        provider="azure",
        sector="Healthcare",
        tenant_scope="Research subscription / IoT Hub scope",
        iam=IamProfile(
            privileged_accounts=2,
            privileged_accounts_without_mfa=0,
            overprivileged_accounts=0,
            stale_service_principals=0,
            rbac_review_age_days=30,
            conditional_access_enforced_for_admins=True,
            identity_observability="full",
        ),
        network=NetworkProfile(
            internet_exposed_rdp_assets=0,
            internet_exposed_ssh_assets=0,
            permissive_nsg_rules=0,
            public_storage_endpoints=0,
            private_endpoints_required=0,
            private_endpoints_configured=0,
        ),
        data=DataProfile(
            public_storage_assets=0,
            unencrypted_data_stores=0,
            backup_coverage_ratio=1.0,
            retention_policy_coverage_ratio=1.0,
            key_vault_mfa_enabled=True,
            key_vault_purge_protection_enabled=True,
        ),
        monitoring=MonitoringProfile(
            activity_log_retention_days=180,
            critical_alert_coverage_ratio=0.95,
            defender_coverage_ratio=0.95,
            centralized_logging_enabled=True,
            incident_response_runbooks_enabled=True,
        ),
        compute=ComputeProfile(
            unpatched_critical_vms=0,
            endpoint_protection_coverage_ratio=1.0,
            hardened_baseline_coverage_ratio=1.0,
            workload_backup_agent_coverage_ratio=1.0,
        ),
        governance=GovernanceProfile(
            tagging_coverage_ratio=1.0,
            budget_alerts_enabled=True,
            policy_assignment_coverage_ratio=1.0,
            orphaned_resource_count=0,
        ),
        iot=iot,
        metadata={"profile_source": "test"},
    )


def strong_iot_profile() -> IotProfile:
    return IotProfile(
        iot_hub_count=1,
        device_identity_count=12,
        device_identity_observable=True,
        certificate_authority_configured=True,
        shared_access_policy_count=2,
        overbroad_shared_access_policy_count=0,
        diagnostic_settings_enabled=True,
        diagnostic_destination_count=1,
        diagnostic_category_coverage_ratio=0.95,
        defender_iot_enabled=True,
        iot_security_monitoring_observable=True,
        public_network_access_enabled=False,
        allowed_ip_rule_count=1,
        private_endpoint_count=1,
        private_endpoint_required=True,
        message_route_count=2,
        telemetry_retention_days=90,
        telemetry_storage_governed=True,
        iot_key_vault_linked=True,
        iot_secret_rotation_observable=True,
        alert_rule_count=3,
        action_group_count=1,
        clinical_operational_boundary_documented=True,
        evidence_state="observed",
    )


def weak_iot_profile() -> IotProfile:
    return IotProfile(
        iot_hub_count=1,
        device_identity_count=0,
        device_identity_observable=False,
        certificate_authority_configured=False,
        shared_access_policy_count=6,
        overbroad_shared_access_policy_count=2,
        diagnostic_settings_enabled=False,
        diagnostic_destination_count=0,
        diagnostic_category_coverage_ratio=0.25,
        defender_iot_enabled=False,
        iot_security_monitoring_observable=False,
        public_network_access_enabled=True,
        allowed_ip_rule_count=0,
        private_endpoint_count=0,
        private_endpoint_required=True,
        message_route_count=0,
        telemetry_retention_days=7,
        telemetry_storage_governed=False,
        iot_key_vault_linked=False,
        iot_secret_rotation_observable=False,
        alert_rule_count=0,
        action_group_count=0,
        clinical_operational_boundary_documented=False,
        device_evidence_required_count=3,
        clinical_operational_evidence_required_count=2,
        evidence_state="partial",
    )


def test_iot_controls_are_skipped_when_profile_has_no_iot_domain() -> None:
    findings = evaluate_iot_controls([make_profile()])
    assert findings == []


def test_iot_controls_return_no_findings_for_strong_iomt_posture() -> None:
    findings = evaluate_iot_controls([make_profile(iot=strong_iot_profile())])
    assert findings == []


def test_iot_controls_flag_weak_iomt_posture() -> None:
    findings = evaluate_iot_controls([make_profile(iot=weak_iot_profile())])

    control_ids = {finding.control_id for finding in findings}
    assert {
        "IOT-001",
        "IOT-002",
        "IOT-003",
        "IOT-004",
        "IOT-005",
        "IOT-006",
        "IOT-007",
        "IOT-008",
        "IOT-009",
        "IOT-010",
    } == control_ids

    public_access = next(item for item in findings if item.control_id == "IOT-005")
    assert public_access.category == FindingCategory.IOT
    assert public_access.severity == FindingSeverity.HIGH
    assert public_access.metadata["control_category"] == "Healthcare IoT"


def test_iot_controls_participate_in_replay_and_category_scoring() -> None:
    findings = evaluate_profiles([make_profile(iot=weak_iot_profile())])
    scored = score_findings(findings)

    assert any(finding.control_id.startswith("IOT-") for finding in findings)
    assert scored.category_scores["Healthcare IoT"] > 0
    assert scored.overall_risk_score == 0.0


def test_iot_evidence_is_visible_in_report_metadata() -> None:
    profile = make_profile(iot=weak_iot_profile())
    profile.metadata.update(
        {
            "collection_mode": "azure_sdk_subscription_inventory",
            "resource_group_scope": "cris-lab-iomt-test",
            "iot_collection_mode": "azure_iot_hub_cli_inventory",
            "iot_hub_count": 1,
            "iot_device_identity_count": 0,
            "iot_overbroad_shared_access_policy_count": 2,
            "iot_diagnostic_destination_count": 0,
            "iot_defender_enabled": False,
            "iot_public_network_hub_count": 1,
            "iot_private_endpoint_count": 0,
            "iot_alert_rule_count": 0,
        }
    )
    findings = evaluate_iot_controls([profile])
    scored = score_findings(findings)

    report = build_json_report(
        profiles=[profile],
        findings=findings,
        scoring_result=scored,
    )
    collection_details = report["organizations"][0]["collection_details"]
    coverage = build_collector_coverage([profile])[0]

    assert collection_details["iot_collection_mode"] == "azure_iot_hub_cli_inventory"
    assert collection_details["resource_group_scope"] == "cris-lab-iomt-test"
    assert collection_details["evidence_counts"]["iot_hub_count"] == 1
    assert collection_details["evidence_counts"]["iot_public_network_hub_count"] == 1
    assert "azure_iot_hub_cli_inventory" in coverage.observed_domains
