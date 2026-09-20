#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BOOTSTRAP_DIR="${ROOT_DIR}/terraform/bootstrap"

cd "${BOOTSTRAP_DIR}"

if [[ ! -f terraform.tfvars ]]; then
  echo "[ERROR] terraform.tfvars does not exist."
  echo "Create it from terraform.tfvars.example and review the values."
  exit 1
fi

echo "======================================"
echo "Terraform Bootstrap"
echo "======================================"

gcloud auth application-default print-access-token >/dev/null

terraform init
terraform fmt -check
terraform validate
terraform plan   -var-file=terraform.tfvars   -out=bootstrap.tfplan

echo
read -r -p "Apply this bootstrap plan? Type APPLY: " CONFIRM
if [[ "${CONFIRM}" != "APPLY" ]]; then
  echo "Aborted."
  rm -f bootstrap.tfplan
  exit 1
fi

terraform apply bootstrap.tfplan
rm -f bootstrap.tfplan

echo
echo "[PASS] Terraform state bucket created/managed."
terraform output
