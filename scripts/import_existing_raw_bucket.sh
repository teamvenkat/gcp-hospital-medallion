#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-project-5fbc8bf7-2dd6-4f0a-a5f}"
BUCKET_NAME="${BUCKET_NAME:-gcp-hospital-medallion-data}"

cd "$(dirname "$0")/../terraform"

echo "Project : ${PROJECT_ID}"
echo "Bucket  : gs://${BUCKET_NAME}"
echo
echo "This imports the existing bucket into Terraform state."
echo "It does NOT change the bucket."
echo

terraform init
terraform import \
  -var="project_id=${PROJECT_ID}" \
  -var="bucket_name=${BUCKET_NAME}" \
  google_storage_bucket.raw \
  "projects/${PROJECT_ID}/buckets/${BUCKET_NAME}"

echo
echo "Import complete. Run:"
echo "  terraform plan -var-file=dev.tfvars"
