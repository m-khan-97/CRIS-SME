// Static mirror of the healthcare-evidence narrative fields in
// data/iomt_healthcare_control_mapping.json (version "2026-05-18").
// This is reference/policy data, not per-assessment data -- it changes
// rarely, so it is copied here deliberately rather than fetched at runtime.
// Re-sync by hand if the source JSON's mapping_review/evidence_class fields
// change.

export type IomtEvidenceClass = "direct_cloud" | "inferred_cloud" | "clinical_operational_required";

export interface IomtControlMappingEntry {
  controlId: string;
  evidenceClass: IomtEvidenceClass;
  ncscCafObjectives: string[];
  nhsDsptOutcomes: { outcomeId: string; name: string }[];
  cloudSupportedClaim: string;
  evidenceLimitation: string;
  expertReviewQuestion: string;
}

export const IOMT_EVIDENCE_CLASS_LABEL: Record<IomtEvidenceClass, string> = {
  direct_cloud: "Direct cloud evidence",
  inferred_cloud: "Inferred cloud evidence",
  clinical_operational_required: "Requires human validation",
};

export const IOMT_CONTROL_MAPPING: Record<string, IomtControlMappingEntry> = {
  "IOT-001": {
    controlId: "IOT-001",
    evidenceClass: "direct_cloud",
    ncscCafObjectives: ["B2 identity and access control"],
    nhsDsptOutcomes: [
      { outcomeId: "B2.a", name: "Identity verification, authentication and authorisation" },
    ],
    cloudSupportedClaim:
      "Azure IoT Hub device identity inventory and authentication metadata can support a cloud-side registration and device-access governance claim.",
    evidenceLimitation:
      "It does not validate device-side credential storage, firmware trust anchors, biomedical asset ownership, or whether a registered identity maps to an authorised clinical device.",
    expertReviewQuestion:
      "Is device identity inventory a meaningful healthcare IoT assurance signal when explicitly bounded to cloud registration and authentication metadata?",
  },
  "IOT-002": {
    controlId: "IOT-002",
    evidenceClass: "direct_cloud",
    ncscCafObjectives: ["B2 identity and access control"],
    nhsDsptOutcomes: [
      { outcomeId: "B2.a", name: "Identity verification, authentication and authorisation" },
      { outcomeId: "B3.a", name: "Secure configuration" },
    ],
    cloudSupportedClaim:
      "IoT Hub shared access policy names, counts, and rights can support a least-privilege cloud access governance claim.",
    evidenceLimitation:
      "It does not prove how applications use keys, whether secrets are rotated in practice, or whether emergency access procedures are clinically approved.",
    expertReviewQuestion:
      "Are overbroad shared access policies a valid healthcare IoT governance risk when framed as non-human/application authority over ingestion and device-management paths?",
  },
  "IOT-003": {
    controlId: "IOT-003",
    evidenceClass: "direct_cloud",
    ncscCafObjectives: ["C1 security monitoring"],
    nhsDsptOutcomes: [{ outcomeId: "C1.a", name: "Monitoring coverage" }],
    cloudSupportedClaim:
      "Diagnostic settings and destinations can support a cloud-side logging coverage claim for IoT Hub telemetry and operations.",
    evidenceLimitation:
      "It does not prove that logs are reviewed by a SOC, retained under an approved clinical investigation policy, or correlated with device-side telemetry.",
    expertReviewQuestion:
      "Is diagnostic setting coverage sufficient evidence for a cloud governance monitoring control, subject to separate operational review?",
  },
  "IOT-004": {
    controlId: "IOT-004",
    evidenceClass: "inferred_cloud",
    ncscCafObjectives: ["C1 security monitoring", "C2 proactive security event discovery"],
    nhsDsptOutcomes: [
      { outcomeId: "C1.a", name: "Monitoring coverage" },
      { outcomeId: "C2.a", name: "Proactive security event discovery" },
    ],
    cloudSupportedClaim:
      "Observable Defender for IoT, Defender for Cloud, or equivalent alert integration can support a cloud-side security monitoring evidence claim.",
    evidenceLimitation:
      "When licensing, permissions, or service availability prevent observation, the finding is an evidence gap rather than proof that compensating monitoring is absent.",
    expertReviewQuestion:
      "Is it defensible to report unavailable Defender/equivalent monitoring evidence as an observability gap rather than a definitive monitoring failure?",
  },
  "IOT-005": {
    controlId: "IOT-005",
    evidenceClass: "direct_cloud",
    ncscCafObjectives: ["B4 data security", "B5 resilient networks and systems"],
    nhsDsptOutcomes: [{ outcomeId: "B4.a", name: "Secure by design" }],
    cloudSupportedClaim:
      "IoT Hub public network access, firewall rules, allowed IP ranges, and private endpoint state can support a cloud boundary exposure claim.",
    evidenceLimitation:
      "It does not prove whether public connectivity is clinically justified, protected by external controls, or required for remote-care workflows.",
    expertReviewQuestion:
      "Is public IoT ingestion exposure a valid healthcare IoT risk signal when intentional-public and remote-care exceptions are handled by manual review?",
  },
  "IOT-006": {
    controlId: "IOT-006",
    evidenceClass: "direct_cloud",
    ncscCafObjectives: ["B5 resilient networks and systems"],
    nhsDsptOutcomes: [
      { outcomeId: "B4.a", name: "Secure by design" },
      { outcomeId: "B5.a", name: "Resilient networks and systems" },
    ],
    cloudSupportedClaim:
      "Private endpoint inventory and network isolation settings contribute candidate evidence toward sensitive telemetry path isolation, especially when public ingestion lacks compensating IP-filter or certificate evidence.",
    evidenceLimitation:
      "It does not prove end-to-end clinical network segmentation, gateway hardening, or whether public managed ingestion is an accepted design exception.",
    expertReviewQuestion:
      "For cloud-connected healthcare IoT, when should private endpoint absence be treated as a risk versus an accepted architecture decision?",
  },
  "IOT-007": {
    controlId: "IOT-007",
    evidenceClass: "inferred_cloud",
    ncscCafObjectives: ["B4 data security", "D1 response and recovery planning"],
    nhsDsptOutcomes: [{ outcomeId: "B4.b", name: "Secure data management" }],
    cloudSupportedClaim:
      "IoT Hub message routes and governed storage destinations contribute candidate evidence toward cloud-side telemetry routing and retention governance.",
    evidenceLimitation:
      "It does not prove lawful basis, clinical record status, retention-period adequacy, privacy impact assessment approval, or patient-data minimisation.",
    expertReviewQuestion:
      "Is telemetry routing to governed storage a useful assurance signal if privacy and clinical-record interpretation are kept outside cloud automation?",
  },
  "IOT-008": {
    controlId: "IOT-008",
    evidenceClass: "inferred_cloud",
    ncscCafObjectives: ["B2 identity and access control", "B3 secure configuration"],
    nhsDsptOutcomes: [
      { outcomeId: "B2.a", name: "Identity verification, authentication and authorisation" },
      { outcomeId: "B4.b", name: "Secure data management" },
    ],
    cloudSupportedClaim:
      "Key Vault and secret-management posture can support a cloud-side credential governance claim for IoT integrations.",
    evidenceLimitation:
      "It does not prove which applications consume each secret, whether rotation is operationally followed, or whether third-party supplier secrets are managed outside Azure.",
    expertReviewQuestion:
      "Is Key Vault/managed-secret posture a credible proxy for IoT integration credential governance when application usage remains manually validated?",
  },
  "IOT-009": {
    controlId: "IOT-009",
    evidenceClass: "direct_cloud",
    ncscCafObjectives: ["C1 security monitoring", "D2 lessons learned"],
    nhsDsptOutcomes: [
      { outcomeId: "C1.a", name: "Monitoring coverage" },
      { outcomeId: "D1.a", name: "Response plan" },
    ],
    cloudSupportedClaim:
      "Azure Monitor alert rules and action groups can support an operational alerting coverage claim for IoT Hub telemetry conditions.",
    evidenceLimitation:
      "It does not prove clinical escalation ownership, incident response quality, alert fatigue, or whether alerts are acted on by accountable responders.",
    expertReviewQuestion:
      "Is a deployed IoT-specific Azure Monitor alert a sufficient cloud-side signal for incident detection readiness, subject to clinical response validation?",
  },
  "IOT-010": {
    controlId: "IOT-010",
    evidenceClass: "clinical_operational_required",
    ncscCafObjectives: ["A1 governance", "A2 risk management"],
    nhsDsptOutcomes: [
      { outcomeId: "A2.a", name: "Risk management process" },
      { outcomeId: "D1.a", name: "Response plan" },
    ],
    cloudSupportedClaim:
      "Evidence class counts, unavailable signal counts, and report caveats can support an explicit assurance-boundary claim.",
    evidenceLimitation:
      "It does not replace clinical safety cases, medical-device safety review, biomedical engineering validation, or operational acceptance.",
    expertReviewQuestion:
      "Does the explicit boundary control make the paper more defensible by preventing cloud evidence from being misread as clinical or medical-device assurance?",
  },
};
