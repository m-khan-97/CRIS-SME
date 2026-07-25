import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { FlaskConical } from "lucide-react";
import {
  getAssessmentRun,
  getAwsEnvironment,
  getAzureEnvironment,
  startAwsAssessment,
  startAzureAssessment,
  validateAwsRole,
} from "../api/client";
import { Card, EmptyState, Spinner, StatusBadge } from "../components/ui";
import { useAssessment } from "../context/AssessmentContext";

const IS_DEMO = import.meta.env.VITE_DEMO_MODE === "true";

type Provider = "azure" | "aws";

export function NewAssessment() {
  return IS_DEMO ? <NewAssessmentDemoNotice /> : <NewAssessmentLive />;
}

function NewAssessmentDemoNotice() {
  return (
    <div className="flex flex-col gap-6 p-[24px_26px_28px]">
      <div>
        <h1 className="text-2xl font-semibold text-text-strong">New Assessment</h1>
        <p className="mt-1 text-sm text-text-muted">
          Run a live CRIS-SME assessment against an authorised Azure or AWS environment.
        </p>
      </div>
      <div className="flex max-w-xl flex-col gap-4 rounded-2xl border border-amber-400/30 bg-amber-400/[0.07] p-8">
        <div className="flex items-center gap-3">
          <FlaskConical className="h-6 w-6 text-amber-500" strokeWidth={1.6} />
          <span className="text-[15px] font-bold text-text-strong">Demo mode — live assessments disabled</span>
        </div>
        <p className="text-[13.5px] leading-relaxed text-text-body">
          This hosted demo runs against a pre-loaded anonymised dataset for <b>Contoso Healthcare Ltd</b>.
          All dashboards, findings, IoT controls, attack paths, and compliance mappings you see are real
          CRIS-SME output — just against a sanitised environment rather than your own cloud account.
        </p>
        <p className="text-[13.5px] leading-relaxed text-text-body">
          To run a live assessment against your own Azure or AWS subscription, contact Aureon Systems Ltd
          for an evaluation licence — your data never leaves your own infrastructure.
        </p>
        <a
          href={import.meta.env.VITE_CONTACT_URL ?? "#contact"}
          className="mt-2 inline-flex w-fit items-center gap-2 rounded-md bg-primary px-4 py-2 text-[13px] font-bold text-white shadow-primary transition-colors hover:bg-primary-hover"
        >
          Request a live trial →
        </a>
      </div>
    </div>
  );
}

function NewAssessmentLive() {
  const queryClient = useQueryClient();
  const { setSelectedReportId } = useAssessment();
  const [provider, setProvider] = useState<Provider>("azure");
  const [runId, setRunId] = useState<string | null>(null);
  const [authorizationConfirmed, setAuthorizationConfirmed] = useState(false);
  const [organizationName, setOrganizationName] = useState("");
  const [subscriptionId, setSubscriptionId] = useState("");
  const [tenantId, setTenantId] = useState("");
  const [accountId, setAccountId] = useState("");
  const [roleArn, setRoleArn] = useState("");
  const [externalId, setExternalId] = useState("");

  const azureEnvironment = useQuery({
    queryKey: ["azure-environment"],
    queryFn: getAzureEnvironment,
    enabled: provider === "azure",
  });

  const awsEnvironment = useQuery({
    queryKey: ["aws-environment"],
    queryFn: getAwsEnvironment,
    enabled: provider === "aws",
  });

  const run = useQuery({
    queryKey: ["assessment-run", runId],
    queryFn: () => getAssessmentRun(runId!),
    enabled: !!runId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed") {
        return false;
      }
      return 1_500;
    },
  });

  useEffect(() => {
    if (run.data?.status !== "completed") return;
    setSelectedReportId(run.data.run_id);
    void queryClient.invalidateQueries({ queryKey: ["assessment-history"] });
  }, [queryClient, run.data?.run_id, run.data?.status, setSelectedReportId]);

  const startAzure = useMutation({
    mutationFn: startAzureAssessment,
    onSuccess: (data) => {
      setRunId(data.run_id);
      queryClient.invalidateQueries({ queryKey: ["assessment-run", data.run_id] });
    },
  });

  const startAws = useMutation({
    mutationFn: startAwsAssessment,
    onSuccess: (data) => {
      setRunId(data.run_id);
      queryClient.invalidateQueries({ queryKey: ["assessment-run", data.run_id] });
    },
  });

  const verifyRole = useMutation({
    mutationFn: validateAwsRole,
  });

  const startAssessment = provider === "azure" ? startAzure : startAws;

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (provider === "azure") {
      startAzure.mutate({
        authorization_confirmed: authorizationConfirmed,
        organization_name: organizationName.trim(),
        subscription_id: subscriptionId || undefined,
        tenant_id: tenantId || undefined,
      });
    } else {
      startAws.mutate({
        authorization_confirmed: authorizationConfirmed,
        organization_name: organizationName.trim(),
        account_id: accountId || undefined,
        role_arn: roleArn || undefined,
        external_id: externalId || undefined,
      });
    }
  };

  const generateExternalId = () => {
    setExternalId(crypto.randomUUID());
  };

  const switchProvider = (next: Provider) => {
    setProvider(next);
    setAuthorizationConfirmed(false);
  };

  return (
    <div className="flex flex-col gap-6 p-[24px_26px_28px]">
      <div>
        <h1 className="text-2xl font-semibold text-text-strong">New Assessment</h1>
        <p className="mt-1 text-sm text-text-muted">
          Run a live CRIS-SME assessment against an authorized Azure subscription or
          AWS account.
        </p>
      </div>

      <div className="flex w-fit rounded-md border border-border-strong bg-surface-subtle p-1">
        {(["azure", "aws"] as Provider[]).map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => switchProvider(option)}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
              provider === option
                ? "bg-primary text-white"
                : "text-text-muted hover:text-text-strong"
            }`}
          >
            {option === "azure" ? "Azure" : "AWS"}
          </button>
        ))}
      </div>

      {provider === "aws" && (
        <p className="text-xs text-sev-medium-text">
          AWS collection is a research preview: it has not yet been verified
          against a live AWS account.
        </p>
      )}

      {provider === "azure" ? (
        <Card title="Azure CLI environment">
          {azureEnvironment.isLoading && (
            <div className="flex items-center gap-2 text-text-muted">
              <Spinner /> Checking Azure CLI session…
            </div>
          )}
          {azureEnvironment.data && (
            <div className="flex items-center justify-between">
              <div>
                <StatusBadge
                  status={azureEnvironment.data.authenticated ? "completed" : "failed"}
                />
                <span className="ml-2 text-sm text-text-body">
                  {azureEnvironment.data.message}
                </span>
              </div>
              {azureEnvironment.data.account && (
                <div className="text-right text-xs text-text-muted">
                  <div>{azureEnvironment.data.account.subscription_name}</div>
                  <div>{azureEnvironment.data.account.subscription_id}</div>
                </div>
              )}
            </div>
          )}
        </Card>
      ) : (
        <Card title="AWS credentials">
          {awsEnvironment.isLoading && (
            <div className="flex items-center gap-2 text-text-muted">
              <Spinner /> Checking AWS credential chain…
            </div>
          )}
          {awsEnvironment.data && (
            <div className="flex items-center justify-between">
              <div>
                <StatusBadge
                  status={awsEnvironment.data.authenticated ? "completed" : "failed"}
                />
                <span className="ml-2 text-sm text-text-body">
                  {awsEnvironment.data.message}
                </span>
              </div>
              {awsEnvironment.data.account && (
                <div className="text-right text-xs text-text-muted">
                  <div>{awsEnvironment.data.account.account_id}</div>
                  <div className="max-w-xs truncate">{awsEnvironment.data.account.arn}</div>
                </div>
              )}
            </div>
          )}
        </Card>
      )}

      <Card title="Run configuration">
        <form className="flex flex-col gap-4" onSubmit={onSubmit}>
          <label className="flex max-w-xl flex-col gap-1 text-sm text-text-body">
            Organization name
            <input
              required
              className="rounded-md border border-border-strong bg-surface-card px-3 py-2 text-sm text-text-strong focus:border-primary focus:outline-none"
              value={organizationName}
              onChange={(event) => setOrganizationName(event.target.value)}
              placeholder="e.g. SIGI Technologies"
            />
            <span className="text-xs text-text-muted">
              Used to label this assessment, its history, and exported reports.
            </span>
          </label>
          {provider === "azure" ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <label className="flex flex-col gap-1 text-sm text-text-body">
                Subscription ID (optional)
                <input
                  className="rounded-md border border-border-strong bg-surface-card px-3 py-2 text-sm text-text-strong focus:border-primary focus:outline-none"
                  value={subscriptionId}
                  onChange={(event) => setSubscriptionId(event.target.value)}
                  placeholder={azureEnvironment.data?.account?.subscription_id ?? "auto-detected"}
                />
              </label>
              <label className="flex flex-col gap-1 text-sm text-text-body">
                Tenant ID (optional)
                <input
                  className="rounded-md border border-border-strong bg-surface-card px-3 py-2 text-sm text-text-strong focus:border-primary focus:outline-none"
                  value={tenantId}
                  onChange={(event) => setTenantId(event.target.value)}
                  placeholder={azureEnvironment.data?.account?.tenant_id ?? "auto-detected"}
                />
              </label>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <label className="flex flex-col gap-1 text-sm text-text-body">
                  Account ID (optional)
                  <input
                    className="rounded-md border border-border-strong bg-surface-card px-3 py-2 text-sm text-text-strong focus:border-primary focus:outline-none"
                    value={accountId}
                    onChange={(event) => setAccountId(event.target.value)}
                    placeholder={awsEnvironment.data?.account?.account_id ?? "auto-detected"}
                  />
                </label>
              </div>

              <div className="rounded-md border border-border-card bg-surface-subtle p-3">
                <p className="mb-3 text-xs text-text-muted">
                  Cross-account scanning (optional): leave blank to scan the
                  account behind whatever AWS credentials are configured on
                  this machine. Fill in a Role ARN to instead assume a role
                  into a different target account — see{" "}
                  <code className="text-text-body">docs/aws-cross-account-setup.md</code>.
                </p>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                  <label className="flex flex-col gap-1 text-sm text-text-body">
                    Role ARN
                    <input
                      className="rounded-md border border-border-strong bg-surface-card px-3 py-2 text-sm text-text-strong focus:border-primary focus:outline-none"
                      value={roleArn}
                      onChange={(event) => setRoleArn(event.target.value)}
                      placeholder="arn:aws:iam::123456789012:role/cris-sme-target"
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-sm text-text-body">
                    External ID
                    <div className="flex gap-2">
                      <input
                        className="flex-1 rounded-md border border-border-strong bg-surface-card px-3 py-2 text-sm text-text-strong focus:border-primary focus:outline-none"
                        value={externalId}
                        onChange={(event) => setExternalId(event.target.value)}
                        placeholder="shared secret used in the role's trust policy"
                      />
                      <button
                        type="button"
                        onClick={generateExternalId}
                        className="shrink-0 rounded-md border border-border-strong px-3 py-2 text-xs text-text-body hover:bg-surface-subtle"
                      >
                        Generate
                      </button>
                    </div>
                  </label>
                </div>

                <div className="mt-3 flex items-center gap-3">
                  <button
                    type="button"
                    disabled={!roleArn || verifyRole.isPending}
                    onClick={() => verifyRole.mutate({ role_arn: roleArn, external_id: externalId || undefined })}
                    className="rounded-md border border-border-strong px-3 py-1.5 text-xs font-medium text-text-strong transition-colors hover:bg-surface-subtle disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {verifyRole.isPending ? "Verifying…" : "Verify role"}
                  </button>
                  {verifyRole.data && (
                    <div className="flex items-center gap-2 text-xs">
                      <StatusBadge status={verifyRole.data.verified ? "completed" : "failed"} />
                      <span className={verifyRole.data.verified ? "text-status-good-text" : "text-sev-critical-text"}>
                        {verifyRole.data.verified
                          ? `Verified — target account ${verifyRole.data.account_id}`
                          : verifyRole.data.message}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          <label className="flex items-center gap-2 text-sm text-text-body">
            <input
              type="checkbox"
              checked={authorizationConfirmed}
              onChange={(event) => setAuthorizationConfirmed(event.target.checked)}
              className="h-4 w-4 rounded border-border-strong bg-surface-card text-primary"
            />
            I confirm I am authorized to run a CRIS-SME assessment against this{" "}
            {provider === "azure" ? "Azure tenant/subscription" : "AWS account"}.
          </label>

          {startAssessment.isError && (
            <p className="text-sm text-sev-critical-text">
              {(startAssessment.error as Error).message}
            </p>
          )}

          <button
            type="submit"
            disabled={!authorizationConfirmed || !organizationName.trim() || startAssessment.isPending}
            className="w-fit rounded-md bg-primary px-4 py-2 text-sm font-medium text-text-strong transition-colors hover:bg-primary-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {startAssessment.isPending ? "Starting…" : "Start assessment"}
          </button>
        </form>
      </Card>

      {runId && (
        <Card title="Run progress">
          {run.isLoading && (
            <div className="flex items-center gap-2 text-text-muted">
              <Spinner /> Loading run status…
            </div>
          )}
          {run.data && (
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-3">
                <StatusBadge status={run.data.status} />
                <span className="text-sm text-text-body">
                  Run {run.data.run_id}
                </span>
              </div>

              {run.data.error && (
                <p className="text-sm text-sev-critical-text">{run.data.error}</p>
              )}

              <RunnerTimeline events={run.data.runner_events} />

              {run.data.status === "completed" && (
                <p className="text-sm text-status-good-text">
                  Assessment complete. Visit Overview, Findings, and Resources to
                  explore the new report.
                </p>
              )}
            </div>
          )}
        </Card>
      )}
    </div>
  );
}

function RunnerTimeline({
  events,
}: {
  events: { sequence: number; phase: string; status: string; message: string }[];
}) {
  if (!events.length) {
    return (
      <EmptyState message="Waiting for the assessment runner to emit progress events…" />
    );
  }

  const completedPhases = new Set(
    events.filter((event) => event.status === "completed").map((event) => event.phase)
  );

  const phases = [...new Set(events.map((event) => event.phase))];

  return (
    <ol className="flex flex-col gap-2">
      {phases.map((phase) => {
        const isComplete = completedPhases.has(phase);
        const latest = events.filter((event) => event.phase === phase).at(-1);
        return (
          <li key={phase} className="flex items-center gap-3 text-sm">
            <span
              className={`flex h-5 w-5 items-center justify-center rounded-full border text-[10px] ${
                isComplete
                  ? "border-status-good-border bg-status-good-bg text-status-good-text"
                  : "border-sev-low-border bg-sev-low-bg text-sev-low-text animate-pulse"
              }`}
            >
              {isComplete ? "✓" : "•"}
            </span>
            <span className="font-medium text-text-strong">
              {phase.replaceAll("_", " ")}
            </span>
            <span className="text-text-muted">{latest?.message}</span>
          </li>
        );
      })}
    </ol>
  );
}
