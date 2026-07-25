# AWS Least-Privilege Setup

This guide defines the AWS permissions needed for CRIS-SME's AWS collector without granting broad administrator access.

**Status: research preview.** The AWS collector (`AwsCollector`) issues real boto3 calls and has been unit-tested against fake clients, but has not yet been verified against a live AWS account. Do not mark AWS provider contracts as `active` by attaching this policy alone — that requires a verified live run in addition to the artifacts below.

The policy artifact lives at:

`infra/aws/iam-policies/cris-sme-assessment-reader.json`

It covers every read-only API call the AWS collector makes, grouped by domain. There is no AWS analog to Azure's RBAC/Graph split — all permissions are plain IAM actions on a single policy document.

## IAM Policy

The policy includes read/list/describe/get actions for:

- IAM users, roles, attached and inline policies, group memberships and group-attached policies, MFA devices, access keys, password policy, and account summary; STS caller identity; IAM Access Analyzer
- EC2 security groups, VPC endpoints, region enumeration, and internet-facing load balancer (ALB/NLB/CLB) and listener inventory
- S3 bucket inventory, bucket location (for region-correct per-bucket calls), public-access status, ACLs, Block Public Access configuration, encryption, versioning, and tagging; RDS instance inventory; KMS keys; Secrets Manager
- CloudTrail trails and logging status, CloudWatch Logs retention, CloudWatch alarms, GuardDuty detectors and active findings, Security Hub standards and active findings, SSM documents
- EC2 instance inventory, SSM managed-instance and patch-compliance state, AWS Backup protected resources, Lambda function inventory, Function URL auth configuration, and resource-policy visibility, ECS cluster/service inventory, EKS cluster inventory and public-endpoint configuration
- Resource Groups Tagging API, unattached EBS volumes, unassociated Elastic IPs, AWS Config recorder status, and AWS Config rule-compliance summary
- AWS Budgets and AWS Organizations service control policies (optional — see below)
- AWS IoT Core things, thing groups, certificates, policies, topic rules, and security profiles

Create the policy and attach it to the assessment identity:

```bash
aws iam create-policy \
  --policy-name CRIS-SME-Assessment-Reader \
  --policy-document file://infra/aws/iam-policies/cris-sme-assessment-reader.json

aws iam attach-user-policy \
  --user-name <assessment-user> \
  --policy-arn arn:aws:iam::<account-id>:policy/CRIS-SME-Assessment-Reader
```

For a role-based identity (e.g. an EC2 instance role or a role assumed via SSO), use `attach-role-policy` instead.

To scan an AWS account *other than* the one these credentials belong to — without configuring local AWS CLI credentials for every target account — see [AWS Cross-Account Scanning Setup](aws-cross-account-setup.md), which reuses this same policy document as the permission set attached to the cross-account role.

## Optional Permissions

`budgets:ViewBudget` and `organizations:ListPolicies` are optional. AWS Budgets requires explicit billing-console access, and `organizations:ListPolicies` only resolves for accounts that are part of an AWS Organization with visibility into service control policies. If these are unavailable, CRIS-SME records `budget_evidence_state: "unavailable"` and a zero service-control-policy count instead of assuming compliance — consistent with the evidence-honesty boundary used throughout CRIS-SME.

## Credential Setup

CRIS-SME does not use the AWS CLI for collection — it uses boto3's standard credential chain. Configure credentials with any of:

```bash
aws configure --profile cris-sme-assessment   # writes ~/.aws/credentials
# or
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1
```

CRIS-SME never asks for or persists these credentials itself; the local runner's `/api/environment/aws` check calls `sts.get_caller_identity()` against whatever credential chain is already configured on the host.

## Region Scope

Unlike Azure's subscription-wide control plane, most AWS resource APIs are regional. By default the collector enumerates all opted-in regions via `ec2:DescribeRegions`. Set `CRIS_SME_AWS_REGIONS` (comma-separated, e.g. `us-east-1,eu-west-2`) to restrict collection to specific regions and reduce assessment time.

## Known Limitations

- AWS has no Conditional Access equivalent; admin-MFA enforcement is approximated from the account password policy and `AccountMFAEnabled`.
- AWS has no Key Vault equivalent; "key vault" posture is approximated from KMS key state and Secrets Manager rotation.
- AWS IoT Core has no "hub" resource; IoT posture is approximated from Thing Groups and Things, and is the weakest cross-provider analog of the seven collected domains.
- `linux_password_auth_enabled_vms` is not observable from the EC2 API and is always reported as `0`.

## Contract Alignment

This setup artifact is tested (`tests/test_aws_least_privilege_setup.py`) against the AWS provider evidence contracts: every required or optional AWS permission declared by a `research_preview` (or higher) contract must appear in the policy document.
