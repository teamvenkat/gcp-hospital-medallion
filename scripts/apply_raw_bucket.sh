#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-project-5fbc8bf7-2dd6-4f0a-a5f}"
BUCKET_NAME="${BUCKET_NAME:-gcp-hospital-medallion-data}"
TFVARS="${TFVARS:-dev.tfvars}"

cd "$(dirname "$0")/../terraform"

terraform init
terraform validate
terraform plan \
  -var-file="${TFVARS}" \
  -out=tfplan

echo
read -r -p "Apply this Raw bucket configuration? Type APPLY: " CONFIRM
if [[ "${CONFIRM}" != "APPLY" ]]; then
  echo "Aborted."
  exit 1
fi

terraform apply tfplan
