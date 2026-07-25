# Healthcare IoT controls for cloud-hosted IoMT governance assessments.
from __future__ import annotations

from collections.abc import Callable, Iterable

from cris_sme.controls.common import build_control_finding
from cris_sme.models.cloud_profile import CloudProfile, IotProfile
from cris_sme.models.finding import Finding, FindingSeverity


def evaluate_iot_controls(profiles: list[CloudProfile]) -> list[Finding]:
    """Evaluate optional Healthcare IoT controls across collected profiles."""
    findings: list[Finding] = []

    for profile in profiles:
        iot = profile.iot
        if iot is None or iot.iot_hub_count == 0:
            continue

        evaluators: Iterable[Callable[[CloudProfile, IotProfile], list[Finding]]] = (
            _evaluate_device_identity,
            _evaluate_shared_access_policy,
            _evaluate_diagnostic_logging,
            _evaluate_defender_iot,
            _evaluate_public_access,
            _evaluate_private_endpoint,
            _evaluate_telemetry_governance,
            _evaluate_secret_governance,
            _evaluate_clinical_alerting,
            _evaluate_clinical_boundary,
        )
        for evaluator in evaluators:
            findings.extend(evaluator(profile, iot))

    return findings


def _metadata(iot: IotProfile, **extra: object) -> dict[str, object]:
    return {
        "iomt_evidence_state": iot.evidence_state,
        "iot_hub_count": iot.iot_hub_count,
        "device_identity_count": iot.device_identity_count,
        **extra,
    }


def _evaluate_device_identity(profile: CloudProfile, iot: IotProfile) -> list[Finding]:
    if (
        iot.device_identity_observable
        and iot.device_identity_count > 0
        and iot.certificate_authority_configured
    ):
        return []

    evidence: list[str] = []
    if not iot.device_identity_observable:
        evidence.append("IoT device identity inventory was not observable in this run")
    if iot.device_identity_count == 0:
        evidence.append("No IoT device identities were visible for the assessed hub scope")
    if not iot.certificate_authority_configured:
        evidence.append("Certificate-authority based device authentication was not observed")

    return [
        build_control_finding(
            profile=profile,
            control_id="IOT-001",
            severity=FindingSeverity.HIGH,
            evidence=evidence,
            is_compliant=False,
            confidence=0.84 if iot.device_identity_observable else 0.72,
            exposure=0.65,
            remediation_effort=0.5,
            generated_by="iot_controls",
            metadata=_metadata(
                iot,
                device_identity_observable=iot.device_identity_observable,
                certificate_authority_configured=iot.certificate_authority_configured,
            ),
        )
    ]


def _evaluate_shared_access_policy(profile: CloudProfile, iot: IotProfile) -> list[Finding]:
    if iot.overbroad_shared_access_policy_count == 0 and iot.shared_access_policy_count <= 4:
        return []

    evidence = [
        f"{iot.shared_access_policy_count} IoT shared access policie(s) were observed",
    ]
    if iot.overbroad_shared_access_policy_count:
        evidence.append(
            f"{iot.overbroad_shared_access_policy_count} shared access policie(s) appear overbroad"
        )

    return [
        build_control_finding(
            profile=profile,
            control_id="IOT-002",
            severity=FindingSeverity.HIGH
            if iot.overbroad_shared_access_policy_count
            else FindingSeverity.MEDIUM,
            evidence=evidence,
            is_compliant=False,
            confidence=0.86,
            exposure=0.7,
            remediation_effort=0.4,
            generated_by="iot_controls",
            metadata=_metadata(
                iot,
                shared_access_policy_count=iot.shared_access_policy_count,
                overbroad_shared_access_policy_count=(
                    iot.overbroad_shared_access_policy_count
                ),
            ),
        )
    ]


def _evaluate_diagnostic_logging(profile: CloudProfile, iot: IotProfile) -> list[Finding]:
    if (
        iot.diagnostic_settings_enabled
        and iot.diagnostic_destination_count > 0
        and iot.diagnostic_category_coverage_ratio >= 0.8
    ):
        return []

    evidence = []
    if not iot.diagnostic_settings_enabled:
        evidence.append("IoT Hub diagnostic settings were not enabled")
    if iot.diagnostic_destination_count == 0:
        evidence.append("No diagnostic destination was observed for IoT telemetry logs")
    if iot.diagnostic_category_coverage_ratio < 0.8:
        evidence.append(
            "IoT diagnostic category coverage is below the 80% baseline"
        )

    return [
        build_control_finding(
            profile=profile,
            control_id="IOT-003",
            severity=FindingSeverity.MEDIUM,
            evidence=evidence,
            is_compliant=False,
            confidence=0.9,
            exposure=0.55,
            remediation_effort=0.35,
            generated_by="iot_controls",
            metadata=_metadata(
                iot,
                diagnostic_settings_enabled=iot.diagnostic_settings_enabled,
                diagnostic_destination_count=iot.diagnostic_destination_count,
                diagnostic_category_coverage_ratio=(
                    iot.diagnostic_category_coverage_ratio
                ),
            ),
        )
    ]


def _evaluate_defender_iot(profile: CloudProfile, iot: IotProfile) -> list[Finding]:
    if iot.iot_security_monitoring_observable and iot.defender_iot_enabled:
        return []

    evidence = []
    if not iot.iot_security_monitoring_observable:
        evidence.append("IoT security monitoring state was not observable")
    if not iot.defender_iot_enabled:
        evidence.append("Defender for IoT coverage was not observed for the hub scope")

    return [
        build_control_finding(
            profile=profile,
            control_id="IOT-004",
            severity=FindingSeverity.MEDIUM,
            evidence=evidence,
            is_compliant=False,
            confidence=0.76 if iot.iot_security_monitoring_observable else 0.68,
            exposure=0.55,
            remediation_effort=0.55,
            generated_by="iot_controls",
            metadata=_metadata(
                iot,
                defender_iot_enabled=iot.defender_iot_enabled,
                iot_security_monitoring_observable=(
                    iot.iot_security_monitoring_observable
                ),
            ),
        )
    ]


def _evaluate_public_access(profile: CloudProfile, iot: IotProfile) -> list[Finding]:
    if (
        not iot.public_network_access_enabled
        or iot.allowed_ip_rule_count > 0
        or iot.private_endpoint_count > 0
    ):
        return []

    return [
        build_control_finding(
            profile=profile,
            control_id="IOT-005",
            severity=FindingSeverity.HIGH,
            evidence=[
                "IoT Hub public network access is enabled",
                "No IP filter rules or private endpoints were observed for the hub scope",
            ],
            is_compliant=False,
            confidence=0.88,
            exposure=0.9,
            remediation_effort=0.45,
            generated_by="iot_controls",
            metadata=_metadata(
                iot,
                public_network_access_enabled=iot.public_network_access_enabled,
                allowed_ip_rule_count=iot.allowed_ip_rule_count,
                private_endpoint_count=iot.private_endpoint_count,
            ),
        )
    ]


def _evaluate_private_endpoint(profile: CloudProfile, iot: IotProfile) -> list[Finding]:
    uncompensated_public_ingestion = (
        iot.public_network_access_enabled
        and iot.allowed_ip_rule_count == 0
        and not iot.certificate_authority_configured
    )
    if (
        not iot.private_endpoint_required
        or iot.private_endpoint_count > 0
        or not uncompensated_public_ingestion
    ):
        return []

    return [
        build_control_finding(
            profile=profile,
            control_id="IOT-006",
            severity=FindingSeverity.MEDIUM,
            evidence=[
                "IoT Hub public network access is enabled without IP filter evidence",
                "Certificate-authority based device authentication was not observed",
                "No private endpoint was observed for the IoT Hub scope",
            ],
            is_compliant=False,
            confidence=0.82,
            exposure=0.65,
            remediation_effort=0.55,
            generated_by="iot_controls",
            metadata=_metadata(
                iot,
                private_endpoint_required=iot.private_endpoint_required,
                private_endpoint_count=iot.private_endpoint_count,
                public_network_access_enabled=iot.public_network_access_enabled,
                allowed_ip_rule_count=iot.allowed_ip_rule_count,
                certificate_authority_configured=iot.certificate_authority_configured,
                decision_basis=(
                    "conditional_private_endpoint_gap_requires_public_exposure_"
                    "without_ip_filter_or_certificate_evidence"
                ),
            ),
        )
    ]


def _evaluate_telemetry_governance(profile: CloudProfile, iot: IotProfile) -> list[Finding]:
    if (
        iot.message_route_count > 0
        and iot.telemetry_retention_days >= 30
        and iot.telemetry_storage_governed
    ):
        return []

    evidence = []
    if iot.message_route_count == 0:
        evidence.append("No IoT telemetry message route was observed")
    if iot.telemetry_retention_days < 30:
        evidence.append(
            f"IoT telemetry retention is {iot.telemetry_retention_days} day(s), below the 30-day baseline"
        )
    if not iot.telemetry_storage_governed:
        evidence.append("Telemetry storage governance was not observed")

    return [
        build_control_finding(
            profile=profile,
            control_id="IOT-007",
            severity=FindingSeverity.MEDIUM,
            evidence=evidence,
            is_compliant=False,
            confidence=0.8,
            exposure=0.5,
            remediation_effort=0.5,
            generated_by="iot_controls",
            metadata=_metadata(
                iot,
                message_route_count=iot.message_route_count,
                telemetry_retention_days=iot.telemetry_retention_days,
                telemetry_storage_governed=iot.telemetry_storage_governed,
            ),
        )
    ]


def _evaluate_secret_governance(profile: CloudProfile, iot: IotProfile) -> list[Finding]:
    if iot.iot_key_vault_linked and iot.iot_secret_rotation_observable:
        return []

    evidence = []
    if not iot.iot_key_vault_linked:
        evidence.append("IoT credentials were not linked to a governed key vault path")
    if not iot.iot_secret_rotation_observable:
        evidence.append("IoT credential rotation evidence was not observable")

    return [
        build_control_finding(
            profile=profile,
            control_id="IOT-008",
            severity=FindingSeverity.MEDIUM,
            evidence=evidence,
            is_compliant=False,
            confidence=0.74,
            exposure=0.6,
            remediation_effort=0.5,
            generated_by="iot_controls",
            metadata=_metadata(
                iot,
                iot_key_vault_linked=iot.iot_key_vault_linked,
                iot_secret_rotation_observable=iot.iot_secret_rotation_observable,
            ),
        )
    ]


def _evaluate_clinical_alerting(profile: CloudProfile, iot: IotProfile) -> list[Finding]:
    if iot.alert_rule_count > 0 and iot.action_group_count > 0:
        return []

    evidence = []
    if iot.alert_rule_count == 0:
        evidence.append("No IoT-specific clinical or operational alert rule was observed")
    if iot.action_group_count == 0:
        evidence.append("No action group was observed for IoT alert routing")

    return [
        build_control_finding(
            profile=profile,
            control_id="IOT-009",
            severity=FindingSeverity.MEDIUM,
            evidence=evidence,
            is_compliant=False,
            confidence=0.83,
            exposure=0.45,
            remediation_effort=0.45,
            generated_by="iot_controls",
            metadata=_metadata(
                iot,
                alert_rule_count=iot.alert_rule_count,
                action_group_count=iot.action_group_count,
            ),
        )
    ]


def _evaluate_clinical_boundary(profile: CloudProfile, iot: IotProfile) -> list[Finding]:
    if (
        iot.clinical_operational_boundary_documented
        and iot.device_evidence_required_count == 0
        and iot.clinical_operational_evidence_required_count == 0
    ):
        return []

    evidence = []
    if not iot.clinical_operational_boundary_documented:
        evidence.append(
            "Clinical and operational ownership boundary was not documented in collected evidence"
        )
    if iot.device_evidence_required_count:
        evidence.append(
            f"{iot.device_evidence_required_count} device-level evidence item(s) require clinical asset validation"
        )
    if iot.clinical_operational_evidence_required_count:
        evidence.append(
            f"{iot.clinical_operational_evidence_required_count} operational evidence item(s) require human confirmation"
        )

    return [
        build_control_finding(
            profile=profile,
            control_id="IOT-010",
            severity=FindingSeverity.LOW,
            evidence=evidence,
            is_compliant=False,
            confidence=0.9,
            exposure=0.35,
            remediation_effort=0.4,
            generated_by="iot_controls",
            metadata=_metadata(
                iot,
                clinical_operational_boundary_documented=(
                    iot.clinical_operational_boundary_documented
                ),
                device_evidence_required_count=iot.device_evidence_required_count,
                clinical_operational_evidence_required_count=(
                    iot.clinical_operational_evidence_required_count
                ),
            ),
        )
    ]
