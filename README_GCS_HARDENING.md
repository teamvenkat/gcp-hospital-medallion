# Raw/GCS Hardening — Implementation

This package hardens the existing CSV → GCS Raw layer.

## Files

```text
terraform/
├── versions.tf
├── variables.tf
├── main.tf
├── outputs.tf
├── dev.tfvars.example
└── prod.tfvars.example

scripts/
├── create_raw_bucket.sh
├── import_existing_raw_bucket.sh
├── apply_raw_bucket.sh
└── validate_raw_bucket.sh

docs/
└── 10-gcs-storage-governance.md
```

## Current project

```text
Project: project-5fbc8bf7-2dd6-4f0a-a5f
Bucket : gcp-hospital-medallion-data
Region : asia-south1
```

## First-time setup

```bash
cd terraform
cp dev.tfvars.example dev.tfvars
terraform init
terraform validate
terraform plan -var-file=dev.tfvars
```

For the bucket that already exists:

```bash
cd ..
chmod +x scripts/*.sh
./scripts/import_existing_raw_bucket.sh
```

Then:

```bash
cd terraform
terraform plan -var-file=dev.tfvars
```

Review the plan carefully before applying.

Apply through the guarded script:

```bash
cd ..
./scripts/apply_raw_bucket.sh
```

Validate:

```bash
./scripts/validate_raw_bucket.sh
```

## Important

The existing development reset script deletes the development bucket. The Terraform configuration uses:

```text
force_destroy = false
```

on purpose.

We do not want `terraform destroy` or infrastructure changes to silently delete Raw objects.

The development reset remains an explicit destructive operation.

## Official references

- Google Cloud Storage overview: https://cloud.google.com/storage
- Uniform bucket-level access: https://docs.cloud.google.com/storage/docs/using-uniform-bucket-level-access
- Soft delete: https://docs.cloud.google.com/storage/docs/soft-delete
- Lifecycle management: https://docs.cloud.google.com/storage/docs/lifecycle
- Bucket creation: https://docs.cloud.google.com/storage/docs/creating-buckets
- Terraform GCS bucket resource: https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/storage_bucket
