#!/usr/bin/env bash

# Hospital Medallion - GCP API enablement
#
# This script enables only the APIs required for the current
# raw ingestion / BigQuery platform.
#
# It is safe to run multiple times.
#
# It does NOT create:
# - GCS buckets
# - BigQuery datasets
# - BigQuery tables
# - Composer environments

set -euo pipefail

PROJECT_ID="${HOSPITAL_GCP_PROJECT_ID:-project-5fbc8bf7-2dd6-4f0a-a5f}"

REQUIRED_APIS=(
    "bigquery.googleapis.com"
    "storage.googleapis.com"
)

echo "========================================"
echo "Hospital Medallion"
echo "GCP API Enablement"
echo "========================================"
echo
echo "Project: $PROJECT_ID"
echo

# --------------------------------------------------
# Check gcloud
# --------------------------------------------------

if ! command -v gcloud >/dev/null 2>&1; then
    echo "[FAIL] Google Cloud CLI is not installed."
    exit 1
fi

# --------------------------------------------------
# Verify active project
# --------------------------------------------------

ACTIVE_PROJECT="$(gcloud config get-value project 2>/dev/null | tr -d '\r')"

if [[ "$ACTIVE_PROJECT" != "$PROJECT_ID" ]]; then
    echo "[FAIL] Active GCP project does not match."
    echo
    echo "Expected: $PROJECT_ID"
    echo "Found   : $ACTIVE_PROJECT"
    echo
    echo "Run Step 2 first."
    exit 1
fi

echo "[PASS] Active project: $ACTIVE_PROJECT"
echo

# --------------------------------------------------
# Enable required APIs
# --------------------------------------------------

for API in "${REQUIRED_APIS[@]}"
do
    echo "Checking: $API"

    if gcloud services list \
        --enabled \
        --project="$PROJECT_ID" \
        --filter="config.name=$API" \
        --format="value(config.name)" \
        | grep -qx "$API"
    then
        echo "[ALREADY_ENABLED] $API"
    else
        echo "[ENABLING] $API"

        gcloud services enable "$API" \
            --project="$PROJECT_ID"

        echo "[ENABLED] $API"
    fi

    echo
done

# --------------------------------------------------
# Final verification
# --------------------------------------------------

echo "========================================"
echo "API Verification"
echo "========================================"
echo

FAILED=0

for API in "${REQUIRED_APIS[@]}"
do
    if gcloud services list \
        --enabled \
        --project="$PROJECT_ID" \
        --filter="config.name=$API" \
        --format="value(config.name)" \
        | grep -qx "$API"
    then
        echo "[PASS] $API"
    else
        echo "[FAIL] $API"
        FAILED=1
    fi
done

echo

if [[ "$FAILED" -ne 0 ]]; then
    echo "API enablement verification FAILED."
    exit 1
fi

echo "========================================"
echo "GCP API Enablement Completed"
echo "========================================"
echo
echo "Required APIs are enabled."
echo
echo "Composer has NOT been enabled."
echo "Composer will be handled separately because"
echo "it creates a billable managed environment."