# Infrastructure / Terraform / Governance

## Terraform targets

```text
GCS
BigQuery
IAM
service accounts
Composer
Dataproc
```

## Target flow

```text
Terraform
   ↓
GCP infrastructure
```

## IAM

Use least privilege and service-account based workloads.

## Governance

Saviynt is planned for enterprise IAM/governance integration later.

Infrastructure automation should be introduced after the data layers are working.
