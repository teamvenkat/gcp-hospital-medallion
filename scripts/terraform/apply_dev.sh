#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DEV_DIR="${ROOT_DIR}/terraform/environments/dev"

cd "${DEV_DIR}"

if [[ ! -f dev.tfplan ]]; then
  echo "[ERROR] dev.tfplan does not exist."
  echo "Run ./scripts/terraform/plan_dev.sh first."
  exit 1
fi

echo "Applying the previously reviewed DEV plan..."
terraform apply dev.tfplan
rm -f dev.tfplan
