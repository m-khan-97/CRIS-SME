# Azure Least-Privilege Setup

This guide defines the Azure permissions needed for CRIS-SME live evidence collection without granting broad owner or contributor access.

The role artifact lives at:

`infra/azure/role-definitions/cris-sme-assessment-reader.json`

It covers Azure Resource Manager control-plane reads used by the current Azure collector and provider evidence contracts. Microsoft Graph permissions are separate because Azure custom RBAC roles cannot grant Graph API permissions.

## Azure RBAC Role

The custom role includes read actions for:

- role assignments and policy assignments
- network security groups, public IPs, network interfaces, and network exposure context
- storage accounts, SQL servers, Key Vaults, and IoT Hubs
- virtual machines and workload inventory
- diagnostic settings, activity log alerts, legacy activity-log profile retention, and budget evidence
- Microsoft Defender for Cloud pricing tier (scored across every plan the subscription has, not just VMs/SQL/CloudPosture) and native security assessment state
- Recovery Services vault and backup-protected-item state (VM backup coverage)
- metric alert rules (used for IoT Hub alert-coverage evidence)
- subscription resource inventory and Azure Policy compliance-state summary (non-compliant resource/policy counts, distinct from the policy-assignment-count signal)

Create the role for a subscription:

```bash
SUBSCRIPTION_ID="<subscription-id>"
ROLE_FILE="infra/azure/role-definitions/cris-sme-assessment-reader.json"
TMP_ROLE_FILE="/tmp/cris-sme-assessment-reader-${SUBSCRIPTION_ID}.json"

sed "s|<subscription-id>|${SUBSCRIPTION_ID}|g" "${ROLE_FILE}" > "${TMP_ROLE_FILE}"
az role definition create --role-definition "${TMP_ROLE_FILE}"
```

Assign it to the assessment identity:

```bash
SUBSCRIPTION_ID="<subscription-id>"
ASSIGNEE_OBJECT_ID="<user-or-service-principal-object-id>"

az role assignment create \
  --assignee-object-id "${ASSIGNEE_OBJECT_ID}" \
  --assignee-principal-type ServicePrincipal \
  --role "CRIS-SME Assessment Reader" \
  --scope "/subscriptions/${SUBSCRIPTION_ID}"
```

For a user identity, change `--assignee-principal-type` to `User`.

## Microsoft Graph Permissions

CRIS-SME can run with only Azure RBAC evidence, but IAM assurance is stronger when tenant Graph evidence is visible.

Recommended Graph application or delegated permissions:

- `Directory.Read.All`: directory role and principal context
- `Policy.Read.All`: Conditional Access policy visibility
- `Reports.Read.All`: MFA registration report visibility
- `AccessReview.Read.All`: identity governance access review freshness visibility
- `RoleManagement.Read.Directory`: PIM-eligible (time-bound) role assignment visibility, distinct from standing role assignments visible via RBAC alone

If these are unavailable, CRIS-SME records the observability boundary instead of assuming compliance. This is expected for least-privilege SME assessments where tenant-wide identity evidence is not always granted.

## Azure CLI Prerequisites

The local runner uses the authenticated Azure CLI context:

```bash
az account show
az account set --subscription "<subscription-id>"
```

IoT Hub evidence uses Azure CLI IoT commands when IoT controls are in scope. Install the extension if needed:

```bash
az extension add --name azure-iot
```

## Contract Alignment

This setup artifact is tested against the active Azure provider evidence contracts:

- every active or research-preview Azure ARM permission declared by the contracts must appear in the custom role
- Microsoft Graph permissions must remain documented separately
- optional ARM evidence such as budget reads is included in the role to avoid unnecessary governance evidence gaps

Do not mark AWS or GCP provider contracts as active by copying this role. Their contracts remain planned until provider-specific collectors, tests, docs, and least-privilege setup artifacts exist.
