#!/usr/bin/env bash

set -euo pipefail

PROJECT_ID="project-5fbc8bf7-2dd6-4f0a-a5f"
BUCKET_NAME="gcp-hospital-medallion-data"
CONTROL_DATASET="hospital_control"

echo "========================================"
echo "Hospital Medallion"
echo "Development Environment Reset"
echo "========================================"
echo
echo "Project          : ${PROJECT_ID}"
echo "GCS Bucket       : gs://${BUCKET_NAME}"
echo "Control Dataset  : ${CONTROL_DATASET}"
echo
echo "THIS WILL DELETE:"
echo "  - GCS bucket and ALL objects inside it"
echo "  - BigQuery control dataset and ALL tables inside it"
echo
echo "THIS WILL NOT DELETE:"
echo "  - hospital_bronze_ven"
echo "  - Any other BigQuery dataset"
echo "  - The GCP project"
echo "  - Composer"
echo "  - Local files"
echo

read -r -p "Type DELETE to continue: " CONFIRMATION

if [[ "${CONFIRMATION}" != "DELETE" ]]; then
    echo
    echo "Reset cancelled."
    exit 0
fi

echo
echo "========================================"
echo "Starting reset"
echo "========================================"

ACTIVE_PROJECT="$(gcloud config get-value project 2>/dev/null || true)"

if [[ "${ACTIVE_PROJECT}" != "${PROJECT_ID}" ]]; then
    echo "[FAIL] Active GCP project is '${ACTIVE_PROJECT}', expected '${PROJECT_ID}'."
    exit 1
fi

echo "[PASS] Active project: ${PROJECT_ID}"

# ------------------------------------------------------------
# 1. Delete GCS bucket
# ------------------------------------------------------------

echo
echo "[1/2] Removing GCS bucket..."

if gcloud storage buckets describe "gs://${BUCKET_NAME}" \
    --project="${PROJECT_ID}" >/dev/null 2>&1; then

    echo "[FOUND] gs://${BUCKET_NAME}"
    echo "[DELETE] Removing bucket and all objects..."

    gcloud storage rm --recursive "gs://${BUCKET_NAME}"

    # Verify deletion.
    if gcloud storage buckets describe "gs://${BUCKET_NAME}" \
        --project="${PROJECT_ID}" >/dev/null 2>&1; then
        echo "[FAIL] GCS bucket still exists after deletion."
        exit 1
    fi

    echo "[PASS] GCS bucket deleted."
else
    echo "[SKIP] GCS bucket does not exist."
fi

# ------------------------------------------------------------
# 2. Delete BigQuery control dataset
# ------------------------------------------------------------

echo
echo "[2/2] Removing BigQuery control dataset..."

DATASET_REF="${PROJECT_ID}:${CONTROL_DATASET}"

if bq show --project_id="${PROJECT_ID}" "${DATASET_REF}" >/dev/null 2>&1; then

    echo "[FOUND] ${DATASET_REF}"
    echo "[DELETE] Removing dataset and all tables..."

    bq rm -r -f "${DATASET_REF}"

    # Verify deletion. Failure here must stop the reset.
    if bq show --project_id="${PROJECT_ID}" "${DATASET_REF}" >/dev/null 2>&1; then
        echo "[FAIL] BigQuery control dataset still exists after deletion."
        exit 1
    fi

    echo "[PASS] Control dataset deleted."
else
    echo "[SKIP] Control dataset does not exist."
fi

echo
echo "========================================"
echo "Verifying reset state"
echo "========================================"

if gcloud storage buckets describe "gs://${BUCKET_NAME}" \
    --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo "[FAIL] GCS bucket still exists."
    exit 1
fi
echo "[PASS] GCS bucket absent."

if bq show --project_id="${PROJECT_ID}" "${DATASET_REF}" >/dev/null 2>&1; then
    echo "[FAIL] Control dataset still exists."
    exit 1
fi
echo "[PASS] Control dataset absent."

echo
echo "========================================"
echo "Development Reset Completed"
echo "========================================"
echo
echo "Deleted:"
echo "  GCS bucket       : gs://${BUCKET_NAME}"
echo "  Control dataset  : ${DATASET_REF}"
echo
echo "Preserved:"
echo "  BigQuery Bronze  : ${PROJECT_ID}:hospital_bronze_ven"
echo "  GCP project      : ${PROJECT_ID}"
echo "  Composer         : unchanged"
echo "  Local files      : unchanged"
echo
echo "You can now rerun the setup scripts"
echo "for storage and control tables from scratch."
