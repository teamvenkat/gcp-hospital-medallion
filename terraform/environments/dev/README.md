# Development Terraform Root

This directory is the **DEV root module** for the main infrastructure.

It uses the remote GCS Terraform backend created by `terraform/bootstrap`.

## Backend

```text
gs://gcp-hospital-medallion-tfstate
  └── terraform/state/dev
```

Do not use Terraform CLI workspaces to represent DEV/TEST/PROD. Each environment has its own root directory and backend prefix.

## Phase 0

The root is intentionally empty of application resources.

The first successful initialization proves:

```text
bootstrap state bucket
        ↓
remote backend
        ↓
DEV root
```

Application infrastructure will be added in controlled phases.
