#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-project-5fbc8bf7-2dd6-4f0a-a5f}"
BUCKET_NAME="${BUCKET_NAME:-gcp-hospital-medallion-data}"
REGION="${REGION:-asia-south1}"
SOFT_DELETE_DAYS="${SOFT_DELETE_DAYS:-30}"

if gcloud storage buckets describe "gs://${BUCKET_NAME}" \
    --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "[FOUND] gs://${BUCKET_NAME}"
  echo "Use Terraform import + apply for an existing bucket."
  exit 0
fi

echo "[CREATE] gs://${BUCKET_NAME}"

gcloud storage buckets create \
  "gs://${BUCKET_NAME}" \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --default-storage-class=STANDARD \
  --uniform-bucket-level-access \
  --public-access-prevention=enforced \
  --soft-delete-duration="${SOFT_DELETE_DAYS}d"

echo "[PASS] Bucket created."
