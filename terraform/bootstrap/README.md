# Terraform Bootstrap

This configuration creates the **separate GCS bucket used for Terraform remote state**.

It is intentionally a bootstrap configuration because the GCS backend bucket must exist before the main Terraform configuration can use it.

## What it creates

- Cloud Storage API enablement
- Dedicated Terraform state bucket
- Uniform bucket-level access
- Public access prevention
- Object Versioning
- 30-day soft delete
- State-object lifecycle cleanup
- `force_destroy = false`

## State model

Bootstrap uses local Terraform state temporarily.

After the state bucket exists, the main environment configurations use the GCS backend.

Do not use this directory to manage application infrastructure.

## Run

```bash
gcloud auth application-default login

cd terraform/bootstrap
cp terraform.tfvars.example terraform.tfvars

terraform init
terraform fmt -check
terraform validate
terraform plan -var-file=terraform.tfvars -out=bootstrap.tfplan
terraform apply bootstrap.tfplan
```

After successful apply, verify:

```bash
gcloud storage buckets describe gs://gcp-hospital-medallion-tfstate
```

The bucket must be private and must have Object Versioning enabled.

## Important

Do not put secrets in `terraform.tfvars`.

Do not commit:

- `terraform.tfvars`
- `*.tfstate`
- `*.tfstate.*`
- `*.tfplan`
