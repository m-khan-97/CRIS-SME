# Unit tests for Azure-native recommendation comparison in CRIS-SME.
from cris_sme.engine.native_validation import build_native_validation_summary
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
from cris_sme.models.finding import Finding, FindingCategory, FindingSeverity, RemediationCostTier


def make_profile() -> CloudProfile:
    """Create a compact profile with native recommendation metadata."""
    return CloudProfile(
        organization_id="native-001",
        organization_name="Native Validation SME",
        provider="azure",
        sector="Financial Services",
        tenant_scope="subscription/native-001",
        iam=IamProfile(
            privileged_accounts=1,
            privileged_accounts_without_mfa=0,
            overprivileged_accounts=1,
            stale_service_principals=0,
            rbac_review_age_days=30,
            conditional_access_enforced_for_admins=True,
        ),
        network=NetworkProfile(
            internet_exposed_rdp_assets=0,
            internet_exposed_ssh_assets=1,
            permissive_nsg_rules=1,
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
            activity_log_retention_days=90,
            critical_alert_coverage_ratio=1.0,
            defender_coverage_ratio=1.0,
            centralized_logging_enabled=True,
            incident_response_runbooks_enabled=True,
        ),
        compute=ComputeProfile(
            unpatched_critical_vms=0,
            endpoint_protection_coverage_ratio=1.0,
            hardened_baseline_coverage_ratio=1.0,
            workload_backup_agent_coverage_ratio=1.0,
            linux_password_auth_enabled_vms=0,
        ),
        governance=GovernanceProfile(
            tagging_coverage_ratio=1.0,
            budget_alerts_enabled=True,
            policy_assignment_coverage_ratio=1.0,
            orphaned_resource_count=0,
        ),
        metadata={
            "native_security_recommendations": [
                {
                    "display_name": "All network ports should be restricted on network security groups associated to your virtual machine",
                    "status_code": "Unhealthy",
                    "resource_name": "vm-01",
                },
                {
                    "display_name": "There should be more than one owner assigned to subscriptions",
                    "status_code": "Unhealthy",
                    "resource_name": "subscription-01",
                },
            ]
        },
    )


def make_finding(control_id: str, category: FindingCategory) -> Finding:
    """Create a compact non-compliant finding for native-validation tests."""
    return Finding(
        control_id=control_id,
        title="Synthetic finding",
        category=category,
        severity=FindingSeverity.HIGH,
        evidence=["evidence"],
        resource_scope="subscription/native-001",
        is_compliant=False,
        confidence=0.9,
        exposure=0.8,
        data_sensitivity=0.7,
        remediation_effort=0.4,
        remediation_summary="Fix it",
        remediation_cost_tier=RemediationCostTier.FREE,
        mapping=[],
        metadata={"organization_name": "Native Validation SME"},
    )


def test_build_native_validation_summary_reports_agreement_and_cris_only() -> None:
    profile = make_profile()
    scoring = score_findings(
        [
            make_finding("NET-002", FindingCategory.NETWORK),
            make_finding("CMP-001", FindingCategory.COMPUTE),
        ]
    )

    summary = build_native_validation_summary([profile], scoring.prioritized_findings)

    assert summary["framework"] == "Microsoft Defender for Cloud"
    assert summary["native_unhealthy_recommendation_count"] == 2
    assert summary["agreement_count"] >= 1
    assert summary["cris_only_count"] >= 1
