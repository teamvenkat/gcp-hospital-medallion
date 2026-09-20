#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEV_DIR="${ROOT_DIR}/terraform/environments/dev"

cd "${DEV_DIR}"

terraform fmt -check
terraform validate

terraform plan   -var-file=terraform.tfvars   -out=dev.tfplan

echo
echo "[PASS] Plan created: ${DEV_DIR}/dev.tfplan"
echo "Review it before applying."
