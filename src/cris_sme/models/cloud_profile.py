# Synthetic cloud posture models used to generate findings through control evaluation.
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class IamProfile(BaseModel):
    """Minimal IAM posture captured from a provider-neutral SME identity environment."""

    privileged_accounts: int = Field(..., ge=0)
    privileged_accounts_without_mfa: int = Field(..., ge=0)
    overprivileged_accounts: int = Field(..., ge=0)
    stale_service_principals: int = Field(..., ge=0)
    rbac_review_age_days: int = Field(..., ge=0)
    conditional_access_enforced_for_admins: bool
    privileged_user_assignments: int = Field(0, ge=0)
    privileged_service_principal_assignments: int = Field(0, ge=0)
    disabled_service_principals: int = Field(0, ge=0)
    signed_in_user_directory_roles: int = Field(0, ge=0)
    signed_in_user_is_directory_admin: bool = False
    visible_directory_role_catalog_entries: int = Field(0, ge=0)
    directory_role_catalog_visible: bool = False
    identity_observability: str = Field(default="partial", min_length=4)
    rbac_review_api_accessible: bool = True
    rbac_review_definition_count: int = Field(0, ge=0)
    rbac_review_privileged_scope_count: int = Field(0, ge=0)
    rbac_review_scope: str = Field(default="unknown", min_length=3)


class NetworkProfile(BaseModel):
    """Minimal network posture captured from a synthetic SME Azure environment."""

    internet_exposed_rdp_assets: int = Field(..., ge=0)
    internet_exposed_ssh_assets: int = Field(..., ge=0)
    permissive_nsg_rules: int = Field(..., ge=0)
    public_storage_endpoints: int = Field(..., ge=0)
    private_endpoints_required: int = Field(..., ge=0)
    private_endpoints_configured: int = Field(..., ge=0)
    private_endpoint_exemptions: int = Field(0, ge=0)
    private_endpoint_requirement_basis: str = Field(default="unspecified", min_length=3)


class DataProfile(BaseModel):
    """Minimal data protection posture captured from a synthetic SME cloud environment."""

    public_storage_assets: int = Field(..., ge=0)
    unencrypted_data_stores: int = Field(..., ge=0)
    backup_coverage_ratio: float = Field(..., ge=0.0, le=1.0)
    retention_policy_coverage_ratio: float = Field(..., ge=0.0, le=1.0)
    key_vault_mfa_enabled: bool
    key_vault_purge_protection_enabled: bool
    key_vault_count: int = Field(0, ge=0)
    key_vault_purge_protected_count: int = Field(0, ge=0)
    key_vault_posture_state: str = Field(default="not_observed", min_length=3)


class MonitoringProfile(BaseModel):
    """Minimal monitoring posture captured from a synthetic SME cloud environment."""

    activity_log_retention_days: int = Field(..., ge=0)
    critical_alert_coverage_ratio: float = Field(..., ge=0.0, le=1.0)
    defender_coverage_ratio: float = Field(..., ge=0.0, le=1.0)
    centralized_logging_enabled: bool
    incident_response_runbooks_enabled: bool


class ComputeProfile(BaseModel):
    """Minimal compute and workload posture captured from a synthetic SME cloud environment."""

    unpatched_critical_vms: int = Field(..., ge=0)
    endpoint_protection_coverage_ratio: float = Field(..., ge=0.0, le=1.0)
    hardened_baseline_coverage_ratio: float = Field(..., ge=0.0, le=1.0)
    workload_backup_agent_coverage_ratio: float = Field(..., ge=0.0, le=1.0)
    linux_password_auth_enabled_vms: int = Field(0, ge=0)


class GovernanceProfile(BaseModel):
    """Minimal governance and cost hygiene posture captured from a synthetic SME cloud environment."""

    tagging_coverage_ratio: float = Field(..., ge=0.0, le=1.0)
    budget_alerts_enabled: bool
    budget_api_accessible: bool = True
    budget_alert_count: int = Field(0, ge=0)
    budget_evidence_state: str = Field(default="observed", min_length=3)
    policy_assignment_coverage_ratio: float = Field(..., ge=0.0, le=1.0)
    orphaned_resource_count: int = Field(..., ge=0)


class CloudProfile(BaseModel):
    """Synthetic cloud governance profile collected before control evaluation."""

    organization_id: str = Field(..., min_length=3)
    organization_name: str = Field(..., min_length=3)
    provider: str = Field(default="azure", min_length=2)
    sector: str = Field(..., min_length=2)
    tenant_scope: str = Field(..., min_length=3)
    iam: IamProfile
    network: NetworkProfile
    data: DataProfile
    monitoring: MonitoringProfile
    compute: ComputeProfile
    governance: GovernanceProfile
    metadata: dict[str, Any] = Field(default_factory=dict)
