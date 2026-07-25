#!/usr/bin/env bash
# CRIS-SME remediation reference pack
# Snippet kind: aws_cli
#
# These commands are reference-only and are not executed by CRIS-SME.
# Review each command, adapt placeholders (e.g. <resource-group>), and
# run it manually in your own change-controlled session.
set -euo pipefail

# DATA-001: Public storage access increases data exposure risk
# Review public S3 and RDS exposure
aws s3api list-buckets --query 'Buckets[].Name' --output table && aws rds describe-db-instances --query 'DBInstances[].{Id:DBInstanceIdentifier,Public:PubliclyAccessible}' --output table

# IAM-001: Privileged role assignments without MFA enforcement
# Review IAM users and MFA devices
aws iam list-users --output table

# MON-001: Activity log retention is below governance and investigation expectations
# Review CloudTrail and CloudWatch Logs retention
aws cloudtrail describe-trails --include-shadow-trails false --output table && aws logs describe-log-groups --query 'logGroups[].{Name:logGroupName,Retention:retentionInDays}' --output table

# NET-001: Administrative services are exposed to the public internet
# Review security-group ingress on administrative ports
aws ec2 describe-security-groups --query 'SecurityGroups[].{GroupId:GroupId,Ingress:IpPermissions}' --output json

