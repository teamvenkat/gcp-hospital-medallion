#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================"
echo "Hospital Medallion"
echo "Full Environment Setup"
echo "========================================"
echo
echo "Setup scripts:"
echo "  00_reset_ingestion_resources.sh"
echo "  01_check_prerequisites.sh"
echo "  02_configure_gcp.sh"
echo "  03_enable_apis.sh"
echo "  04_create_storage.sh"
echo "  05_create_datasets.sh"
echo "  06_create_control_tables.sh"
echo "  07_seed_file_ingestion_config.sh"
echo "  08_validate_control_layer.sh"
echo

run_step() {
    local script_name="$1"

    echo
    echo "========================================"
    echo "RUNNING: ${script_name}"
    echo "========================================"

    if [[ ! -x "${SCRIPT_DIR}/${script_name}" ]]; then
        echo "[FAIL] ${script_name} is not executable."
        echo "Run: chmod +x scripts/setup/*.sh"
        exit 1
    fi

    "${SCRIPT_DIR}/${script_name}"

    echo
    echo "[PASS] ${script_name}"
}

run_step "00_reset_ingestion_resources.sh"
run_step "01_check_prerequisites.sh"
run_step "02_configure_gcp.sh"
run_step "03_enable_apis.sh"
run_step "04_create_storage.sh"
run_step "05_create_datasets.sh"
run_step "06_create_control_tables.sh"
run_step "07_seed_file_ingestion_config.sh"
run_step "08_validate_control_layer.sh"

echo
echo "========================================"
echo "Hospital Medallion"
echo "Full Setup Completed"
echo "========================================"
echo
echo "All setup steps completed successfully."
echo
echo "Next:"
echo "  Run the raw file ingestion workflow."
echo