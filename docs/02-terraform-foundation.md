# Terraform Foundation

## Objective

Establish Terraform as the infrastructure-as-code control plane **before application infrastructure is created**.

## Architecture

```text
GCP project
    │
    ▼
Terraform bootstrap
    │
    └── dedicated GCS state bucket
            │
            ▼
      remote Terraform state
            │
            ▼
       environment root
            │
            ├── DEV
            ├── TEST
            └── PROD
```

## Why bootstrap exists

The GCS Terraform backend requires its bucket to exist before the backend can be initialized. The bootstrap therefore uses temporary local state only to create the dedicated state bucket.

HashiCorp's GCS backend supports state locking and recommends Object Versioning for state recovery.

## State bucket

The state bucket is separate from application data:

```text
gcp-hospital-medallion-tfstate
        ≠
gcp-hospital-medallion-data
```

The state bucket is configured with:

- STANDARD storage
- uniform bucket-level access
- public access prevention
- Object Versioning
- soft delete
- `force_destroy = false`
- lifecycle cleanup for old state object versions

## Environment roots

Each environment gets its own Terraform root:

```text
terraform/environments/dev
terraform/environments/test
terraform/environments/prod
```

Each root has its own backend prefix.

We intentionally do not use CLI workspaces as the primary environment separation mechanism.

## Local authentication

For local development:

```bash
gcloud auth application-default login
```

Do not download service-account JSON keys for local Terraform execution.

## Standard workflow

```text
terraform fmt
      ↓
terraform validate
      ↓
terraform plan -out=<plan>
      ↓
review
      ↓
terraform apply <plan>
```

The plan is reviewed before apply.

## Bootstrap workflow

```bash
cd terraform/bootstrap
cp terraform.tfvars.example terraform.tfvars

terraform init
terraform fmt -check
terraform validate
terraform plan -var-file=terraform.tfvars -out=bootstrap.tfplan
terraform apply bootstrap.tfplan
```

Then initialize DEV:

```bash
./scripts/terraform/init_dev.sh
```

The DEV root should now use:

```text
gs://gcp-hospital-medallion-tfstate
  prefix = terraform/state/dev
```

## Security rules

Never commit:

```text
terraform.tfvars
*.tfstate
*.tfstate.*
*.tfplan
```

Never put credentials or service-account private keys in Terraform configuration.

## What comes next

After this foundation is proven, the next infrastructure stage will add:

1. Raw GCS module
2. BigQuery datasets
3. service accounts
4. IAM

The application ingestion code comes after the infrastructure baseline.

## References

- Terraform GCS backend: https://developer.hashicorp.com/terraform/language/backend/gcs
- Google Cloud Terraform security: https://docs.cloud.google.com/docs/terraform/best-practices/security
- Google Cloud Terraform operations: https://docs.cloud.google.com/docs/terraform/best-practices/operations
- Google Cloud Terraform root modules: https://docs.cloud.google.com/docs/terraform/best-practices/root-modules
