# GCS Raw Storage Governance

## Scope

This document covers the infrastructure hardening of:

```text
gs://gcp-hospital-medallion-data
```

for the CSV → Raw layer.

The source remains **CSV only**. No Pub/Sub, CDC, API, or other source technology is introduced here.

## Target configuration

```text
GCS Raw
│
├── STANDARD
├── Uniform bucket-level access
├── Public access prevention
├── Soft delete
├── Retention policy
├── Lifecycle transitions
├── IAM
└── Terraform-managed configuration
```

## Why these controls exist

### Uniform bucket-level access

IAM becomes the access-control mechanism and object ACLs are disabled.

### Public access prevention

Raw hospital data must not become publicly accessible.

### Soft delete

Protects against accidental or malicious deletion. Current Google Cloud documentation says newly created buckets have a default seven-day soft-delete duration and allow customization from 7 to 90 days.

### Retention

A retention policy prevents deletion before the configured minimum retention period. This is separate from soft delete.

### Lifecycle

Lifecycle rules automate storage-class transitions and, if we later choose, deletion. The initial design uses lifecycle for storage optimization rather than automatic Raw deletion.

## Current proposed policy

Development:

```text
STANDARD
Soft delete: 30 days
Retention: disabled by default for dev reset compatibility
30 days → NEARLINE
90 days → COLDLINE
365 days in COLDLINE → ARCHIVE
No automatic deletion
```

Production:

```text
STANDARD
Soft delete: 30 days
Retention: 30 days initially
30 days → NEARLINE
90 days → COLDLINE
365 days in COLDLINE → ARCHIVE
Deletion: separate approved retention decision
```

These are platform defaults, not regulatory retention requirements. Hospital/legal retention requirements must be established separately before production.

## Important distinction

Local lifecycle:

```text
incoming/
processed/
skipped/
failed/
non_processed/
```

is application workflow state.

GCS lifecycle:

```text
STANDARD
  ↓
NEARLINE
  ↓
COLDLINE
  ↓
ARCHIVE
```

is storage management.

Control tables remain the source of operational processing state.

## Existing bucket

For the current bucket, do not recreate it blindly.

Use:

```bash
./scripts/import_existing_raw_bucket.sh
```

Then:

```bash
cd terraform
cp dev.tfvars.example dev.tfvars
terraform plan -var-file=dev.tfvars
```

Review the plan before applying.

## Reproducibility

A new environment can use:

```text
Terraform variables
       ↓
terraform init
       ↓
terraform plan
       ↓
terraform apply
       ↓
validation script
```

## Verification

```bash
./scripts/validate_raw_bucket.sh
```

Verify:

- bucket location
- STANDARD default storage class
- uniform bucket-level access
- public access prevention
- soft delete
- retention policy
- lifecycle rules
- IAM bindings

## Future security

The initial implementation uses Google-managed encryption.

CMEK with Cloud KMS can be introduced when the project establishes a requirement for customer-managed keys.

## Future IAM

Application service accounts should eventually use least-privilege roles:

```text
Raw ingestion service account
    → write/create to Raw

Bronze service account
    → read Raw

Human developer
    → controlled operational access
```

Avoid using broad project-level administrator roles for runtime workloads.

## What this stage does not cover

This document intentionally does not introduce:

- streaming ingestion
- Pub/Sub
- CDC
- SFTP
- APIs
- HL7/FHIR
- Bronze processing

Those belong outside the current CSV source scope or in later layers.
