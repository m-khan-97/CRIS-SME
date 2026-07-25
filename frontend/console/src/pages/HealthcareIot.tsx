import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, ShieldAlert } from "lucide-react";
import { useAssessmentReport } from "../context/AssessmentContext";
import type { PrioritizedRisk } from "../api/types";
import { EmptyState, Spinner } from "../components/ui";
import {
  DataTable,
  KpiCard,
  Meter,
  Panel,
  SeverityTag,
  normalizeSeverity,
  type DataTableColumn,
} from "../components/clarion";
import {
  IOMT_CONTROL_MAPPING,
  IOMT_EVIDENCE_CLASS_LABEL,
  type IomtEvidenceClass,
} from "../data/iomtControlMapping";

type IotFindingRow = PrioritizedRisk & { id: string };

const EVIDENCE_CLASS_ORDER: IomtEvidenceClass[] = [
  "direct_cloud",
  "inferred_cloud",
  "clinical_operational_required",
];

const EVIDENCE_CLASS_COLOR: Record<IomtEvidenceClass, string> = {
  direct_cloud: "var(--color-sev-low)",
  inferred_cloud: "var(--color-sev-medium)",
  clinical_operational_required: "var(--color-violet)",
};

const INVENTORY_FIELDS: { key: string; label: string }[] = [
  { key: "iot_hub_count", label: "IoT Hub / Thing Group count" },
  { key: "iot_device_identity_count", label: "Device identities" },
  { key: "iot_shared_access_policy_count", label: "Shared access policies" },
  { key: "iot_overbroad_shared_access_policy_count", label: "Overbroad policies" },
  { key: "iot_private_endpoint_count", label: "Private endpoints" },
  { key: "iot_alert_rule_count", label: "Alert rules" },
];

export function HealthcareIot() {
  const navigate = useNavigate();
  const { data: report, isLoading, error } = useAssessmentReport();

  const [selectedId, setSelectedId] = useState<string | null>(null);

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-8 text-text-muted">
        <Spinner /> Loading Healthcare IoT data…
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <EmptyState message={`Failed to load report: ${(error as Error).message}`} />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="p-8">
        <EmptyState message="No assessment report found yet." />
      </div>
    );
  }

  const domainScore = (report.category_scores as Record<string, number> | undefined)?.[
    "Healthcare IoT"
  ];
  const allRisks = report.prioritized_risks ?? [];
  const iotRisks = allRisks.filter((risk) => risk.control_id.startsWith("IOT-"));

  if (domainScore === undefined && iotRisks.length === 0) {
    return (
      <div className="flex flex-col gap-[18px] p-[24px_26px_28px]">
        <PageHeader />
        <EmptyState message="No Healthcare IoT / IoMT resources were detected in the latest assessment for this account. This page activates automatically once an IoT Hub (Azure) or IoT Core Thing Group (AWS) is present." />
      </div>
    );
  }

  const rows: IotFindingRow[] = iotRisks
    .slice()
    .sort((a, b) => b.score - a.score)
    .map((risk) => ({ ...risk, id: risk.finding_id }));
  const selected = rows.find((row) => row.id === selectedId) ?? rows[0];

  const criticalHighCount = iotRisks.filter((risk) =>
    ["critical", "high"].includes(risk.severity.toLowerCase())
  ).length;
  const evidenceSufficientCount = iotRisks.filter((risk) => {
    const sufficiency = (risk as Record<string, any>).evidence_sufficiency?.sufficiency;
    return typeof sufficiency === "string" && sufficiency !== "unsupported";
  }).length;

  const evidenceClassCounts: Record<IomtEvidenceClass, number> = {
    direct_cloud: 0,
    inferred_cloud: 0,
    clinical_operational_required: 0,
  };
  for (const risk of iotRisks) {
    const mapping = IOMT_CONTROL_MAPPING[risk.control_id];
    if (mapping) evidenceClassCounts[mapping.evidenceClass] += 1;
  }
  const evidenceClassTotal = iotRisks.length || 1;

  const organizations = (report as Record<string, any>).organizations as
    | Record<string, any>[]
    | undefined;
  const organization = organizations?.[0];
  const collectionDetails = organization?.collection_details as Record<string, any> | undefined;
  const inventoryEntries = collectionDetails
    ? INVENTORY_FIELDS.filter(
        (field) =>
          collectionDetails[field.key] !== undefined && collectionDetails[field.key] !== null
      )
    : [];
  const defenderEnabled = collectionDetails?.iot_defender_enabled;

  const columns: DataTableColumn<IotFindingRow>[] = [
    {
      key: "control",
      header: "Control",
      width: "78px",
      render: (row) => (
        <span className="font-mono text-[11px] font-semibold text-text-muted">{row.control_id}</span>
      ),
    },
    {
      key: "sev",
      header: "Sev",
      width: "60px",
      render: (row) => <SeverityTag level={normalizeSeverity(row.severity)} />,
    },
    {
      key: "finding",
      header: "Finding",
      render: (row) => (
        <span className="block truncate text-[12.5px] font-semibold text-text-strong">
          {row.title}
        </span>
      ),
    },
    {
      key: "score",
      header: "Score",
      align: "right",
      width: "50px",
      render: (row) => (
        <span className="text-[16px] font-extrabold text-text-strong">{Math.round(row.score)}</span>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-[18px] p-[24px_26px_28px]">
      <PageHeader />

      <div className="flex items-start gap-3 rounded-xl border border-sev-medium-border bg-sev-medium-bg p-[14px_16px]">
        <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-sev-medium-text" strokeWidth={1.8} />
        <p className="m-0 text-[12px] font-medium leading-[1.55] text-sev-medium-text">
          <b>Research preview — cloud governance only.</b> This assesses device-identity
          registration, access-policy hygiene, diagnostic/monitoring coverage, and network
          exposure for cloud-connected IoT/IoMT services. It does <b>not</b> assess device
          firmware, clinical safety, patient data handling, or medical-device certification —
          those require dedicated clinical and biomedical engineering review.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3.5 lg:grid-cols-4">
        <KpiCard
          label="IoMT domain risk score"
          value={domainScore !== undefined ? Math.round(domainScore) : "—"}
        />
        <KpiCard
          label="Open IoT findings"
          value={iotRisks.length}
          accent={iotRisks.length > 0 ? "high" : "good"}
        />
        <KpiCard
          label="Critical / High severity"
          value={criticalHighCount}
          accent={criticalHighCount > 0 ? "critical" : "good"}
        />
        <KpiCard label="Evidence sufficient" value={`${evidenceSufficientCount} / ${iotRisks.length}`} />
      </div>

      <Panel
        title="Evidence-sufficiency boundary"
        meta="How much of this readiness is hard cloud evidence vs inference vs human sign-off"
      >
        <div className="flex flex-col gap-3">
          {EVIDENCE_CLASS_ORDER.map((evidenceClass) => (
            <div key={evidenceClass} className="flex items-center gap-3">
              <span className="w-[190px] shrink-0 text-[12px] font-semibold text-text-body">
                {IOMT_EVIDENCE_CLASS_LABEL[evidenceClass]}
              </span>
              <div className="flex-1">
                <Meter
                  value={evidenceClassCounts[evidenceClass]}
                  max={evidenceClassTotal}
                  color={EVIDENCE_CLASS_COLOR[evidenceClass]}
                />
              </div>
              <span className="w-[24px] shrink-0 text-right text-[12px] font-bold text-text-strong">
                {evidenceClassCounts[evidenceClass]}
              </span>
            </div>
          ))}
        </div>
      </Panel>

      {inventoryEntries.length > 0 && (
        <Panel title="IoT inventory">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {inventoryEntries.map((field) => (
              <div key={field.key}>
                <div className="text-[10px] font-bold uppercase tracking-[.07em] text-text-muted">
                  {field.label}
                </div>
                <div className="mt-1 text-[18px] font-extrabold text-text-strong">
                  {String(collectionDetails?.[field.key])}
                </div>
              </div>
            ))}
            {typeof defenderEnabled === "boolean" && (
              <div>
                <div className="text-[10px] font-bold uppercase tracking-[.07em] text-text-muted">
                  Defender for IoT
                </div>
                <div
                  className={`mt-1 text-[18px] font-extrabold ${
                    defenderEnabled ? "text-status-good-text" : "text-sev-medium-text"
                  }`}
                >
                  {defenderEnabled ? "Enabled" : "Not observed"}
                </div>
              </div>
            )}
          </div>
        </Panel>
      )}

      <div className="grid grid-cols-1 gap-[18px] lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <DataTable
          columns={columns}
          rows={rows}
          selectedId={selected?.id}
          onRowClick={(row) => setSelectedId(row.id)}
        />
        <IotFindingDetail risk={selected} />
      </div>

      <button
        type="button"
        onClick={() => navigate("/findings?category=Healthcare%20IoT")}
        className="flex h-9 w-fit items-center gap-1.5 self-start rounded-md border border-border-strong bg-surface-card px-3.5 text-[12.5px] font-semibold text-text-body hover:bg-surface-subtle"
      >
        View all Healthcare IoT findings in Findings Workbench
        <ArrowRight className="h-3.5 w-3.5" strokeWidth={1.8} />
      </button>
    </div>
  );
}

function PageHeader() {
  return (
    <div>
      <h1 className="m-0 text-[15px] font-bold text-text-strong">Healthcare IoT</h1>
      <p className="m-0 mt-1 text-[11.5px] font-medium text-text-muted">
        Cloud governance assurance for connected medical devices · IoMT research preview
      </p>
    </div>
  );
}

function IotFindingDetail({ risk }: { risk: IotFindingRow | undefined }) {
  if (!risk) {
    return (
      <aside className="flex flex-col rounded-2xl border border-border-card bg-surface-card p-[20px_22px]">
        <EmptyState message="Select a control to see its detail." />
      </aside>
    );
  }

  const level = normalizeSeverity(risk.severity);
  const mapping = (risk as Record<string, any>).mapping as string[] | undefined;
  const sufficiency = (risk as Record<string, any>).evidence_sufficiency as
    | Record<string, any>
    | undefined;
  const research = IOMT_CONTROL_MAPPING[risk.control_id];

  return (
    <aside className="flex flex-col gap-4 rounded-2xl border border-border-card bg-surface-card p-[20px_22px]">
      <div className="flex items-center gap-2">
        <span className="font-mono text-[12px] font-semibold text-primary">{risk.control_id}</span>
        <SeverityTag level={level} />
        {research && (
          <span className="ml-auto rounded-[5px] bg-surface-rail px-[7px] py-[3px] text-[9.5px] font-bold text-text-muted">
            {IOMT_EVIDENCE_CLASS_LABEL[research.evidenceClass]}
          </span>
        )}
      </div>
      <h3 className="m-0 text-[18px] font-extrabold tracking-[-.01em] text-text-strong">
        {risk.title}
      </h3>

      {risk.evidence?.length > 0 && (
        <div>
          <SectionLabel>Evidence</SectionLabel>
          <div className="flex flex-col gap-[7px] border-l-2 border-primary-tint-border py-0.5 pl-3">
            {risk.evidence.map((item, index) => (
              <div key={index} className="text-[12px] font-medium leading-[1.5] text-text-body">
                {item}
              </div>
            ))}
          </div>
        </div>
      )}

      {sufficiency && (
        <div className="rounded-[10px] border border-sev-medium-border bg-sev-medium-bg p-[13px_14px]">
          <div className="mb-1 text-[10px] font-bold uppercase tracking-[.07em] text-sev-medium-text">
            Evidence-sufficiency boundary
          </div>
          {(sufficiency.missing_requirements ?? []).length > 0 && (
            <div className="mb-1.5 text-[12px] font-medium leading-[1.5] text-sev-medium-text">
              Not cloud-observable: {sufficiency.missing_requirements.join("; ")}
            </div>
          )}
          {(sufficiency.limitation_notes ?? []).map((note: string, index: number) => (
            <div key={index} className="text-[12px] font-medium leading-[1.5] text-sev-medium-text">
              {note}
            </div>
          ))}
        </div>
      )}

      {mapping && mapping.length > 0 && (
        <div>
          <SectionLabel>Compliance mapping</SectionLabel>
          <div className="flex flex-wrap gap-1.5">
            {mapping.map((item) => (
              <span
                key={item}
                className="rounded-full border border-border-strong bg-surface-subtle px-2 py-0.5 text-[11px] font-medium text-text-body"
              >
                {item}
              </span>
            ))}
          </div>
        </div>
      )}

      {risk.remediation_summary && (
        <div className="rounded-[10px] border border-border-divider bg-surface-subtle p-[13px_14px]">
          <div className="mb-1 text-[12.5px] font-semibold text-text-strong">
            {risk.remediation_summary}
          </div>
          {risk.remediation_cost_tier && (
            <div className="text-[12px] font-medium text-text-body">
              Estimated cost tier:{" "}
              <b className="text-status-good-text">{risk.remediation_cost_tier}</b>
            </div>
          )}
        </div>
      )}

      {research && (
        <div className="rounded-[10px] border border-primary-tint-border bg-primary-tint p-[13px_14px]">
          <div className="mb-1 text-[10px] font-bold uppercase tracking-[.07em] text-primary-on-tint">
            Open research question
          </div>
          <p className="m-0 text-[12px] font-medium italic leading-[1.5] text-primary-on-tint">
            “{research.expertReviewQuestion}”
          </p>
        </div>
      )}
    </aside>
  );
}

function SectionLabel({ children }: { children: string }) {
  return (
    <div className="mb-2 text-[10px] font-bold uppercase tracking-[.09em] text-text-muted">
      {children}
    </div>
  );
}
