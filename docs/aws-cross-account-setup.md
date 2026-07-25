# AWS Cross-Account Scanning Setup

**Status: research preview.** Cross-account `sts:AssumeRole` support exists
in code and is unit-tested, but — like the rest of the AWS collector — has
not yet been verified against a real cross-account trust relationship.

This is for scanning a **different** AWS account than the one whose
credentials are configured on the machine running CRIS-SME, without setting
up local AWS CLI credentials for every target account. It's the same pattern
Wiz/Vanta/Prowler-as-a-service use to connect to customer accounts.

If you only ever scan the account whose credentials are already configured
locally (`aws configure`, SSO, env vars, instance role), you don't need any
of this — see [AWS Least-Privilege Setup](aws-least-privilege-setup.md)
instead.

## The model

- **Hub identity**: whatever AWS credentials are already configured on the
  machine running `local_runner` — unchanged from the direct-scanning setup.
- **Target account**: the account you want to scan. It creates a role that
  trusts the hub identity and is gated by a shared External ID. CRIS-SME's
  hub identity then calls `sts:AssumeRole` to get temporary credentials
  scoped to the target account — nothing is installed or configured in the
  target account beyond this one IAM role.

There is no central CRIS-SME-owned AWS account or fixed ARN to trust — the
"hub" is just whichever identity you've configured locally. For an MSP
scanning multiple client accounts, that's typically a dedicated IAM user or
role in your own security-tooling account.

## 1. Find your hub principal ARN

On the machine that will run `local_runner`:

```bash
aws sts get-caller-identity --query Arn --output text
```

Copy this ARN — the target account's trust policy needs it.

## 2. Generate an External ID

Click **Generate** next to the External ID field in the console's New
Assessment → AWS tab (or run `python3 -c "import secrets; print(secrets.token_urlsafe(24))"`).
Use a fresh, unpredictable value per target account — this is AWS's
documented mitigation for the
["confused deputy" problem](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-user_externalid.html)
with third-party cross-account roles. Don't reuse the same External ID across
multiple target accounts.

## 3. Create the trust role in the target account

Using the target account's own credentials (not the hub's):

```bash
HUB_PRINCIPAL_ARN="arn:aws:iam::<hub-account-id>:user/<hub-user>"   # from step 1
EXTERNAL_ID="<value from step 2>"

cat > /tmp/cris-sme-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "AWS": "${HUB_PRINCIPAL_ARN}" },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": { "sts:ExternalId": "${EXTERNAL_ID}" }
      }
    }
  ]
}
EOF

aws iam create-role \
  --role-name cris-sme-target \
  --assume-role-policy-document file:///tmp/cris-sme-trust-policy.json

aws iam put-role-policy \
  --role-name cris-sme-target \
  --policy-name cris-sme-assessment-reader \
  --policy-document file://infra/aws/iam-policies/cris-sme-assessment-reader.json
```

(Reuses the same read-only permission set documented in
[AWS Least-Privilege Setup](aws-least-privilege-setup.md) — no new
permissions are introduced for cross-account scanning.)

Note the resulting role ARN from the `create-role` output (or
`aws iam get-role --role-name cris-sme-target --query Role.Arn --output text`).

## 4. Confirm the hub identity can assume it

```bash
aws sts assume-role \
  --role-arn arn:aws:iam::<target-account-id>:role/cris-sme-target \
  --external-id "${EXTERNAL_ID}" \
  --role-session-name cris-sme-manual-check
```

If this fails, fix it here before going to the console — the trust policy's
`Principal` or `ExternalId` is the most common mismatch.

## 5. Run the scan

In the console's New Assessment → AWS tab, paste the Role ARN and External
ID into the "Cross-account scanning" section, click **Verify role** (calls
`POST /api/environment/aws/validate-role`, which assumes the role and reports
the resolved target account without starting a full assessment), then start
the assessment as normal. Leaving Role ARN blank falls back to direct
local-credential scanning, exactly as before.

## What CRIS-SME never does

- Never asks for or stores the target account's AWS credentials — only a
  Role ARN and an External ID, neither of which is a secret on their own.
- Never persists the role ARN/external ID anywhere — they're per-assessment
  form inputs (same as the existing Account ID / Subscription ID / Tenant ID
  fields), not saved across runs. There is no "connected accounts" list.
- Never assumes a role without the explicit authorization checkbox already
  required for every assessment.
