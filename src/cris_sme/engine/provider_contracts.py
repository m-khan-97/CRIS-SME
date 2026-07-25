# Provider evidence contract generation for CRIS-SME control governance.
from __future__ import annotations

from cris_sme.models.platform import (
    ProviderAuthContract,
    ProviderEvidenceContract,
    ProviderEvidenceCapability,
    ProviderEvidenceContractCatalog,
    ProviderFreshnessPolicy,
    ProviderIdentityContract,
    ProviderLimitation,
    ProviderPermissionContract,
    ProviderScopeContract,
)
from cris_sme.policies import POLICY_PACK_VERSION, load_control_specs


SUPPORTED_PROVIDERS = ("azure", "aws", "gcp")


def build_provider_evidence_contract_catalog(
    *,
    providers: tuple[str, ...] = SUPPORTED_PROVIDERS,
) -> ProviderEvidenceContractCatalog:
    """Build per-provider evidence contracts from the active control specs."""
    specs = load_control_specs()
    contracts: list[ProviderEvidenceContract] = []
    for spec in specs.values():
        for provider in providers:
            support_status = str(
                spec.provider_support.get(provider, "unsupported")
            ).lower()
            freshness_hours = _freshness_hours(spec.domain)
            contracts.append(
                ProviderEvidenceContract(
                    contract_id=f"pec_{provider}_{spec.control_id.lower()}_{spec.version}",
                    provider=provider,
                    control_id=spec.control_id,
                    control_version=spec.version,
                    domain=spec.domain,
                    support_status=support_status,
                    evidence_requirements=list(spec.evidence_requirements),
                    freshness_hours=freshness_hours,
                    sufficiency_policy=_sufficiency_policy(support_status),
                    confidence_penalty_rules=list(spec.confidence_penalty_rules),
                    known_limitations=list(spec.known_limitations),
                    activation_gate=_activation_gate(provider, support_status),
                    identity=_identity_contract(provider),
                    scopes=_scope_contract(provider),
                    auth=_auth_contract(provider),
                    permissions=_permission_contract(
                        provider,
                        spec.domain,
                        support_status,
                    ),
                    evidence_capabilities=[
                        _evidence_capability(
                            provider,
                            spec.control_id,
                            spec.domain,
                            support_status,
                        )
                    ],
                    freshness_policy=_freshness_policy(freshness_hours),
                    limitations=_provider_limitations(
                        provider,
                        spec.control_id,
                        spec.domain,
                        support_status,
                        spec.known_limitations,
                    ),
                )
            )

    return ProviderEvidenceContractCatalog(
        policy_pack_version=POLICY_PACK_VERSION,
        provider_count=len(providers),
        control_count=len(specs),
        contract_count=len(contracts),
        support_status_counts=_support_status_counts(contracts),
        contracts=contracts,
    )


def _freshness_hours(domain: str) -> int:
    normalized = domain.lower()
    if "iam" in normalized:
        return 24
    if "network" in normalized:
        return 24
    if "data" in normalized:
        return 48
    if "monitoring" in normalized:
        return 24
    if "compute" in normalized:
        return 72
    return 168


def _identity_contract(provider: str) -> ProviderIdentityContract:
    if provider == "azure":
        return ProviderIdentityContract(
            identity_type="azure_subscription_tenant",
            account_scope_label="subscription",
            tenant_scope_label="tenant",
            principal_ref="azure_cli_or_default_credential_principal",
            identity_sources=[
                "Azure Resource Manager subscription context",
                "Microsoft Graph tenant context where permissions allow",
            ],
        )
    if provider == "aws":
        return ProviderIdentityContract(
            identity_type="aws_account_organization",
            account_scope_label="account",
            tenant_scope_label="organization",
            principal_ref="aws_caller_identity_principal",
            identity_sources=[
                "AWS STS caller identity",
                "AWS Organizations account context when enabled",
            ],
        )
    return ProviderIdentityContract(
        identity_type="gcp_project_organization",
        account_scope_label="project",
        tenant_scope_label="organization",
        principal_ref="gcp_adc_service_account_or_user_planned",
        identity_sources=[
            "Google Cloud Resource Manager project context",
            "Cloud Identity organization context when enabled",
        ],
    )


def _scope_contract(provider: str) -> ProviderScopeContract:
    if provider == "azure":
        return ProviderScopeContract(
            scope_type="subscription_first",
            supported_scopes=["tenant", "subscription", "resource_group"],
            default_scope="subscription",
            scope_limitations=[
                "Tenant-wide identity signals require Microsoft Graph permissions.",
                "Resource-group scoping can hide subscription-level governance evidence.",
            ],
        )
    if provider == "aws":
        return ProviderScopeContract(
            scope_type="account_first_planned",
            supported_scopes=["organization", "account", "region"],
            default_scope="account",
            scope_limitations=[
                "Organization and multi-account aggregation are planned but not active.",
            ],
        )
    return ProviderScopeContract(
        scope_type="project_first_planned",
        supported_scopes=["organization", "folder", "project", "region"],
        default_scope="project",
        scope_limitations=[
            "Organization and folder traversal are planned but not active.",
        ],
    )


def _auth_contract(provider: str) -> ProviderAuthContract:
    if provider == "azure":
        return ProviderAuthContract(
            auth_modes=[
                "azure_cli",
                "default_azure_credential",
                "managed_identity",
                "service_principal",
            ],
            preferred_auth_mode="azure_cli",
            secret_handling=(
                "CRIS-SME does not collect or persist provider secrets; credentials stay "
                "inside the configured Azure identity chain."
            ),
        )
    if provider == "aws":
        return ProviderAuthContract(
            auth_modes=["aws_credential_chain", "assume_role"],
            preferred_auth_mode="aws_credential_chain",
            secret_handling=(
                "CRIS-SME does not collect or persist AWS secrets; credentials stay "
                "inside the standard boto3 credential chain (environment, "
                "~/.aws/credentials, or an IAM role) or, for cross-account "
                "scanning, temporary sts:AssumeRole credentials that are never "
                "written to disk."
            ),
        )
    return ProviderAuthContract(
        auth_modes=[
            "application_default_credentials_planned",
            "workload_identity_planned",
        ],
        preferred_auth_mode="application_default_credentials_planned",
        secret_handling=(
            "GCP credentials are not collected by CRIS-SME; planned support should use "
            "application default credentials or workload identity without persisting secrets."
        ),
    )


def _permission_contract(
    provider: str,
    domain: str,
    support_status: str,
) -> ProviderPermissionContract:
    required = _required_permissions(provider, domain, support_status)
    return ProviderPermissionContract(
        permission_model=_permission_model(provider, support_status),
        required_permissions=required,
        optional_permissions=_optional_permissions(provider, domain, support_status),
        least_privilege_notes=_least_privilege_notes(provider, support_status),
    )


def _permission_model(provider: str, support_status: str) -> str:
    if support_status == "planned":
        return f"{provider}_least_privilege_planned"
    if support_status == "research_preview":
        return f"{provider}_research_preview_permissions"
    return f"{provider}_least_privilege"


def _required_permissions(
    provider: str,
    domain: str,
    support_status: str,
) -> list[str]:
    if support_status == "planned":
        return [f"{provider}:planned_collector_permissions"]
    if support_status == "research_preview" and provider not in {"azure", "aws"}:
        return [f"{provider}:research_preview_read_permissions"]

    normalized = domain.lower()
    if provider == "azure":
        if "iam" in normalized:
            return [
                "Microsoft.Authorization/roleAssignments/read",
                "Microsoft.Graph/directoryRoles/read",
            ]
        if "network" in normalized:
            return ["Microsoft.Network/*/read"]
        if "data" in normalized:
            return [
                "Microsoft.Storage/storageAccounts/read",
                "Microsoft.Sql/servers/read",
                "Microsoft.KeyVault/vaults/read",
            ]
        if "monitoring" in normalized:
            return [
                "Microsoft.Insights/diagnosticSettings/read",
                "Microsoft.Insights/activityLogAlerts/read",
                "Microsoft.Insights/logProfiles/read",
                "Microsoft.Security/*/read",
            ]
        if "compute" in normalized:
            return [
                "Microsoft.Compute/virtualMachines/read",
                "Microsoft.RecoveryServices/*/read",
            ]
        if "iot" in normalized:
            return [
                "Microsoft.Devices/IotHubs/read",
                "Microsoft.Insights/metricAlerts/read",
                "Microsoft.Security/*/read",
            ]
        return [
            "Microsoft.Resources/subscriptions/resources/read",
            "Microsoft.Authorization/policyAssignments/read",
            "Microsoft.PolicyInsights/policyStates/summarize/action",
        ]
    if provider == "aws":
        if "iam" in normalized:
            return [
                "iam:ListUsers",
                "iam:ListRoles",
                "iam:ListAttachedUserPolicies",
                "iam:ListAttachedRolePolicies",
                "iam:ListUserPolicies",
                "iam:ListRolePolicies",
                "iam:GetUserPolicy",
                "iam:GetRolePolicy",
                "iam:ListGroupsForUser",
                "iam:ListAttachedGroupPolicies",
                "iam:ListMFADevices",
                "iam:ListAccessKeys",
                "iam:GetAccessKeyLastUsed",
                "iam:GetAccountPasswordPolicy",
                "iam:GetAccountSummary",
                "sts:GetCallerIdentity",
                "access-analyzer:ListAnalyzers",
            ]
        if "network" in normalized:
            return [
                "ec2:DescribeSecurityGroups",
                "ec2:DescribeVpcEndpoints",
                "ec2:DescribeRegions",
                "elasticloadbalancing:DescribeLoadBalancers",
                "elasticloadbalancing:DescribeListeners",
            ]
        if "data" in normalized:
            return [
                "s3:ListAllMyBuckets",
                "s3:GetBucketLocation",
                "s3:GetBucketPolicyStatus",
                "s3:GetBucketAcl",
                "s3:GetEncryptionConfiguration",
                "s3:GetBucketVersioning",
                "s3:GetBucketTagging",
                "s3:GetBucketPublicAccessBlock",
                "rds:DescribeDBInstances",
                "kms:ListKeys",
                "kms:DescribeKey",
                "secretsmanager:ListSecrets",
            ]
        if "monitoring" in normalized:
            return [
                "cloudtrail:DescribeTrails",
                "cloudtrail:GetTrailStatus",
                "logs:DescribeLogGroups",
                "cloudwatch:DescribeAlarms",
                "guardduty:ListDetectors",
                "guardduty:ListFindings",
                "securityhub:GetEnabledStandards",
                "securityhub:GetFindings",
                "ssm:ListDocuments",
            ]
        if "compute" in normalized:
            return [
                "ec2:DescribeInstances",
                "ssm:DescribeInstanceInformation",
                "ssm:DescribeInstancePatchStates",
                "backup:ListProtectedResources",
                "lambda:ListFunctions",
                "lambda:GetFunctionUrlConfig",
                "lambda:GetPolicy",
                "ecs:ListClusters",
                "ecs:DescribeClusters",
                "eks:ListClusters",
                "eks:DescribeCluster",
            ]
        if "iot" in normalized:
            return [
                "iot:ListThings",
                "iot:ListThingGroups",
                "iot:ListCertificates",
                "iot:ListPolicies",
                "iot:GetPolicy",
                "iot:ListTopicRules",
                "iot:GetTopicRule",
                "iot:ListSecurityProfiles",
            ]
        return [
            "tag:GetResources",
            "ec2:DescribeVolumes",
            "ec2:DescribeAddresses",
            "config:DescribeConfigurationRecorderStatus",
            "config:GetComplianceSummaryByConfigRule",
        ]
    return [f"{provider}:read_only_control_plane"]


def _optional_permissions(
    provider: str,
    domain: str,
    support_status: str,
) -> list[str]:
    if support_status == "planned":
        return [f"{provider}:optional_org_scope_planned"]
    normalized = domain.lower()
    if provider == "azure" and "iam" in normalized:
        return [
            "Microsoft.Graph/conditionalAccessPolicies/read",
            "Microsoft.Graph/accessReviews/read",
            "Microsoft.Graph/credentialUserRegistrationDetails/read",
            "Microsoft.Graph/roleEligibilityScheduleInstances/read",
        ]
    if provider == "azure" and "governance" in normalized:
        return ["Microsoft.Consumption/budgets/read"]
    if provider == "aws" and "governance" in normalized:
        return ["budgets:ViewBudget", "organizations:ListPolicies"]
    return []


def _least_privilege_notes(provider: str, support_status: str) -> list[str]:
    if support_status == "planned":
        return [
            (
                "Provider support is planned; permissions are placeholders until "
                "collector implementation exists."
            ),
            (
                "Do not mark this provider active until least-privilege setup "
                "artifacts and tests are present."
            ),
        ]
    if support_status == "research_preview":
        return [
            "Research-preview permissions must be separated from production assurance claims.",
        ]
    return [
        f"Use read-only {provider} permissions wherever possible.",
        "Unavailable permissions should create explicit evidence gaps rather than compliance assumptions.",
    ]


def _evidence_capability(
    provider: str,
    control_id: str,
    domain: str,
    support_status: str,
) -> ProviderEvidenceCapability:
    active = support_status in {"active", "supported", "research_preview"}
    return ProviderEvidenceCapability(
        capability_id=f"cap_{provider}_{control_id.lower()}",
        capability_type=_capability_type(domain),
        collection_method=_collection_method(provider, domain, support_status),
        resource_types=_resource_types(domain),
        supports_resource_level_evidence=active,
        supports_freshness_check=active,
        limitations=_capability_limitations(provider, support_status),
    )


def _capability_type(domain: str) -> str:
    normalized = domain.lower()
    if "iam" in normalized:
        return "identity_posture"
    if "network" in normalized:
        return "network_exposure"
    if "data" in normalized:
        return "data_protection"
    if "monitoring" in normalized:
        return "monitoring_retention"
    if "compute" in normalized:
        return "workload_posture"
    if "iot" in normalized:
        return "iot_platform_posture"
    return "governance_inventory"


def _collection_method(provider: str, domain: str, support_status: str) -> str:
    if support_status == "planned":
        return f"{provider}_collector_planned"
    if support_status == "research_preview":
        return f"{provider}_research_preview_collector"
    if provider == "azure":
        normalized = domain.lower()
        if "iam" in normalized:
            return "azure_role_assignments_and_graph"
        if "network" in normalized:
            return "azure_network_management"
        if "data" in normalized:
            return "azure_storage_sql_keyvault_inventory"
        if "monitoring" in normalized:
            return "azure_monitor_inventory"
        if "compute" in normalized:
            return "azure_compute_inventory"
        if "iot" in normalized:
            return "azure_iot_control_plane"
        return "azure_resource_policy_inventory"
    return f"{provider}_read_only_inventory"


def _resource_types(domain: str) -> list[str]:
    normalized = domain.lower()
    if "iam" in normalized:
        return ["principal", "role_assignment", "access_policy"]
    if "network" in normalized:
        return ["network_security_group", "firewall_rule", "public_endpoint"]
    if "data" in normalized:
        return ["storage_account", "database", "key_vault"]
    if "monitoring" in normalized:
        return ["diagnostic_setting", "activity_log_alert", "log_workspace"]
    if "compute" in normalized:
        return ["virtual_machine", "workload"]
    if "iot" in normalized:
        return ["iot_hub", "device_identity", "message_route"]
    return ["subscription", "resource_group", "policy_assignment", "tag"]


def _capability_limitations(provider: str, support_status: str) -> list[str]:
    if support_status == "planned":
        return [f"{provider} capability is declared for planning only and is not live-supported."]
    if support_status == "research_preview":
        return [f"{provider} capability is limited to research-preview evidence."]
    return []


def _freshness_policy(freshness_hours: int) -> ProviderFreshnessPolicy:
    return ProviderFreshnessPolicy(
        freshness_hours=freshness_hours,
        stale_after_hours=max(freshness_hours * 2, freshness_hours + 1),
        policy=(
            "Evidence older than the freshness window should reduce sufficiency or "
            "create a visible stale-evidence gap."
        ),
    )


def _provider_limitations(
    provider: str,
    control_id: str,
    domain: str,
    support_status: str,
    spec_limitations: list[str],
) -> list[ProviderLimitation]:
    limitations = [
        ProviderLimitation(
            limitation_id=f"lim_{provider}_{control_id.lower()}_support",
            severity="medium" if support_status == "planned" else "low",
            description=_support_limitation(provider, support_status),
            affected_evidence=[_capability_type(domain)],
        )
    ]
    for index, limitation in enumerate(spec_limitations, start=1):
        limitations.append(
            ProviderLimitation(
                limitation_id=f"lim_{provider}_{control_id.lower()}_{index}",
                severity="medium",
                description=limitation,
                affected_evidence=list(_resource_types(domain)),
            )
        )
    return limitations


def _support_limitation(provider: str, support_status: str) -> str:
    if support_status in {"active", "supported"}:
        return (
            f"{provider} evidence path is active but still bounded by granted "
            "permissions and collection scope."
        )
    if support_status == "research_preview":
        return (
            f"{provider} evidence path is research preview and cannot support "
            "production assurance alone."
        )
    if support_status == "planned":
        return f"{provider} evidence path is planned and must not be represented as live evidence."
    return f"{provider} evidence path is unsupported for this control."


def _sufficiency_policy(support_status: str) -> str:
    if support_status in {"active", "supported"}:
        return (
            "A control decision should be treated as sufficient only when declared "
            "evidence requirements are directly observed and within freshness bounds."
        )
    if support_status == "planned":
        return (
            "Provider path is planned; decisions may be modeled for schema testing but "
            "must not be claimed as live provider evidence."
        )
    if support_status == "research_preview":
        return (
            "Provider path is available only for research preview; decisions must be "
            "reported as experimental and separated from production assurance claims."
        )
    return (
        "Provider path is unsupported; unavailable evidence must remain explicit and "
        "must not be interpreted as compliance."
    )


def _activation_gate(provider: str, support_status: str) -> str:
    if support_status in {"active", "supported"}:
        return (
            f"{provider} support is active for this control in the current policy pack."
        )
    if support_status == "planned":
        return (
            f"{provider} support can be activated only after collector evidence, adapter "
            "routing, tests, and documented limitations are present."
        )
    if support_status == "research_preview":
        return (
            f"{provider} support is limited to research-preview evidence until lab "
            "validation, collector coverage, and expert review are complete."
        )
    return f"{provider} support is not available for this control."


def _support_status_counts(
    contracts: list[ProviderEvidenceContract],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for contract in contracts:
        counts[contract.support_status] = counts.get(contract.support_status, 0) + 1
    return counts
