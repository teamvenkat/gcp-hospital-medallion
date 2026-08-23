#!/usr/bin/env bash

# Hospital Medallion - BigQuery dataset setup
#
# Creates/verifies ONLY the datasets used by this project:
#   hospital_bronze_ven
#   hospital_silver_ven
#   hospital_gold_ven
#   hospital_control
#
# Existing non-_ven datasets are deliberately NOT touched:
#   hospital_bronze
#   hospital_silver
#   hospital_gold
#
# Idempotent: safe to run repeatedly.
#
# This script creates DATASETS ONLY.
# It does not create tables, views, models, or ingestion configuration.

set -euo pipefail

PROJECT_ID="${HOSPITAL_GCP_PROJECT_ID:-project-5fbc8bf7-2dd6-4f0a-a5f}"
LOCATION="${HOSPITAL_GCP_REGION:-asia-south1}"

BRONZE_DATASET="hospital_bronze_ven"
SILVER_DATASET="hospital_silver_ven"
GOLD_DATASET="hospital_gold_ven"
CONTROL_DATASET="hospital_control"

echo "========================================"
echo "Hospital Medallion"
echo "BigQuery Dataset Setup"
echo "========================================"
echo
echo "Project  : $PROJECT_ID"
echo "Location : $LOCATION"
echo
echo "Project datasets used by this setup:"
echo "  $BRONZE_DATASET"
echo "  $SILVER_DATASET"
echo "  $GOLD_DATASET"
echo "  $CONTROL_DATASET"
echo
echo "Existing non-_ven datasets will NOT be touched:"
echo "  hospital_bronze"
echo "  hospital_silver"
echo "  hospital_gold"
echo

# --------------------------------------------------
# 1. Check required CLIs
# --------------------------------------------------

if ! command -v gcloud >/dev/null 2>&1; then
    echo "[FAIL] Google Cloud CLI is not installed."
    exit 1
fi

if ! command -v bq >/dev/null 2>&1; then
    echo "[FAIL] BigQuery CLI is not installed."
    exit 1
fi

# --------------------------------------------------
# 2. Verify active project
# --------------------------------------------------

ACTIVE_PROJECT="$(gcloud config get-value project 2>/dev/null | tr -d '\r')"

if [[ "$ACTIVE_PROJECT" != "$PROJECT_ID" ]]; then
    echo "[FAIL] Active GCP project does not match."
    echo "       Expected: $PROJECT_ID"
    echo "       Found   : $ACTIVE_PROJECT"
    echo "       Run Step 2 first."
    exit 1
fi

echo "[PASS] Active project: $ACTIVE_PROJECT"
echo

# --------------------------------------------------
# 3. Create/verify only our datasets
# --------------------------------------------------

create_dataset() {
    local dataset_id="$1"
    local description="$2"

    echo "Checking dataset: $dataset_id"

    if bq show \
        --project_id="$PROJECT_ID" \
        "${PROJECT_ID}:${dataset_id}" >/dev/null 2>&1
    then
        echo "[ALREADY_EXISTS] ${PROJECT_ID}:${dataset_id}"
    else
        echo "[CREATING] ${PROJECT_ID}:${dataset_id}"

        bq --location="$LOCATION" mk \
            --dataset \
            --project_id="$PROJECT_ID" \
            --description="$description" \
            "${PROJECT_ID}:${dataset_id}"

        echo "[CREATED] ${PROJECT_ID}:${dataset_id}"
    fi

    echo
}

create_dataset \
    "$BRONZE_DATASET" \
    "Hospital Bronze raw and append-only data layer"

create_dataset \
    "$SILVER_DATASET" \
    "Hospital Silver cleansed, deduplicated and conformed data layer"

create_dataset \
    "$GOLD_DATASET" \
    "Hospital Gold curated analytical data layer"

create_dataset \
    "$CONTROL_DATASET" \
    "Operational control, audit, reconciliation, DQ and pipeline metadata for the hospital data platform"

# --------------------------------------------------
# 4. Verify our dataset locations
# --------------------------------------------------

echo "========================================"
echo "Dataset Verification"
echo "========================================"
echo

FAILED=0

for DATASET in \
    "$BRONZE_DATASET" \
    "$SILVER_DATASET" \
    "$GOLD_DATASET" \
    "$CONTROL_DATASET"
do
    DATASET_LOCATION="$(
        bq show \
            --format=prettyjson \
            "${PROJECT_ID}:${DATASET}" 2>/dev/null \
        | python3 -c '
import json
import sys
data = json.load(sys.stdin)
print(data.get("location", ""))
'
    )"

    if [[ "$DATASET_LOCATION" == "$LOCATION" ]]; then
        echo "[PASS] $DATASET : $DATASET_LOCATION"
    else
        echo "[FAIL] $DATASET : expected $LOCATION, found $DATASET_LOCATION"
        FAILED=1
    fi
done

echo

if [[ "$FAILED" -ne 0 ]]; then
    echo "Dataset verification FAILED."
    exit 1
fi

# --------------------------------------------------
# Final summary
# --------------------------------------------------

echo "========================================"
echo "BigQuery Dataset Setup Summary"
echo "========================================"
echo
echo "[PASS] $PROJECT_ID:$BRONZE_DATASET"
echo "[PASS] $PROJECT_ID:$SILVER_DATASET"
echo "[PASS] $PROJECT_ID:$GOLD_DATASET"
echo "[PASS] $PROJECT_ID:$CONTROL_DATASET"
echo
echo "Location: $LOCATION"
echo
echo "hospital_bronze, hospital_silver and hospital_gold"
echo "were NOT modified."
echo
echo "Only datasets were created/verified."
echo "No tables or views were created."
echo "No Composer environment was created."
echo
echo "BigQuery dataset setup completed successfully."
