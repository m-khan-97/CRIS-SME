# AWS-backed collector for building provider-normalized CRIS-SME profiles from AWS account context.
#
# Research-preview status: this collector issues real boto3 calls using the
# standard AWS credential chain, but has not yet been verified against a live
# AWS account. Several fields are best-effort analogs of Azure concepts that
# have no exact AWS counterpart (see module-level NOTE comments below); treat
# any such field as an approximation, not a guarantee of equivalence.
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Callable

MAX_REGION_WORKERS = 10

from cris_sme.collectors.providers import get_profile_adapter
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

ClientFactory = Callable[[str, str | None], Any]

ADMIN_POLICY_ARNS = {
    "arn:aws:iam::aws:policy/AdministratorAccess",
}


class _NullAwsClient:
    """Stand-in client returned once credentials are known to be unavailable.

    Constructing a *real* boto3 client independently re-triggers credential
    resolution (and its IMDS round-trip cost) even if no method on the
    resulting client is ever called. Once `AwsCollector` has proven that no
    credentials are usable, every subsequent domain method gets this instead
    of a real client, so that cost is paid at most once per collection run.
    """

    def __getattr__(self, name: str) -> Callable[..., Any]:
        def _raise(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("AWS credentials are unavailable for this collection run.")

        return _raise


@dataclass(slots=True)
class AwsCollectorSettings:
    """Configuration for the first-stage AWS-backed collector."""

    account_id: str | None = None
    organization_name: str = "AWS SME Account"
    sector: str = "SME"
    tenant_scope: str | None = None
    organization_id: str | None = None
    dataset_source_type: str = "live_real"
    authorization_basis: str = "authorized_account_access"
    dataset_use: str = "live_case_study"
    regions: tuple[str, ...] | None = None
    role_arn: str | None = None
    external_id: str | None = None


class AwsCollector:
    """Collect AWS account context and normalize it into CRIS-SME cloud profiles."""

    def __init__(
        self,
        settings: AwsCollectorSettings | None = None,
        client_factory: ClientFactory | None = None,
    ) -> None:
        self.settings = settings or AwsCollectorSettings()
        self._client_factory = client_factory
        self._session: Any = None
        self._credentials_available: bool | None = None
        self._cached_identity: dict[str, Any] | None = None

    def collect_raw_profiles(self) -> list[dict[str, Any]]:
        """Return a conservative raw AWS profile built from authenticated account context."""
        account_id = self._resolve_account_id()
        return [self._build_raw_profile_from_account(account_id)]

    def collect_profiles(self) -> list[CloudProfile]:
        """Return provider-normalized AWS cloud profiles."""
        adapter = get_profile_adapter("aws")
        profiles = [
            adapter.normalize_profile(raw_profile)
            for raw_profile in self.collect_raw_profiles()
        ]

        if self.settings.account_id:
            filtered_profiles = [
                profile
                for profile in profiles
                if profile.metadata.get("account_id") == self.settings.account_id
            ]
            if not filtered_profiles:
                raise ValueError(
                    f"AWS account '{self.settings.account_id}' was not found "
                    "for the current credential context."
                )
            return filtered_profiles

        return profiles

    def _resolve_account_id(self) -> str:
        """Resolve the AWS account id from STS caller identity, falling back to settings."""
        identity = self._get_caller_identity()
        if identity and identity.get("Account"):
            return str(identity["Account"])

        if self.settings.account_id:
            return self.settings.account_id

        raise ValueError(
            "Unable to resolve an AWS account from the current credential "
            "context. Configure AWS credentials or set AWS_ACCOUNT_ID."
        )

    def _build_raw_profile_from_account(self, account_id: str) -> dict[str, Any]:
        """Build a conservative raw AWS profile for adapter normalization."""
        regions = self._resolve_regions()
        organization_id = self.settings.organization_id or f"aws-{account_id}"
        organization_name, organization_name_source = self._resolve_organization_name(
            account_id, regions
        )
        tenant_scope = self.settings.tenant_scope or account_id

        iam_profile, iam_metadata = self._collect_iam_profile()
        network_profile, network_metadata = self._collect_network_profile(regions)
        data_profile, data_metadata = self._collect_data_profile(regions)
        private_endpoint_requirement = self._derive_private_endpoint_requirement(
            storage_account_count=int(data_metadata.get("storage_account_count", 0)),
            sql_server_count=int(data_metadata.get("sql_server_count", 0)),
            intentional_public_service_count=int(
                data_metadata.get("intentional_public_service_count", 0)
            ),
        )
        if (
            private_endpoint_requirement["required"] > 0
            and network_profile.private_endpoints_required == 0
        ):
            network_profile = NetworkProfile(
                internet_exposed_rdp_assets=network_profile.internet_exposed_rdp_assets,
                internet_exposed_ssh_assets=network_profile.internet_exposed_ssh_assets,
                permissive_nsg_rules=network_profile.permissive_nsg_rules,
                public_storage_endpoints=network_profile.public_storage_endpoints,
                private_endpoints_required=private_endpoint_requirement["required"],
                private_endpoints_configured=network_profile.private_endpoints_configured,
                private_endpoint_exemptions=private_endpoint_requirement["exemptions"],
                private_endpoint_requirement_basis=str(
                    private_endpoint_requirement["basis"]
                ),
            )
        monitoring_profile, monitoring_metadata = self._collect_monitoring_profile(regions)
        compute_profile, compute_metadata = self._collect_compute_profile(regions)
        governance_profile, governance_metadata = self._collect_governance_profile(
            regions, account_id
        )
        iot_profile, iot_metadata = self._collect_iot_profile(regions)

        return {
            "organization_id": organization_id,
            "organization_name": organization_name,
            "provider": "aws",
            "sector": self.settings.sector,
            "tenant_scope": tenant_scope,
            "iam": iam_profile.model_dump(),
            "network": network_profile.model_dump(),
            "data": data_profile.model_dump(),
            "monitoring": monitoring_profile.model_dump(),
            "compute": compute_profile.model_dump(),
            "governance": governance_profile.model_dump(),
            "iot": iot_profile.model_dump() if iot_profile is not None else None,
            "metadata": {
                "collection_mode": "aws_boto3_account_inventory",
                "collector_stage": "aws_live_enriched",
                "profile_source": "aws_live",
                "dataset_source_type": self.settings.dataset_source_type,
                "authorization_basis": self.settings.authorization_basis,
                "dataset_use": self.settings.dataset_use,
                "account_id": account_id,
                "organization_name_source": organization_name_source,
                "regions_scanned": list(regions),
                **iam_metadata,
                **network_metadata,
                **data_metadata,
                "private_endpoint_requirement_basis": (
                    network_profile.private_endpoint_requirement_basis
                ),
                "private_endpoint_exemption_count": (
                    network_profile.private_endpoint_exemptions
                ),
                **monitoring_metadata,
                **compute_metadata,
                **governance_metadata,
                **iot_metadata,
                "note": (
                    "This profile was created from live AWS account context via "
                    "boto3. IAM, network, data, monitoring, compute, and "
                    "governance posture include live AWS evidence where "
                    "available. Several fields are best-effort analogs of "
                    "Azure concepts with no exact AWS equivalent (e.g. Key "
                    "Vault posture is approximated from KMS/Secrets Manager, "
                    "IoT Hub posture from AWS IoT Core); this collector is a "
                    "research preview and has not yet been verified against a "
                    "live AWS account."
                ),
            },
        }

    def _resolve_organization_name(
        self,
        account_id: str,
        regions: list[str] | tuple[str, ...] | None = None,
    ) -> tuple[str, str]:
        """Resolve a display name without pretending AWS account IDs encode company identity."""
        configured = self.settings.organization_name.strip()
        if configured and configured != "AWS SME Account":
            return configured, "configured"

        tagged_resources: list[dict[str, Any]] = []
        for region in regions or (self._primary_region(),):
            tagging = self._build_client("resourcegroupstaggingapi", region)
            tagged_resources.extend(
                self._paginate_allow_failure(
                    tagging, "get_resources", items_key="ResourceTagMappingList"
                )
            )
        tagged_names = {
            str(tag.get("Value", "")).strip()
            for resource in tagged_resources
            if isinstance(resource, dict)
            for tag in resource.get("Tags", [])
            if isinstance(tag, dict)
            and str(tag.get("Key", "")).strip().lower() == "organization"
            and str(tag.get("Value", "")).strip()
        }
        if len(tagged_names) == 1:
            return tagged_names.pop(), "resource_tag"

        iam = self._build_client("iam", None)
        aliases = self._call_allow_failure(iam.list_account_aliases)
        account_aliases = aliases.get("AccountAliases", []) if isinstance(aliases, dict) else []
        if len(account_aliases) == 1 and str(account_aliases[0]).strip():
            return str(account_aliases[0]).strip(), "iam_account_alias"

        organizations = self._build_client("organizations", "us-east-1")
        account = self._call_allow_failure(organizations.describe_account, AccountId=account_id)
        account_name = account.get("Account", {}).get("Name") if isinstance(account, dict) else None
        if account_name and str(account_name).strip():
            return str(account_name).strip(), "organizations_account"

        return configured or "AWS SME Account", "default"

    # -- Region and account resolution -----------------------------------

    def _primary_region(self) -> str:
        if self.settings.regions:
            return self.settings.regions[0]
        return "us-east-1"

    def _resolve_regions(self) -> list[str]:
        if self.settings.regions:
            return list(self.settings.regions)

        ec2 = self._build_client("ec2", self._primary_region())
        response = self._call_allow_failure(
            ec2.describe_regions,
            Filters=[
                {
                    "Name": "opt-in-status",
                    "Values": ["opt-in-not-required", "opted-in"],
                }
            ],
        )
        if not isinstance(response, dict):
            return [self._primary_region()]

        regions = [
            str(region["RegionName"])
            for region in response.get("Regions", [])
            if isinstance(region, dict) and region.get("RegionName")
        ]
        return regions or [self._primary_region()]

    # -- boto3 client construction and graceful-failure helpers ----------

    def _get_session(self) -> Any:
        """Build (or reuse) one boto3 Session for the whole collection run.

        Mirrors Prowler's pattern of deriving every client from a single
        session rather than letting each `boto3.client(...)` call
        independently re-resolve credentials. When `settings.role_arn` is
        set, the session is swapped for one backed by temporary
        `sts:AssumeRole` credentials, so every client built afterwards
        operates against the target account rather than the local
        ("hub") identity.
        """
        if self._session is None:
            try:
                import boto3
            except ImportError as exc:
                raise RuntimeError(
                    "AWS collection requires the optional dependency 'boto3'. "
                    "Install the AWS extras before using AwsCollector."
                ) from exc

            base_session = boto3.Session()
            if self.settings.role_arn:
                self._session = self._build_assumed_role_session(base_session)
            else:
                self._session = base_session
        return self._session

    def _build_assumed_role_session(self, base_session: Any) -> Any:
        """Return a new session backed by temporary cross-account AssumeRole credentials."""
        import boto3

        sts = base_session.client("sts", region_name=self._primary_region())
        credentials = self._assume_role_credentials(sts)
        return boto3.Session(
            aws_access_key_id=credentials.get("AccessKeyId"),
            aws_secret_access_key=credentials.get("SecretAccessKey"),
            aws_session_token=credentials.get("SessionToken"),
        )

    def _assume_role_credentials(self, sts_client: Any) -> dict[str, Any]:
        """Call sts:AssumeRole and return the temporary credentials, raising clearly on failure.

        Unlike the rest of the collector's "degrade gracefully to not
        observed" posture, a failed AssumeRole is a hard, immediate error:
        silently falling back to empty findings on a misconfigured role
        would look exactly like a clean account, which would be actively
        misleading rather than honestly incomplete.
        """
        kwargs: dict[str, Any] = {
            "RoleArn": self.settings.role_arn,
            "RoleSessionName": f"cris-sme-assessment-{int(datetime.now(UTC).timestamp())}",
        }
        if self.settings.external_id:
            kwargs["ExternalId"] = self.settings.external_id

        try:
            response = sts_client.assume_role(**kwargs)
        except Exception as exc:
            raise ValueError(
                f"Unable to assume AWS role '{self.settings.role_arn}'. Confirm the "
                "role's trust policy allows this identity, the external ID matches, "
                f"and the role exists. Underlying error: {exc}"
            ) from exc

        return response.get("Credentials", {}) if isinstance(response, dict) else {}

    def _build_client(self, service_name: str, region: str | None) -> Any:
        """Build a boto3 client, using dependency injection when provided."""
        if self._client_factory is not None:
            return self._client_factory(service_name, region)

        if self._credentials_available is False:
            return _NullAwsClient()

        return self._get_session().client(service_name, region_name=region)

    def _has_credentials(self) -> bool:
        """Return whether any AWS credentials are usable, checked once and cached.

        A `NoCredentialsError` on the very first call doesn't just mean that
        one call fails: it means every other call this run would also fail,
        each after independently re-paying the same credential-chain lookup
        cost (env vars, shared config, IMDS). Checking once and caching the
        result means that cost is paid at most once per collection run
        instead of once per API call.
        """
        return self._get_caller_identity() is not None

    def _get_caller_identity(self) -> dict[str, Any] | None:
        """Resolve and cache the STS caller identity once for this collection run."""
        if self._credentials_available is None:
            sts = self._build_client("sts", self._primary_region())
            try:
                identity = sts.get_caller_identity()
                self._cached_identity = identity if isinstance(identity, dict) else {}
                self._credentials_available = True
            except Exception:
                self._cached_identity = None
                self._credentials_available = False
        return self._cached_identity

    def _call_allow_failure(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Call a boto3 client method, returning None on any failure."""
        if not self._has_credentials():
            return None
        try:
            return fn(*args, **kwargs)
        except Exception:
            return None

    def _paginate_allow_failure(
        self,
        client: Any,
        operation_name: str,
        *,
        items_key: str,
        **kwargs: Any,
    ) -> list[Any]:
        """Call a paginated boto3 list/describe operation across all pages, or [] on failure.

        Reads every page via the operation's boto3 paginator instead of only
        the first; AWS list/describe APIs commonly truncate at 50-1000 items
        per page, and reading only page one would silently undercount on any
        account with more resources than that, with no visible error.
        """
        if not self._has_credentials():
            return []
        try:
            paginator = client.get_paginator(operation_name)
            items: list[Any] = []
            for page in paginator.paginate(**kwargs):
                if not isinstance(page, dict):
                    continue
                page_items = page.get(items_key, [])
                if isinstance(page_items, list):
                    items.extend(page_items)
            return items
        except Exception:
            return []

    def _call_and_extract_items(
        self,
        fn: Callable[..., Any],
        *,
        items_key: str,
        **kwargs: Any,
    ) -> list[Any]:
        """Call a non-paginatable boto3 list/describe method once and return its item list, or []."""
        response = self._call_allow_failure(fn, **kwargs)
        if not isinstance(response, dict):
            return []
        items = response.get(items_key, [])
        return items if isinstance(items, list) else []

    def _map_regions(self, regions: list[str], worker: Callable[[str], Any]) -> list[Any]:
        """Run a per-region worker across all regions, in parallel when there's more than one.

        Mirrors Prowler's per-region ThreadPoolExecutor pattern: real
        multi-region AWS collection pays real per-call network latency, so
        scanning regions concurrently instead of sequentially matters once
        credentials are actually valid.
        """
        if len(regions) <= 1:
            return [worker(region) for region in regions]
        with ThreadPoolExecutor(max_workers=min(len(regions), MAX_REGION_WORKERS)) as executor:
            return list(executor.map(worker, regions))

    # -- Shared helpers ----------------------------------------------------

    @staticmethod
    def _derive_private_endpoint_requirement(
        *,
        storage_account_count: int,
        sql_server_count: int,
        intentional_public_service_count: int,
    ) -> dict[str, Any]:
        """Derive AWS PrivateLink (VPC endpoint) requirements from sensitive-data inventory."""
        sensitive_service_count = storage_account_count + sql_server_count
        exemptions = min(intentional_public_service_count, sensitive_service_count)
        required = max(sensitive_service_count - exemptions, 0)
        basis = (
            "s3_and_rds_inventory"
            if sensitive_service_count
            else "no_sensitive_data_service_inventory"
        )
        return {"required": required, "exemptions": exemptions, "basis": basis}

    # -- IAM domain --------------------------------------------------------

    def _collect_iam_profile(self) -> tuple[IamProfile, dict[str, Any]]:
        """Collect IAM posture from AWS IAM, STS, and Access Analyzer."""
        iam = self._build_client("iam", None)

        users = self._paginate_allow_failure(iam, "list_users", items_key="Users")
        roles = self._paginate_allow_failure(iam, "list_roles", items_key="Roles")

        privileged_user_names = {
            user["UserName"]
            for user in users
            if isinstance(user, dict) and self._principal_is_privileged(iam, "user", user.get("UserName"))
        }
        privileged_role_names = {
            role["RoleName"]
            for role in roles
            if isinstance(role, dict) and self._principal_is_privileged(iam, "role", role.get("RoleName"))
        }
        privileged_principal_count = len(privileged_user_names) + len(privileged_role_names)
        privileged_assignment_count = privileged_principal_count

        privileged_accounts_without_mfa = self._collect_privileged_users_without_mfa(
            iam,
            privileged_user_names=privileged_user_names,
        )

        stale_keys, disabled_principals = self._collect_access_key_posture(iam, users)

        (
            conditional_access_enforced_for_admins,
            conditional_access_accessible,
            conditional_access_policy_count,
        ) = self._collect_admin_mfa_enforcement_signal(iam)

        signed_in_user_arn, signed_in_user_is_admin = self._collect_caller_privilege_signal(
            iam,
            privileged_user_names=privileged_user_names,
            privileged_role_names=privileged_role_names,
        )

        access_review_posture = self._collect_access_analyzer_posture()

        identity_observability = (
            "full" if conditional_access_accessible else "partial"
        )

        return (
            IamProfile(
                privileged_accounts=privileged_principal_count,
                privileged_accounts_without_mfa=privileged_accounts_without_mfa,
                overprivileged_accounts=max(
                    privileged_assignment_count - privileged_principal_count, 0
                ),
                stale_service_principals=stale_keys,
                rbac_review_age_days=access_review_posture["age_days"],
                conditional_access_enforced_for_admins=conditional_access_enforced_for_admins,
                privileged_user_assignments=len(privileged_user_names),
                privileged_service_principal_assignments=len(privileged_role_names),
                disabled_service_principals=disabled_principals,
                signed_in_user_directory_roles=1 if signed_in_user_arn else 0,
                signed_in_user_is_directory_admin=signed_in_user_is_admin,
                visible_directory_role_catalog_entries=len(roles),
                directory_role_catalog_visible=bool(roles),
                identity_observability=identity_observability,
                rbac_review_api_accessible=access_review_posture["api_accessible"],
                rbac_review_definition_count=access_review_posture["definition_count"],
                rbac_review_privileged_scope_count=access_review_posture[
                    "privileged_scope_count"
                ],
                rbac_review_scope=access_review_posture["scope"],
            ),
            {
                "iam_collection_mode": (
                    "aws_iam_user_role_inventory" if (users or roles) else "default_no_iam_inventory"
                ),
                "identity_observability": identity_observability,
                "conditional_access_accessible": conditional_access_accessible,
                "conditional_access_policy_count": conditional_access_policy_count,
            },
        )

    def _principal_is_privileged(
        self,
        iam: Any,
        principal_type: str,
        principal_name: str | None,
    ) -> bool:
        """Return whether a user or role has administrator-equivalent IAM access.

        NOTE: AWS has no Conditional-Access-scoped "privileged role" concept
        like Entra; this proxies privilege from attached and inline
        AdministratorAccess-equivalent policy grants (and, for users,
        group-attached policies), the closest AWS analog to Azure's
        Owner/User Access Administrator role check. A custom policy with an
        Allow Action="*" Resource="*" statement is treated the same as the
        literal AdministratorAccess ARN, since a differently-named policy
        carries the same risk.
        """
        if not principal_name:
            return False

        if self._principal_has_admin_attached_policy(iam, principal_type, principal_name):
            return True
        if self._principal_has_admin_inline_policy(iam, principal_type, principal_name):
            return True
        if principal_type == "user" and self._user_has_admin_group_policy(iam, principal_name):
            return True
        return False

    def _principal_has_admin_attached_policy(
        self,
        iam: Any,
        principal_type: str,
        principal_name: str,
    ) -> bool:
        operation_name = "list_attached_user_policies" if principal_type == "user" else "list_attached_role_policies"
        kwarg = "UserName" if principal_type == "user" else "RoleName"
        attached = self._paginate_allow_failure(
            iam, operation_name, items_key="AttachedPolicies", **{kwarg: principal_name}
        )
        return any(
            policy.get("PolicyArn") in ADMIN_POLICY_ARNS
            for policy in attached
            if isinstance(policy, dict)
        )

    def _principal_has_admin_inline_policy(
        self,
        iam: Any,
        principal_type: str,
        principal_name: str,
    ) -> bool:
        list_operation = "list_user_policies" if principal_type == "user" else "list_role_policies"
        kwarg = "UserName" if principal_type == "user" else "RoleName"
        get_fn = iam.get_user_policy if principal_type == "user" else iam.get_role_policy

        policy_names = self._paginate_allow_failure(
            iam, list_operation, items_key="PolicyNames", **{kwarg: principal_name}
        )
        for policy_name in policy_names:
            if not policy_name:
                continue
            detail = self._call_allow_failure(
                get_fn, PolicyName=policy_name, **{kwarg: principal_name}
            )
            if isinstance(detail, dict) and self._policy_document_grants_admin(
                detail.get("PolicyDocument")
            ):
                return True
        return False

    def _user_has_admin_group_policy(self, iam: Any, user_name: str) -> bool:
        groups = self._paginate_allow_failure(
            iam, "list_groups_for_user", items_key="Groups", UserName=user_name
        )
        for group in groups:
            group_name = group.get("GroupName") if isinstance(group, dict) else None
            if not group_name:
                continue
            attached = self._paginate_allow_failure(
                iam, "list_attached_group_policies", items_key="AttachedPolicies", GroupName=group_name
            )
            if any(
                policy.get("PolicyArn") in ADMIN_POLICY_ARNS
                for policy in attached
                if isinstance(policy, dict)
            ):
                return True
        return False

    @staticmethod
    def _policy_document_grants_admin(document: Any) -> bool:
        """Return whether a policy document contains an Allow Action="*" Resource="*" statement.

        IAM's get_user_policy/get_role_policy already return PolicyDocument
        as a parsed dict (unlike AWS IoT's get_policy, which returns a raw
        JSON string elsewhere in this collector), so no json.loads is
        needed here.
        """
        if not isinstance(document, dict):
            return False
        statements = document.get("Statement", [])
        if isinstance(statements, dict):
            statements = [statements]
        for statement in statements:
            if not isinstance(statement, dict) or statement.get("Effect") != "Allow":
                continue
            actions = statement.get("Action", [])
            resources = statement.get("Resource", [])
            actions = [actions] if isinstance(actions, str) else (actions or [])
            resources = [resources] if isinstance(resources, str) else (resources or [])
            if "*" in actions and "*" in resources:
                return True
        return False

    def _collect_privileged_users_without_mfa(
        self,
        iam: Any,
        *,
        privileged_user_names: set[str],
    ) -> int:
        """Return the count of privileged IAM users without an active MFA device."""
        if not privileged_user_names:
            return 0

        without_mfa = 0
        for user_name in privileged_user_names:
            devices = self._paginate_allow_failure(
                iam, "list_mfa_devices", items_key="MFADevices", UserName=user_name
            )
            if not devices:
                without_mfa += 1
        return without_mfa

    def _collect_access_key_posture(
        self,
        iam: Any,
        users: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Return (stale_access_key_count, disabled_user_count) across IAM users.

        NOTE: AWS has no service-principal concept; stale/unused IAM access
        keys are the closest analog to Azure's stale service principals.
        """
        stale_keys = 0
        disabled_users = 0
        now = datetime.now(UTC)

        for user in users:
            user_name = user.get("UserName") if isinstance(user, dict) else None
            if not user_name:
                continue

            keys = self._paginate_allow_failure(
                iam, "list_access_keys", items_key="AccessKeyMetadata", UserName=user_name
            )
            if not keys:
                continue

            active_keys = [key for key in keys if key.get("Status") == "Active"]
            if keys and not active_keys:
                disabled_users += 1

            for key in active_keys:
                last_used = self._call_allow_failure(
                    iam.get_access_key_last_used,
                    AccessKeyId=key.get("AccessKeyId", ""),
                )
                last_used_date = None
                if isinstance(last_used, dict):
                    last_used_date = last_used.get("AccessKeyLastUsed", {}).get("LastUsedDate")
                if last_used_date is None:
                    stale_keys += 1
                    continue
                try:
                    age_days = (now - last_used_date).days
                except TypeError:
                    continue
                if age_days > 90:
                    stale_keys += 1

        return stale_keys, disabled_users

    def _collect_admin_mfa_enforcement_signal(self, iam: Any) -> tuple[bool, bool, int]:
        """Return whether admin-MFA-equivalent enforcement is observable and present.

        NOTE: AWS has no Conditional Access; this proxies enforcement from the
        account password policy requiring MFA-aware controls being reachable,
        the closest available signal without a full per-policy condition scan.
        """
        policy = self._call_allow_failure(iam.get_account_password_policy)
        if policy is None:
            return (False, False, 0)

        summary = self._call_allow_failure(iam.get_account_summary)
        account_mfa_enabled = False
        if isinstance(summary, dict):
            account_mfa_enabled = bool(
                summary.get("SummaryMap", {}).get("AccountMFAEnabled")
            )
        return (account_mfa_enabled, True, 1 if account_mfa_enabled else 0)

    def _collect_caller_privilege_signal(
        self,
        iam: Any,
        *,
        privileged_user_names: set[str],
        privileged_role_names: set[str],
    ) -> tuple[str | None, bool]:
        """Return the calling identity's ARN and whether it is admin-equivalent."""
        identity = self._get_caller_identity()
        if not identity:
            return (None, False)

        arn = identity.get("Arn")
        if not arn:
            return (None, False)

        caller_name = str(arn).rsplit("/", 1)[-1]
        is_admin = caller_name in privileged_user_names or caller_name in privileged_role_names
        return (str(arn), is_admin)

    def _collect_access_analyzer_posture(self) -> dict[str, Any]:
        """Return observable IAM Access Analyzer posture, the closest AWS analog to an access review."""
        analyzer_client = self._build_client("accessanalyzer", self._primary_region())
        analyzers = self._paginate_allow_failure(
            analyzer_client, "list_analyzers", items_key="analyzers"
        )
        if not analyzers:
            return {
                "age_days": 0,
                "api_accessible": False,
                "definition_count": 0,
                "privileged_scope_count": 0,
                "scope": "unavailable",
            }

        active_analyzers = [
            analyzer for analyzer in analyzers if analyzer.get("status") == "ACTIVE"
        ]
        if not active_analyzers:
            return {
                "age_days": 365,
                "api_accessible": True,
                "definition_count": len(analyzers),
                "privileged_scope_count": 0,
                "scope": "none_configured",
            }

        now = datetime.now(UTC)
        most_recent = None
        for analyzer in active_analyzers:
            created_at = analyzer.get("createdAt")
            if created_at is not None and (most_recent is None or created_at > most_recent):
                most_recent = created_at

        age_days = 365
        if most_recent is not None:
            try:
                age_days = max(0, (now - most_recent).days)
            except TypeError:
                age_days = 365

        account_scoped = any(
            analyzer.get("type") == "ACCOUNT" for analyzer in active_analyzers
        )
        return {
            "age_days": age_days,
            "api_accessible": True,
            "definition_count": len(active_analyzers),
            "privileged_scope_count": len(active_analyzers) if account_scoped else 0,
            "scope": "privileged_role_scoped" if account_scoped else "generic_or_unknown",
        }

    # -- Network domain ------------------------------------------------------

    def _collect_network_profile(
        self,
        regions: list[str],
    ) -> tuple[NetworkProfile, dict[str, Any]]:
        """Collect AWS network posture from security groups and VPC endpoints across regions."""
        rdp_exposure_targets: set[str] = set()
        ssh_exposure_targets: set[str] = set()
        permissive_rule_count = 0
        private_endpoints_configured = 0
        security_group_total = 0

        for region_rdp, region_ssh, region_permissive, region_endpoints, region_sg_count in (
            self._map_regions(regions, self._collect_network_signals_for_region)
        ):
            rdp_exposure_targets.update(region_rdp)
            ssh_exposure_targets.update(region_ssh)
            permissive_rule_count += region_permissive
            private_endpoints_configured += region_endpoints
            security_group_total += region_sg_count

        internet_facing_lb_count = 0
        http_only_internet_facing_lb_count = 0
        load_balancer_total = 0
        for region_lb_count, region_internet_facing, region_http_only in self._map_regions(
            regions, self._collect_load_balancer_signals_for_region
        ):
            load_balancer_total += region_lb_count
            internet_facing_lb_count += region_internet_facing
            http_only_internet_facing_lb_count += region_http_only

        network_collection_mode = (
            "aws_ec2_security_group_inventory"
            if security_group_total
            else "default_no_network_inventory"
        )

        return (
            NetworkProfile(
                internet_exposed_rdp_assets=len(rdp_exposure_targets),
                internet_exposed_ssh_assets=len(ssh_exposure_targets),
                permissive_nsg_rules=permissive_rule_count,
                public_storage_endpoints=0,
                private_endpoints_required=0,
                private_endpoints_configured=private_endpoints_configured,
            ),
            {
                "network_collection_mode": network_collection_mode,
                "security_group_count": security_group_total,
                "load_balancer_count": load_balancer_total,
                "internet_facing_load_balancer_count": internet_facing_lb_count,
                "http_only_internet_facing_load_balancer_count": http_only_internet_facing_lb_count,
            },
        )

    def _collect_load_balancer_signals_for_region(self, region: str) -> tuple[int, int, int]:
        """Return (load_balancer_count, internet_facing_count, http_only_internet_facing_count) for one region.

        Security-group-level checks (above) only see exposure at the
        instance/network-interface layer; an internet-facing ELB/ALB/NLB is
        a distinct, equally direct ingress path that a security-group sweep
        alone never observes.
        """
        elbv2 = self._build_client("elbv2", region)
        load_balancers = self._paginate_allow_failure(
            elbv2, "describe_load_balancers", items_key="LoadBalancers"
        )

        internet_facing = [
            lb
            for lb in load_balancers
            if isinstance(lb, dict) and lb.get("Scheme") == "internet-facing"
        ]

        http_only_count = 0
        for lb in internet_facing:
            lb_arn = lb.get("LoadBalancerArn")
            if not lb_arn:
                continue
            listeners = self._paginate_allow_failure(
                elbv2, "describe_listeners", items_key="Listeners", LoadBalancerArn=lb_arn
            )
            has_https_listener = any(
                isinstance(listener, dict) and listener.get("Protocol") in {"HTTPS", "TLS"}
                for listener in listeners
            )
            has_http_listener = any(
                isinstance(listener, dict) and listener.get("Protocol") == "HTTP"
                for listener in listeners
            )
            if has_http_listener and not has_https_listener:
                http_only_count += 1

        return (len(load_balancers), len(internet_facing), http_only_count)

    def _collect_network_signals_for_region(
        self,
        region: str,
    ) -> tuple[set[str], set[str], int, int, int]:
        """Return (rdp_targets, ssh_targets, permissive_count, endpoint_count, sg_count) for one region."""
        ec2 = self._build_client("ec2", region)
        security_groups = self._paginate_allow_failure(
            ec2, "describe_security_groups", items_key="SecurityGroups"
        )

        rdp_exposure_targets: set[str] = set()
        ssh_exposure_targets: set[str] = set()
        permissive_rule_count = 0

        for group in security_groups:
            group_id = str(group.get("GroupId") or "sg-unknown")
            for permission in group.get("IpPermissions", []) or []:
                if not self._security_group_rule_is_public(permission):
                    continue

                if self._security_group_rule_exposes_port(permission, target_port=3389):
                    rdp_exposure_targets.add(group_id)
                    permissive_rule_count += 1
                    continue

                if self._security_group_rule_exposes_port(permission, target_port=22):
                    ssh_exposure_targets.add(group_id)
                    permissive_rule_count += 1
                    continue

                if self._security_group_rule_is_broadly_permissive(permission):
                    permissive_rule_count += 1

        vpc_endpoints = self._paginate_allow_failure(
            ec2, "describe_vpc_endpoints", items_key="VpcEndpoints"
        )

        return (
            rdp_exposure_targets,
            ssh_exposure_targets,
            permissive_rule_count,
            len(vpc_endpoints),
            len(security_groups),
        )

    @staticmethod
    def _security_group_rule_is_public(permission: dict[str, Any]) -> bool:
        ip_ranges = permission.get("IpRanges", []) or []
        ipv6_ranges = permission.get("Ipv6Ranges", []) or []
        return any(
            isinstance(entry, dict) and entry.get("CidrIp") == "0.0.0.0/0"
            for entry in ip_ranges
        ) or any(
            isinstance(entry, dict) and entry.get("CidrIpv6") == "::/0"
            for entry in ipv6_ranges
        )

    @staticmethod
    def _security_group_rule_exposes_port(
        permission: dict[str, Any],
        *,
        target_port: int,
    ) -> bool:
        protocol = str(permission.get("IpProtocol", "")).lower()
        if protocol == "-1":
            return True

        from_port = permission.get("FromPort")
        to_port = permission.get("ToPort")
        if from_port is None or to_port is None:
            return False

        return from_port <= target_port <= to_port

    @staticmethod
    def _security_group_rule_is_broadly_permissive(permission: dict[str, Any]) -> bool:
        protocol = str(permission.get("IpProtocol", "")).lower()
        if protocol == "-1":
            return True

        from_port = permission.get("FromPort")
        to_port = permission.get("ToPort")
        if from_port is None or to_port is None:
            return False

        return (to_port - from_port) >= 100

    # -- Data domain -----------------------------------------------------

    def _collect_data_profile(
        self,
        regions: list[str],
    ) -> tuple[DataProfile, dict[str, Any]]:
        """Collect AWS data posture from S3, RDS, KMS, and Secrets Manager."""
        s3 = self._build_client("s3", self._primary_region())
        buckets = self._paginate_allow_failure(s3, "list_buckets", items_key="Buckets")

        public_storage_assets = 0
        intentional_public_service_count = 0
        unencrypted_data_stores = 0
        retention_enabled_count = 0
        buckets_without_public_access_block = 0

        region_clients: dict[str, Any] = {self._primary_region(): s3}

        for bucket in buckets:
            bucket_name = bucket.get("Name") if isinstance(bucket, dict) else None
            if not bucket_name:
                continue

            # Most per-bucket metadata calls fail (PermanentRedirect) when
            # made against an S3 client configured for a different region
            # than the bucket actually lives in; resolving and reusing a
            # same-region client avoids silently failing every check below
            # for any bucket outside the primary scan region.
            bucket_client = self._s3_client_for_bucket(s3, region_clients, bucket_name)

            access_block = self._s3_bucket_public_access_block(bucket_client, bucket_name)
            if not access_block["fully_blocked"]:
                buckets_without_public_access_block += 1

            if self._s3_bucket_is_public(bucket_client, bucket_name, access_block):
                public_storage_assets += 1
                if self._s3_bucket_is_intentional_public_service(bucket_client, bucket_name):
                    intentional_public_service_count += 1

            if not self._s3_bucket_is_encrypted(bucket_client, bucket_name):
                unencrypted_data_stores += 1

            if self._s3_bucket_versioning_enabled(bucket_client, bucket_name):
                retention_enabled_count += 1

        storage_account_count = len(buckets)
        covered_data_store_count = retention_enabled_count
        total_data_store_count = storage_account_count
        sql_server_count = 0
        sql_database_count = 0
        public_sql_server_count = 0
        unencrypted_sql_database_count = 0

        for instances in self._map_regions(regions, self._collect_rds_instances_for_region):
            sql_server_count += len(instances)
            sql_database_count += len(instances)
            total_data_store_count += len(instances)

            for instance in instances:
                if instance.get("PubliclyAccessible"):
                    public_sql_server_count += 1
                if instance.get("StorageEncrypted"):
                    covered_data_store_count += 1
                else:
                    unencrypted_data_stores += 1
                    unencrypted_sql_database_count += 1

        coverage_ratio = (
            round(covered_data_store_count / total_data_store_count, 4)
            if total_data_store_count
            else 0.0
        )

        key_vault_posture = self._collect_secrets_posture(self._primary_region())

        return (
            DataProfile(
                public_storage_assets=public_storage_assets,
                unencrypted_data_stores=unencrypted_data_stores,
                backup_coverage_ratio=coverage_ratio,
                retention_policy_coverage_ratio=coverage_ratio,
                key_vault_mfa_enabled=key_vault_posture["mfa_enabled"],
                key_vault_purge_protection_enabled=key_vault_posture["purge_protection_enabled"],
                key_vault_count=key_vault_posture["vault_count"],
                key_vault_purge_protected_count=key_vault_posture["purge_protected_count"],
                key_vault_posture_state=key_vault_posture["state"],
            ),
            {
                "data_collection_mode": (
                    "aws_s3_and_rds_inventory"
                    if storage_account_count and sql_server_count
                    else "aws_s3_inventory"
                    if storage_account_count
                    else "aws_rds_inventory"
                    if sql_server_count
                    else "default_no_storage_inventory"
                ),
                "storage_account_count": storage_account_count,
                "public_storage_asset_count": public_storage_assets,
                "intentional_public_service_count": intentional_public_service_count,
                "unencrypted_data_store_count": unencrypted_data_stores,
                "buckets_without_public_access_block_count": buckets_without_public_access_block,
                "key_vault_count": key_vault_posture["vault_count"],
                "key_vault_purge_protected_count": key_vault_posture["purge_protected_count"],
                "key_vault_posture_state": key_vault_posture["state"],
                "sql_server_count": sql_server_count,
                "sql_database_count": sql_database_count,
                "public_sql_server_count": public_sql_server_count,
                "unencrypted_sql_database_count": unencrypted_sql_database_count,
            },
        )

    def _collect_rds_instances_for_region(self, region: str) -> list[dict[str, Any]]:
        rds = self._build_client("rds", region)
        return self._paginate_allow_failure(rds, "describe_db_instances", items_key="DBInstances")

    def _s3_client_for_bucket(
        self,
        default_client: Any,
        region_clients: dict[str, Any],
        bucket_name: str,
    ) -> Any:
        """Return an S3 client built for the bucket's actual region, caching one client per region."""
        location = self._call_allow_failure(default_client.get_bucket_location, Bucket=bucket_name)
        region = "us-east-1"
        if isinstance(location, dict):
            constraint = location.get("LocationConstraint")
            region = "eu-west-1" if constraint == "EU" else (constraint or "us-east-1")

        if region not in region_clients:
            region_clients[region] = self._build_client("s3", region)
        return region_clients[region]

    def _s3_bucket_public_access_block(self, s3: Any, bucket_name: str) -> dict[str, Any]:
        """Return whether S3 Block Public Access is fully enabled for a bucket.

        Block Public Access can neutralize a public ACL/policy grant at the
        S3-service level; without checking it, a bucket with a public ACL
        grant that BPA is actively ignoring would be misreported as exposed.
        """
        config = self._call_allow_failure(
            s3.get_public_access_block, Bucket=bucket_name
        )
        block = (
            config.get("PublicAccessBlockConfiguration", {})
            if isinstance(config, dict)
            else {}
        )
        fully_blocked = bool(block) and all(
            block.get(key)
            for key in (
                "BlockPublicAcls",
                "IgnorePublicAcls",
                "BlockPublicPolicy",
                "RestrictPublicBuckets",
            )
        )
        return {
            "fully_blocked": fully_blocked,
            "ignore_public_acls": bool(block.get("IgnorePublicAcls")),
        }

    def _s3_bucket_is_public(
        self,
        s3: Any,
        bucket_name: str,
        access_block: dict[str, Any],
    ) -> bool:
        status = self._call_allow_failure(s3.get_bucket_policy_status, Bucket=bucket_name)
        if isinstance(status, dict) and status.get("PolicyStatus", {}).get("IsPublic"):
            return True

        if access_block["ignore_public_acls"]:
            return False

        acl = self._call_allow_failure(s3.get_bucket_acl, Bucket=bucket_name)
        if not isinstance(acl, dict):
            return False

        public_group_uris = {
            "http://acs.amazonaws.com/groups/global/AllUsers",
            "http://acs.amazonaws.com/groups/global/AuthenticatedUsers",
        }
        return any(
            grant.get("Grantee", {}).get("URI") in public_group_uris
            for grant in acl.get("Grants", []) or []
            if isinstance(grant, dict)
        )

    def _s3_bucket_is_encrypted(self, s3: Any, bucket_name: str) -> bool:
        encryption = self._call_allow_failure(s3.get_bucket_encryption, Bucket=bucket_name)
        if not isinstance(encryption, dict):
            return False
        rules = encryption.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])
        return bool(rules)

    def _s3_bucket_versioning_enabled(self, s3: Any, bucket_name: str) -> bool:
        versioning = self._call_allow_failure(s3.get_bucket_versioning, Bucket=bucket_name)
        return isinstance(versioning, dict) and versioning.get("Status") == "Enabled"

    def _s3_bucket_is_intentional_public_service(self, s3: Any, bucket_name: str) -> bool:
        tagging = self._call_allow_failure(s3.get_bucket_tagging, Bucket=bucket_name)
        if not isinstance(tagging, dict):
            return False
        tags = {
            tag.get("Key", ""): tag.get("Value", "")
            for tag in tagging.get("TagSet", []) or []
            if isinstance(tag, dict)
        }
        return self._tags_indicate_intentional_public_service(tags)

    @staticmethod
    def _tags_indicate_intentional_public_service(tags: dict[str, str]) -> bool:
        """Return whether tags explicitly mark a resource as intentionally public.

        Mirrors the tag convention AzureCollector uses so the same evidence
        contract applies across providers.
        """
        intent_values = {
            tags.get("cris-sme-public-intent", ""),
            tags.get("cris-sme-intent", ""),
            tags.get("cris-sme-data-classification", ""),
        }
        return any(
            value
            in {
                "intentional-public-service",
                "public-static-content",
                "public-media-content",
                "public-content",
            }
            for value in intent_values
            if value
        )

    def _collect_secrets_posture(self, region: str) -> dict[str, Any]:
        """Collect KMS/Secrets Manager posture as the AWS analog of Azure Key Vault.

        NOTE: AWS has no direct "Key Vault MFA" equivalent; this approximates
        it from Secrets Manager rotation being enabled. "Purge protection" is
        approximated from KMS keys not being scheduled for deletion, since KMS
        does not expose a standing deletion-protection flag the way Azure Key
        Vault does.
        """
        kms = self._build_client("kms", region)
        keys = self._paginate_allow_failure(kms, "list_keys", items_key="Keys")

        purge_protected_count = 0
        for key in keys:
            key_id = key.get("KeyId") if isinstance(key, dict) else None
            if not key_id:
                continue
            detail = self._call_allow_failure(kms.describe_key, KeyId=key_id)
            if (
                isinstance(detail, dict)
                and detail.get("KeyMetadata", {}).get("KeyState") == "Enabled"
            ):
                purge_protected_count += 1

        secretsmanager = self._build_client("secretsmanager", region)
        secrets = self._paginate_allow_failure(
            secretsmanager, "list_secrets", items_key="SecretList"
        )
        mfa_enabled = bool(secrets) and any(
            secret.get("RotationEnabled") for secret in secrets if isinstance(secret, dict)
        )

        vault_count = len(keys)
        if vault_count == 0:
            state = "not_observed"
        elif purge_protected_count == vault_count:
            state = "observed"
        else:
            state = "partial"

        return {
            "mfa_enabled": mfa_enabled,
            "purge_protection_enabled": purge_protected_count > 0,
            "vault_count": vault_count,
            "purge_protected_count": purge_protected_count,
            "state": state,
        }

    # -- Monitoring domain -------------------------------------------------

    def _collect_monitoring_profile(
        self,
        regions: list[str],
    ) -> tuple[MonitoringProfile, dict[str, Any]]:
        """Collect AWS monitoring posture from CloudTrail, CloudWatch, GuardDuty, and Security Hub."""
        region = self._primary_region()
        cloudtrail = self._build_client("cloudtrail", region)
        trails = self._call_and_extract_items(cloudtrail.describe_trails, items_key="trailList")

        activity_log_retention_days = self._collect_cloudtrail_log_retention_days(
            cloudtrail, trails, region
        )
        centralized_logging_enabled = self._collect_centralized_logging_enabled(
            cloudtrail, trails
        )

        cloudwatch = self._build_client("cloudwatch", region)
        alarms = self._paginate_allow_failure(
            cloudwatch, "describe_alarms", items_key="MetricAlarms"
        )
        critical_alert_coverage_ratio = min(len(alarms) / 3.0, 1.0)

        defender_coverage_ratio, guardduty_enabled, securityhub_enabled = (
            self._collect_threat_detection_coverage(region)
        )
        threat_finding_counts = self._collect_threat_detection_findings(region)

        runbooks_enabled = self._collect_incident_response_runbooks_enabled(region)

        monitoring_collection_mode = (
            "aws_cloudtrail_and_cloudwatch_inventory"
            if trails or alarms
            else "default_no_monitoring_inventory"
        )

        return (
            MonitoringProfile(
                activity_log_retention_days=activity_log_retention_days,
                critical_alert_coverage_ratio=critical_alert_coverage_ratio,
                defender_coverage_ratio=defender_coverage_ratio,
                centralized_logging_enabled=centralized_logging_enabled,
                incident_response_runbooks_enabled=runbooks_enabled,
            ),
            {
                "monitoring_collection_mode": monitoring_collection_mode,
                "activity_log_alert_count": len(alarms),
                "guardduty_enabled": guardduty_enabled,
                "securityhub_enabled": securityhub_enabled,
                **threat_finding_counts,
            },
        )

    def _collect_cloudtrail_log_retention_days(
        self,
        cloudtrail: Any,
        trails: list[dict[str, Any]],
        region: str,
    ) -> int:
        log_group_arns = {
            trail.get("CloudWatchLogsLogGroupArn")
            for trail in trails
            if isinstance(trail, dict) and trail.get("CloudWatchLogsLogGroupArn")
        }
        if not log_group_arns:
            return 0

        logs = self._build_client("logs", region)
        retention_days = 0
        for arn in log_group_arns:
            group_name = str(arn).split(":log-group:")[-1].split(":")[0]
            groups = self._paginate_allow_failure(
                logs, "describe_log_groups", items_key="logGroups", logGroupNamePrefix=group_name
            )
            for group in groups:
                retention_days = max(retention_days, int(group.get("retentionInDays", 0) or 0))
        return retention_days

    def _collect_centralized_logging_enabled(
        self,
        cloudtrail: Any,
        trails: list[dict[str, Any]],
    ) -> bool:
        """Return whether a multi-region trail exists AND is actively logging.

        `IsMultiRegionTrail` alone only proves a trail is *configured*; a
        trail can exist (and satisfy that check) while logging has been
        stopped (`StopLogging`), which `get_trail_status` is the only way to
        observe. Treating existence as sufficient would let a stopped trail
        read as "centralized logging enabled."
        """
        multi_region_trail_names = [
            trail.get("Name") or trail.get("TrailARN")
            for trail in trails
            if isinstance(trail, dict) and trail.get("IsMultiRegionTrail") and (trail.get("Name") or trail.get("TrailARN"))
        ]
        for trail_name in multi_region_trail_names:
            status = self._call_allow_failure(cloudtrail.get_trail_status, Name=trail_name)
            if isinstance(status, dict) and status.get("IsLogging"):
                return True
        return False

    def _collect_threat_detection_coverage(self, region: str) -> tuple[float, bool, bool]:
        guardduty = self._build_client("guardduty", region)
        detector_ids = self._call_allow_failure(guardduty.list_detectors)
        guardduty_enabled = bool(
            isinstance(detector_ids, dict) and detector_ids.get("DetectorIds")
        )

        securityhub = self._build_client("securityhub", region)
        standards = self._call_allow_failure(securityhub.get_enabled_standards)
        securityhub_enabled = bool(
            isinstance(standards, dict) and standards.get("StandardsSubscriptions")
        )

        signals = (guardduty_enabled, securityhub_enabled)
        coverage_ratio = round(sum(1 for signal in signals if signal) / len(signals), 4)
        return coverage_ratio, guardduty_enabled, securityhub_enabled

    def _collect_threat_detection_findings(self, region: str) -> dict[str, int]:
        """Return active finding counts from GuardDuty and Security Hub.

        `_collect_threat_detection_coverage` only proves detection *tooling*
        is configured (a detector/standard exists); it says nothing about
        whether that tooling has actually found anything. A clean-looking
        account with GuardDuty enabled but unread critical findings would
        otherwise look identical to one with zero findings.
        """
        guardduty = self._build_client("guardduty", region)
        detector_ids = self._call_allow_failure(guardduty.list_detectors)
        detector_id = None
        if isinstance(detector_ids, dict):
            ids = detector_ids.get("DetectorIds") or []
            detector_id = ids[0] if ids else None

        guardduty_active_finding_count = 0
        guardduty_high_severity_finding_count = 0
        if detector_id:
            active_findings = self._paginate_allow_failure(
                guardduty,
                "list_findings",
                items_key="FindingIds",
                DetectorId=detector_id,
                FindingCriteria={"Criterion": {"service.archived": {"Eq": ["false"]}}},
            )
            guardduty_active_finding_count = len(active_findings)

            high_severity_findings = self._paginate_allow_failure(
                guardduty,
                "list_findings",
                items_key="FindingIds",
                DetectorId=detector_id,
                FindingCriteria={
                    "Criterion": {
                        "service.archived": {"Eq": ["false"]},
                        "severity": {"Gte": 7.0},
                    }
                },
            )
            guardduty_high_severity_finding_count = len(high_severity_findings)

        securityhub = self._build_client("securityhub", region)
        active_securityhub_findings = self._paginate_allow_failure(
            securityhub,
            "get_findings",
            items_key="Findings",
            Filters={
                "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
                "WorkflowStatus": [
                    {"Value": "NEW", "Comparison": "EQUALS"},
                    {"Value": "NOTIFIED", "Comparison": "EQUALS"},
                ],
            },
        )
        securityhub_active_finding_count = len(active_securityhub_findings)
        securityhub_critical_finding_count = sum(
            1
            for finding in active_securityhub_findings
            if isinstance(finding, dict)
            and finding.get("Severity", {}).get("Label") in {"CRITICAL", "HIGH"}
        )

        return {
            "guardduty_active_finding_count": guardduty_active_finding_count,
            "guardduty_high_severity_finding_count": guardduty_high_severity_finding_count,
            "securityhub_active_finding_count": securityhub_active_finding_count,
            "securityhub_critical_finding_count": securityhub_critical_finding_count,
        }

    def _collect_incident_response_runbooks_enabled(self, region: str) -> bool:
        ssm = self._build_client("ssm", region)
        documents = self._paginate_allow_failure(
            ssm,
            "list_documents",
            items_key="DocumentIdentifiers",
            Filters=[{"Key": "Owner", "Values": ["Self"]}],
        )
        return any(
            document.get("DocumentType") == "Automation"
            for document in documents
            if isinstance(document, dict)
        )

    # -- Compute domain ------------------------------------------------------

    def _collect_compute_profile(
        self,
        regions: list[str],
    ) -> tuple[ComputeProfile, dict[str, Any]]:
        """Collect AWS compute posture from EC2 inventory, SSM, AWS Backup, and Lambda.

        Lambda visibility is collected independent of EC2 presence: an
        account can be entirely serverless with zero EC2 instances, and the
        ComputeProfile's VM-shaped fields (patch state, endpoint-protection
        agents, hardened baseline) have no real Lambda analog, so Lambda
        signals are surfaced as metadata-only counters rather than forced
        into those EC2-specific ratios.
        """
        region_instance_lists = self._map_regions(regions, self._collect_ec2_instances_for_region)
        instances: list[tuple[str, dict[str, Any]]] = [
            (region, instance)
            for region, region_instances in zip(regions, region_instance_lists)
            for instance in region_instances
        ]

        lambda_metadata = self._collect_lambda_posture(regions)
        container_metadata = self._collect_container_posture(regions)

        vm_count = len(instances)
        if vm_count == 0:
            return (
                ComputeProfile(
                    unpatched_critical_vms=0,
                    endpoint_protection_coverage_ratio=0.0,
                    hardened_baseline_coverage_ratio=0.0,
                    workload_backup_agent_coverage_ratio=0.0,
                ),
                {
                    "compute_collection_mode": (
                        "aws_lambda_inventory"
                        if lambda_metadata["lambda_function_count"]
                        else "aws_container_inventory"
                        if container_metadata["ecs_cluster_count"] or container_metadata["eks_cluster_count"]
                        else "default_no_compute_inventory"
                    ),
                    "virtual_machine_count": 0,
                    **lambda_metadata,
                    **container_metadata,
                },
            )

        hardening_covered_count = sum(
            1
            for _, instance in instances
            if self._ec2_instance_meets_hardening_proxy(instance)
        )

        instance_ids_by_region: dict[str, list[str]] = {}
        for region_name, instance in instances:
            instance_id = instance.get("InstanceId")
            if instance_id:
                instance_ids_by_region.setdefault(region_name, []).append(str(instance_id))

        managed_instance_ids: set[str] = set()
        patch_compliant_count = 0
        for managed_ids, region_patch_compliant_count in self._map_regions(
            regions,
            lambda region: self._collect_ssm_patch_signals_for_region(
                region, instance_ids_by_region.get(region, [])
            ),
        ):
            managed_instance_ids.update(managed_ids)
            patch_compliant_count += region_patch_compliant_count

        backup_protected_count = self._collect_backup_protected_ec2_count(regions)
        backup_protected_count = min(backup_protected_count, vm_count)

        endpoint_coverage_ratio = round(len(managed_instance_ids) / vm_count, 4)
        hardening_coverage_ratio = round(hardening_covered_count / vm_count, 4)
        backup_coverage_ratio = round(backup_protected_count / vm_count, 4)
        unpatched_critical_vms = max(vm_count - patch_compliant_count, 0)

        return (
            ComputeProfile(
                unpatched_critical_vms=unpatched_critical_vms,
                endpoint_protection_coverage_ratio=endpoint_coverage_ratio,
                hardened_baseline_coverage_ratio=hardening_coverage_ratio,
                workload_backup_agent_coverage_ratio=backup_coverage_ratio,
                linux_password_auth_enabled_vms=0,
            ),
            {
                "compute_collection_mode": "aws_ec2_inventory",
                "virtual_machine_count": vm_count,
                "vm_extension_covered_count": len(managed_instance_ids),
                "vm_hardening_covered_count": hardening_covered_count,
                "vm_backup_protected_count": backup_protected_count,
                "vm_patch_compliant_count": patch_compliant_count,
                "linux_password_auth_enabled_vm_count": 0,
                **lambda_metadata,
                **container_metadata,
            },
        )

    def _collect_lambda_posture(self, regions: list[str]) -> dict[str, int]:
        """Return Lambda function counts and public-exposure signals across regions.

        Lambda is a totally blind spot without this: the EC2-only compute
        domain has no visibility into an account that runs serverless
        workloads, and a public Function URL or a wildcard resource policy
        is a direct, common misconfiguration analogous to a public S3
        bucket.
        """
        function_count = 0
        public_url_count = 0
        public_policy_count = 0

        for region_result in self._map_regions(regions, self._collect_lambda_signals_for_region):
            region_function_count, region_public_url_count, region_public_policy_count = (
                region_result
            )
            function_count += region_function_count
            public_url_count += region_public_url_count
            public_policy_count += region_public_policy_count

        return {
            "lambda_function_count": function_count,
            "lambda_functions_with_public_url_count": public_url_count,
            "lambda_functions_with_public_policy_count": public_policy_count,
        }

    def _collect_lambda_signals_for_region(self, region: str) -> tuple[int, int, int]:
        """Return (function_count, public_url_count, public_policy_count) for one region."""
        lambda_client = self._build_client("lambda", region)
        functions = self._paginate_allow_failure(
            lambda_client, "list_functions", items_key="Functions"
        )

        public_url_count = 0
        public_policy_count = 0
        for function in functions:
            function_name = function.get("FunctionName") if isinstance(function, dict) else None
            if not function_name:
                continue

            url_config = self._call_allow_failure(
                lambda_client.get_function_url_config, FunctionName=function_name
            )
            if isinstance(url_config, dict) and url_config.get("AuthType") == "NONE":
                public_url_count += 1

            if self._lambda_function_policy_is_public(lambda_client, function_name):
                public_policy_count += 1

        return (len(functions), public_url_count, public_policy_count)

    def _lambda_function_policy_is_public(self, lambda_client: Any, function_name: str) -> bool:
        policy_response = self._call_allow_failure(
            lambda_client.get_policy, FunctionName=function_name
        )
        if not isinstance(policy_response, dict):
            return False

        try:
            import json

            document = json.loads(policy_response.get("Policy", "{}"))
        except (TypeError, ValueError):
            return False

        statements = document.get("Statement", [])
        if isinstance(statements, dict):
            statements = [statements]

        for statement in statements:
            if not isinstance(statement, dict) or statement.get("Effect") != "Allow":
                continue
            principal = statement.get("Principal")
            principal_is_wildcard = principal == "*" or (
                isinstance(principal, dict) and principal.get("AWS") == "*"
            )
            if principal_is_wildcard and not statement.get("Condition"):
                return True
        return False

    def _collect_container_posture(self, regions: list[str]) -> dict[str, int]:
        """Return ECS and EKS cluster counts and EKS public-endpoint exposure across regions.

        Like Lambda, container orchestration has no analog in the VM-shaped
        ComputeProfile ratios, so this is collected independent of EC2
        presence and surfaced as metadata-only counters. Without this, an
        account running entirely on ECS/EKS would be just as invisible to
        the compute domain as a serverless-only account was before Lambda
        visibility was added.
        """
        ecs_cluster_count = 0
        ecs_active_service_count = 0
        eks_cluster_count = 0
        eks_public_endpoint_count = 0
        eks_unrestricted_public_endpoint_count = 0

        for region_result in self._map_regions(regions, self._collect_container_signals_for_region):
            (
                region_ecs_cluster_count,
                region_ecs_active_service_count,
                region_eks_cluster_count,
                region_eks_public_endpoint_count,
                region_eks_unrestricted_public_endpoint_count,
            ) = region_result
            ecs_cluster_count += region_ecs_cluster_count
            ecs_active_service_count += region_ecs_active_service_count
            eks_cluster_count += region_eks_cluster_count
            eks_public_endpoint_count += region_eks_public_endpoint_count
            eks_unrestricted_public_endpoint_count += region_eks_unrestricted_public_endpoint_count

        return {
            "ecs_cluster_count": ecs_cluster_count,
            "ecs_active_service_count": ecs_active_service_count,
            "eks_cluster_count": eks_cluster_count,
            "eks_clusters_with_public_endpoint_count": eks_public_endpoint_count,
            "eks_clusters_with_unrestricted_public_endpoint_count": eks_unrestricted_public_endpoint_count,
        }

    def _collect_container_signals_for_region(self, region: str) -> tuple[int, int, int, int, int]:
        """Return (ecs_cluster_count, ecs_active_service_count, eks_cluster_count, eks_public_count, eks_unrestricted_count) for one region."""
        ecs = self._build_client("ecs", region)
        cluster_arns = self._paginate_allow_failure(ecs, "list_clusters", items_key="clusterArns")
        ecs_active_service_count = 0
        if cluster_arns:
            described = self._call_allow_failure(ecs.describe_clusters, clusters=cluster_arns)
            clusters = described.get("clusters", []) if isinstance(described, dict) else []
            ecs_active_service_count = sum(
                int(cluster.get("activeServicesCount", 0) or 0)
                for cluster in clusters
                if isinstance(cluster, dict)
            )

        eks = self._build_client("eks", region)
        eks_cluster_names = self._paginate_allow_failure(eks, "list_clusters", items_key="clusters")
        eks_public_endpoint_count = 0
        eks_unrestricted_public_endpoint_count = 0
        for cluster_name in eks_cluster_names:
            detail = self._call_allow_failure(eks.describe_cluster, name=cluster_name)
            if not isinstance(detail, dict):
                continue
            vpc_config = detail.get("cluster", {}).get("resourcesVpcConfig", {})
            if not vpc_config.get("endpointPublicAccess"):
                continue
            eks_public_endpoint_count += 1
            public_cidrs = vpc_config.get("publicAccessCidrs", []) or []
            if "0.0.0.0/0" in public_cidrs or not public_cidrs:
                eks_unrestricted_public_endpoint_count += 1

        return (
            len(cluster_arns),
            ecs_active_service_count,
            len(eks_cluster_names),
            eks_public_endpoint_count,
            eks_unrestricted_public_endpoint_count,
        )

    @staticmethod
    def _ec2_instance_meets_hardening_proxy(instance: dict[str, Any]) -> bool:
        """Return whether an EC2 instance enforces IMDSv2 (the available hardening proxy).

        NOTE: unlike AzureCollector's hardening proxy, this does not also
        check root-volume encryption (would require one extra
        describe_volumes call per instance); IMDSv2 enforcement alone is
        used as the v1 proxy.
        """
        metadata_options = instance.get("MetadataOptions", {}) or {}
        return metadata_options.get("HttpTokens") == "required"

    def _collect_ec2_instances_for_region(self, region: str) -> list[dict[str, Any]]:
        ec2 = self._build_client("ec2", region)
        reservations = self._paginate_allow_failure(
            ec2, "describe_instances", items_key="Reservations"
        )
        return [
            instance
            for reservation in reservations
            for instance in reservation.get("Instances", []) or []
            if isinstance(instance, dict)
        ]

    def _collect_ssm_patch_signals_for_region(
        self,
        region: str,
        instance_ids: list[str],
    ) -> tuple[set[str], int]:
        """Return (managed_instance_ids, patch_compliant_count) for one region."""
        ssm = self._build_client("ssm", region)
        managed = self._paginate_allow_failure(
            ssm, "describe_instance_information", items_key="InstanceInformationList"
        )
        managed_instance_ids = {
            str(entry.get("InstanceId"))
            for entry in managed
            if isinstance(entry, dict) and entry.get("InstanceId")
        }
        if not instance_ids:
            return managed_instance_ids, 0

        # describe_instance_patch_states accepts at most 50 instance IDs per
        # call (a request-shape limit, not output pagination), so chunking
        # the input is required to avoid silently dropping instances beyond
        # the first 50 in any one region.
        patch_states: list[Any] = []
        for chunk in self._chunked(instance_ids, 50):
            patch_states.extend(
                self._paginate_allow_failure(
                    ssm,
                    "describe_instance_patch_states",
                    items_key="InstancePatchStates",
                    InstanceIds=chunk,
                )
            )
        patch_compliant_count = sum(
            1
            for state in patch_states
            if isinstance(state, dict) and state.get("InstancesWithCriticalNonCompliantPatches", 0) == 0
        )
        return managed_instance_ids, patch_compliant_count

    @staticmethod
    def _chunked(items: list[str], size: int) -> list[list[str]]:
        return [items[index : index + size] for index in range(0, len(items), size)]

    def _collect_backup_protected_ec2_count(self, regions: list[str]) -> int:
        protected_arns: set[str] = set()
        for region_arns in self._map_regions(regions, self._collect_backup_protected_ec2_arns_for_region):
            protected_arns.update(region_arns)
        return len(protected_arns)

    def _collect_backup_protected_ec2_arns_for_region(self, region: str) -> set[str]:
        backup = self._build_client("backup", region)
        resources = self._paginate_allow_failure(
            backup, "list_protected_resources", items_key="Results"
        )
        return {
            str(resource.get("ResourceArn"))
            for resource in resources
            if isinstance(resource, dict)
            and resource.get("ResourceType") == "EC2"
            and resource.get("ResourceArn")
        }

    # -- Governance domain ---------------------------------------------------

    def _collect_governance_profile(
        self,
        regions: list[str],
        account_id: str,
    ) -> tuple[GovernanceProfile, dict[str, Any]]:
        """Collect AWS governance posture from resource tagging, Budgets, Organizations, and EC2."""
        total_resources = 0
        tagged_resources = 0
        for resources in self._map_regions(regions, self._collect_tagged_resources_for_region):
            total_resources += len(resources)
            tagged_resources += sum(
                1
                for resource in resources
                if isinstance(resource, dict) and resource.get("Tags")
            )

        tagging_coverage_ratio = (
            round(tagged_resources / total_resources, 4) if total_resources else 0.0
        )

        budget_posture = self._collect_budget_posture(account_id)
        policy_assignment_count = self._collect_scp_count()
        policy_assignment_coverage_ratio = min(policy_assignment_count / 5.0, 1.0)
        orphaned_resource_count = self._collect_orphaned_resource_count(regions)
        config_posture = self._collect_aws_config_posture(self._primary_region())

        return (
            GovernanceProfile(
                tagging_coverage_ratio=tagging_coverage_ratio,
                budget_alerts_enabled=budget_posture["enabled"],
                budget_api_accessible=budget_posture["api_accessible"],
                budget_alert_count=budget_posture["budget_count"],
                budget_evidence_state=budget_posture["state"],
                policy_assignment_coverage_ratio=policy_assignment_coverage_ratio,
                orphaned_resource_count=orphaned_resource_count,
            ),
            {
                "governance_collection_mode": (
                    "aws_resource_tagging_inventory"
                    if total_resources or policy_assignment_count or orphaned_resource_count
                    else "default_no_governance_inventory"
                ),
                "governance_resource_count": total_resources,
                "policy_assignment_count": policy_assignment_count,
                "orphaned_resource_count": orphaned_resource_count,
                "budget_api_accessible": budget_posture["api_accessible"],
                "budget_alert_count": budget_posture["budget_count"],
                "budget_evidence_state": budget_posture["state"],
                **config_posture,
            },
        )

    def _collect_aws_config_posture(self, region: str) -> dict[str, Any]:
        """Collect AWS Config recorder status and rule-compliance summary.

        Without this, drift/compliance visibility is entirely absent: the
        rest of this collector infers posture from individual service APIs,
        but never checks whether AWS Config itself is recording or what its
        own rule evaluations already concluded.
        """
        config_client = self._build_client("config", region)

        recorder_statuses = self._call_and_extract_items(
            config_client.describe_configuration_recorder_status,
            items_key="ConfigurationRecordersStatus",
        )
        recorder_enabled = any(
            isinstance(status, dict) and status.get("recording")
            for status in recorder_statuses
        )

        summary = self._call_allow_failure(
            config_client.get_compliance_summary_by_config_rule
        )
        compliant_count = 0
        noncompliant_count = 0
        if isinstance(summary, dict):
            compliance_summary = summary.get("ComplianceSummary", {})
            compliant_count = int(
                compliance_summary.get("CompliantResourceCount", {}).get("CappedCount", 0) or 0
            )
            noncompliant_count = int(
                compliance_summary.get("NonCompliantResourceCount", {}).get("CappedCount", 0) or 0
            )

        return {
            "config_recorder_enabled": recorder_enabled,
            "config_compliant_rule_count": compliant_count,
            "config_noncompliant_rule_count": noncompliant_count,
        }

    def _collect_budget_posture(self, account_id: str) -> dict[str, Any]:
        """Collect AWS Budgets posture; the Budgets API is only available in us-east-1."""
        budgets = self._build_client("budgets", "us-east-1")
        budget_list = self._paginate_allow_failure(
            budgets, "describe_budgets", items_key="Budgets", AccountId=account_id
        )
        if not budget_list:
            accessible = self._call_allow_failure(
                budgets.describe_budgets, AccountId=account_id
            )
            return {
                "enabled": False,
                "api_accessible": accessible is not None,
                "budget_count": 0,
                "state": "observed_empty" if accessible is not None else "unavailable",
            }

        notification_count = 0
        for budget in budget_list:
            budget_name = budget.get("BudgetName") if isinstance(budget, dict) else None
            if not budget_name:
                continue
            notifications = self._paginate_allow_failure(
                budgets,
                "describe_notifications_for_budget",
                items_key="Notifications",
                AccountId=account_id,
                BudgetName=budget_name,
            )
            notification_count += len(notifications)

        return {
            "enabled": notification_count > 0,
            "api_accessible": True,
            "budget_count": len(budget_list),
            "state": "observed",
        }

    def _collect_scp_count(self) -> int:
        """Return the number of Organizations service control policies, or 0 if inaccessible."""
        organizations = self._build_client("organizations", "us-east-1")
        policies = self._paginate_allow_failure(
            organizations,
            "list_policies",
            items_key="Policies",
            Filter="SERVICE_CONTROL_POLICY",
        )
        return len(policies)

    def _collect_orphaned_resource_count(self, regions: list[str]) -> int:
        """Return the count of unattached EBS volumes and unassociated Elastic IPs."""
        return sum(self._map_regions(regions, self._collect_orphaned_resource_count_for_region))

    def _collect_tagged_resources_for_region(self, region: str) -> list[dict[str, Any]]:
        tagging_api = self._build_client("resourcegroupstaggingapi", region)
        return self._paginate_allow_failure(
            tagging_api, "get_resources", items_key="ResourceTagMappingList"
        )

    def _collect_orphaned_resource_count_for_region(self, region: str) -> int:
        ec2 = self._build_client("ec2", region)
        volumes = self._paginate_allow_failure(
            ec2,
            "describe_volumes",
            items_key="Volumes",
            Filters=[{"Name": "status", "Values": ["available"]}],
        )
        addresses = self._call_and_extract_items(ec2.describe_addresses, items_key="Addresses")
        unassociated_addresses = sum(
            1
            for address in addresses
            if isinstance(address, dict) and not address.get("AssociationId")
        )
        return len(volumes) + unassociated_addresses

    # -- IoT domain ----------------------------------------------------------

    def _collect_iot_profile(
        self,
        regions: list[str],
    ) -> tuple[IotProfile | None, dict[str, Any]]:
        """Collect AWS IoT Core posture as the analog of Azure IoT Hub.

        NOTE: this is the weakest cross-provider analog of the seven domains.
        AWS IoT Core has no "hub" resource; "iot_hub_count" is approximated
        from IoT Thing Group count, and several Azure IoT Hub concepts
        (clinical/operational boundary documentation) have no AWS signal at
        all and are conservatively left at their model defaults, exactly as
        AzureCollector itself does for the same fields.
        """
        region = self._primary_region()
        iot = self._build_client("iot", region)

        things = self._paginate_allow_failure(iot, "list_things", items_key="things")
        thing_groups = self._paginate_allow_failure(
            iot, "list_thing_groups", items_key="thingGroups"
        )

        if not things and not thing_groups:
            return (
                None,
                {
                    "iot_collection_mode": "default_no_iot_hub_inventory",
                    "iot_hub_count": 0,
                    "iot_device_identity_count": 0,
                    "iot_device_identity_observable": False,
                    "iot_shared_access_policy_count": 0,
                    "iot_overbroad_shared_access_policy_count": 0,
                    "iot_diagnostic_destination_count": 0,
                    "iot_defender_enabled": False,
                    "iot_public_network_hub_count": 0,
                    "iot_private_endpoint_count": 0,
                    "iot_alert_rule_count": 0,
                },
            )

        hub_count = len(thing_groups) or 1
        device_identity_count = len(things)

        certificates = self._paginate_allow_failure(
            iot, "list_certificates", items_key="certificates"
        )
        certificate_authority_configured = bool(certificates)

        policies = self._paginate_allow_failure(iot, "list_policies", items_key="policies")
        shared_access_policy_count = len(policies)
        overbroad_shared_access_policy_count = sum(
            1
            for policy in policies
            if isinstance(policy, dict) and self._iot_policy_is_overbroad(iot, policy)
        )

        topic_rules = self._paginate_allow_failure(
            iot, "list_topic_rules", items_key="rules"
        )
        diagnostic_destination_count = self._collect_iot_diagnostic_destination_count(
            iot, topic_rules
        )

        security_profiles = self._paginate_allow_failure(
            iot, "list_security_profiles", items_key="securityProfileIdentifiers"
        )
        defender_iot_enabled = bool(security_profiles)

        vpc_endpoint_count = self._collect_iot_vpc_endpoint_count(regions)

        return (
            IotProfile(
                iot_hub_count=hub_count,
                device_identity_count=device_identity_count,
                device_identity_observable=bool(things),
                certificate_authority_configured=certificate_authority_configured,
                shared_access_policy_count=shared_access_policy_count,
                overbroad_shared_access_policy_count=overbroad_shared_access_policy_count,
                diagnostic_settings_enabled=diagnostic_destination_count > 0,
                diagnostic_destination_count=diagnostic_destination_count,
                diagnostic_category_coverage_ratio=(
                    1.0 if diagnostic_destination_count > 0 else 0.0
                ),
                defender_iot_enabled=defender_iot_enabled,
                iot_security_monitoring_observable=True,
                public_network_access_enabled=vpc_endpoint_count == 0,
                allowed_ip_rule_count=0,
                private_endpoint_count=vpc_endpoint_count,
                private_endpoint_required=hub_count > 0,
                message_route_count=len(topic_rules),
                telemetry_retention_days=30 if diagnostic_destination_count else 0,
                telemetry_storage_governed=diagnostic_destination_count > 0,
                iot_key_vault_linked=False,
                iot_secret_rotation_observable=False,
                alert_rule_count=0,
                action_group_count=0,
                clinical_operational_boundary_documented=False,
                device_evidence_required_count=0 if things else hub_count,
                clinical_operational_evidence_required_count=hub_count,
                evidence_state="observed" if things else "partial",
            ),
            {
                "iot_collection_mode": "aws_iot_core_inventory",
                "iot_hub_count": hub_count,
                "iot_device_identity_count": device_identity_count,
                "iot_device_identity_observable": bool(things),
                "iot_shared_access_policy_count": shared_access_policy_count,
                "iot_overbroad_shared_access_policy_count": overbroad_shared_access_policy_count,
                "iot_diagnostic_destination_count": diagnostic_destination_count,
                "iot_defender_enabled": defender_iot_enabled,
                "iot_public_network_hub_count": 1 if vpc_endpoint_count == 0 else 0,
                "iot_private_endpoint_count": vpc_endpoint_count,
                "iot_alert_rule_count": 0,
            },
        )

    def _iot_policy_is_overbroad(self, iot: Any, policy: dict[str, Any]) -> bool:
        policy_name = policy.get("policyName")
        if not policy_name:
            return False
        detail = self._call_allow_failure(iot.get_policy, policyName=policy_name)
        if not isinstance(detail, dict):
            return False
        try:
            import json

            document = json.loads(detail.get("policyDocument", "{}"))
        except (TypeError, ValueError):
            return False

        statements = document.get("Statement", [])
        if isinstance(statements, dict):
            statements = [statements]
        for statement in statements:
            if not isinstance(statement, dict):
                continue
            actions = statement.get("Action", [])
            resources = statement.get("Resource", [])
            actions = [actions] if isinstance(actions, str) else actions
            resources = [resources] if isinstance(resources, str) else resources
            if "iot:*" in actions and "*" in resources:
                return True
        return False

    def _collect_iot_diagnostic_destination_count(
        self,
        iot: Any,
        topic_rules: list[dict[str, Any]],
    ) -> int:
        destination_count = 0
        for rule_summary in topic_rules:
            rule_name = rule_summary.get("ruleName") if isinstance(rule_summary, dict) else None
            if not rule_name:
                continue
            detail = self._call_allow_failure(iot.get_topic_rule, ruleName=rule_name)
            if not isinstance(detail, dict):
                continue
            actions = detail.get("rule", {}).get("actions", [])
            destination_count += sum(
                1
                for action in actions
                if isinstance(action, dict)
                and ({"cloudwatchMetric", "cloudwatchAlarm", "cloudwatchLogs", "s3", "kinesis"} & action.keys())
            )
        return destination_count

    def _collect_iot_vpc_endpoint_count(self, regions: list[str]) -> int:
        return sum(self._map_regions(regions, self._collect_iot_vpc_endpoint_count_for_region))

    def _collect_iot_vpc_endpoint_count_for_region(self, region: str) -> int:
        ec2 = self._build_client("ec2", region)
        endpoints = self._paginate_allow_failure(
            ec2,
            "describe_vpc_endpoints",
            items_key="VpcEndpoints",
            Filters=[
                {
                    "Name": "service-name",
                    "Values": [f"com.amazonaws.{region}.iot.data"],
                }
            ],
        )
        return len(endpoints)
