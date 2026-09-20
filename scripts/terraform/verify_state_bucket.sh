#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-project-5fbc8bf7-2dd6-4f0a-a5f}"
BUCKET_NAME="${STATE_BUCKET_NAME:-gcp-hospital-medallion-tfstate}"

gcloud storage buckets describe "gs://${BUCKET_NAME}"   --project="${PROJECT_ID}"   --format="yaml(name,location,storageClass,publicAccessPrevention,uniformBucketLevelAccess,versioning,softDeletePolicy,lifecycle)"
