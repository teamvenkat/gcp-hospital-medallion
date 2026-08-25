# Architecture

Detailed architecture for the GCP Hospital Medallion platform.

## Layers

```text
Sources → Raw → Bronze → Silver → Gold → Looker Studio
```

## Supporting services

```text
Cloud Composer → orchestration
BigQuery → warehouse/control
GCS → raw object storage
Dataproc/PySpark → processing
Terraform → infrastructure
Jenkins → CI
Harness → CD
Saviynt/IAM → access governance
```

See the root README for the target architecture and build order.
