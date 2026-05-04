# Provider evidence contract generation for CRIS-SME control governance.
from __future__ import annotations

from cris_sme.models.platform import (
    ProviderEvidenceContract,
    ProviderEvidenceContractCatalog,
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
            support_status = str(spec.provider_support.get(provider, "unsupported")).lower()
            contracts.append(
                ProviderEvidenceContract(
                    contract_id=f"pec_{provider}_{spec.control_id.lower()}_{spec.version}",
                    provider=provider,
                    control_id=spec.control_id,
                    control_version=spec.version,
                    domain=spec.domain,
                    support_status=support_status,
                    evidence_requirements=list(spec.evidence_requirements),
                    freshness_hours=_freshness_hours(spec.domain),
                    sufficiency_policy=_sufficiency_policy(support_status),
                    confidence_penalty_rules=list(spec.confidence_penalty_rules),
                    known_limitations=list(spec.known_limitations),
                    activation_gate=_activation_gate(provider, support_status),
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
    return f"{provider} support is not available for this control."


def _support_status_counts(
    contracts: list[ProviderEvidenceContract],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for contract in contracts:
        counts[contract.support_status] = counts.get(contract.support_status, 0) + 1
    return counts
