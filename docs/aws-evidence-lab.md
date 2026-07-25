# AWS Evidence Lab

The AWS Evidence Lab creates small, controlled AWS architectures for testing
CRIS-SME against live AWS control-plane evidence.

It mirrors the Azure Evidence Lab workflow, but uses AWS CLI and
CloudFormation.

## Safety Model

The default scenario is intentionally low cost:

- no EC2 instances are launched
- no IAM users or admin roles are created
- resources are tagged with `cris-sme-lab=true`
- cleanup deletes only the named CloudFormation stack
- deployment and cleanup require `--yes` unless `--dry-run` is used

The `public-exposure` scenario creates public SSH/RDP security-group rules and
an empty public S3 bucket so CRIS-SME can observe known risky AWS states. Use
only an AWS account you own or are explicitly authorised to test.

## Prerequisites

Configure AWS credentials for the account where the lab will be created:

```bash
aws configure --profile cris-sme-assessment
AWS_PROFILE=cris-sme-assessment aws sts get-caller-identity
```

The account/role needs enough permission to create and delete the lab stack:

- CloudFormation stack create/delete
- EC2 VPC, subnet, internet gateway, and security group resources
- S3 bucket and bucket policy resources

For CRIS-SME assessment after deployment, use the read-only collector policy in:

`infra/aws/iam-policies/cris-sme-assessment-reader.json`

## Commands

List scenarios:

```bash
AWS_PROFILE=cris-sme-assessment python3 scripts/aws_evidence_lab.py list
```

Preview without creating anything:

```bash
AWS_PROFILE=cris-sme-assessment python3 scripts/aws_evidence_lab.py deploy \
  --scenario public-exposure \
  --region us-east-1 \
  --run-id aws-day-001 \
  --dry-run
```

Deploy, assess, and cleanup:

```bash
AWS_PROFILE=cris-sme-assessment python3 scripts/aws_evidence_lab.py cycle \
  --scenario public-exposure \
  --region us-east-1 \
  --run-id aws-day-001 \
  --yes
```

Keep the lab after assessment for manual inspection:

```bash
AWS_PROFILE=cris-sme-assessment python3 scripts/aws_evidence_lab.py cycle \
  --scenario public-exposure \
  --region us-east-1 \
  --run-id aws-day-001 \
  --keep \
  --yes
```

Clean up a kept lab:

```bash
AWS_PROFILE=cris-sme-assessment python3 scripts/aws_evidence_lab.py cleanup \
  --scenario public-exposure \
  --region us-east-1 \
  --run-id aws-day-001 \
  --yes
```

## Output Location

Assessment outputs are archived under:

`outputs/aws-evidence-lab/{run_id}/{scenario}/reports/`

Each run includes:

- normal CRIS-SME report artifacts
- `lab_manifest.json`
- scenario metadata
- expected-finding notes

## Scenarios

- `sigi-full-spectrum`: production-shaped SIGI Technologies lab spanning
  network, S3, EC2, RDS, secrets, CloudTrail, CloudWatch, SSM automation,
  ECS, orphaned resources, and AWS IoT Core. It intentionally mixes protected
  and vulnerable states and should be kept only for short assessment windows.
- `public-exposure`: VPC, subnet, internet gateway, public SSH/RDP security
  group rules, and an empty public S3 bucket.
- `clean-baseline`: VPC, subnet, private-only security group, and private
  encrypted/versioned S3 bucket.

## Limitations

The AWS collector is still research preview. The lab validates control-plane
evidence collection mechanics; it is not a representative production AWS
estate. It also does not test endpoint, workload, or runtime telemetry.
