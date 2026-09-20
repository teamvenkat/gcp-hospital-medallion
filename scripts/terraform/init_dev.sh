#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEV_DIR="${ROOT_DIR}/terraform/environments/dev"

cd "${DEV_DIR}"

if [[ ! -f terraform.tfvars ]]; then
  echo "[ERROR] terraform.tfvars does not exist."
  echo "Create it from terraform.tfvars.example."
  exit 1
fi

echo "======================================"
echo "Terraform DEV Initialization"
echo "======================================"

terraform init

echo
echo "[PASS] DEV Terraform backend initialized."
terraform fmt -check
terraform validate
