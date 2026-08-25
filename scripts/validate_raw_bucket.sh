#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-project-5fbc8bf7-2dd6-4f0a-a5f}"
BUCKET_NAME="${BUCKET_NAME:-gcp-hospital-medallion-data}"

echo "======================================"
echo "GCS RAW BUCKET VALIDATION"
echo "======================================"
echo "Project : ${PROJECT_ID}"
echo "Bucket  : gs://${BUCKET_NAME}"
echo

gcloud storage buckets describe "gs://${BUCKET_NAME}" \
  --project="${PROJECT_ID}" \
  --format="yaml(
    name,
    location,
    storageClass,
    publicAccessPrevention,
    uniformBucketLevelAccess,
    softDeletePolicy,
    retentionPolicy,
    lifecycle
  )"

echo
echo "======================================"
echo "IAM POLICY"
echo "======================================"

gcloud storage buckets get-iam-policy \
  "gs://${BUCKET_NAME}" \
  --format="yaml(bindings)"

echo
echo "======================================"
echo "RAW PREFIX"
echo "======================================"

gcloud storage ls "gs://${BUCKET_NAME}/raw_bq/" || true
