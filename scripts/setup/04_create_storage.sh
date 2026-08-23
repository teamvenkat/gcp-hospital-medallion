#!/usr/bin/env bash

# Hospital Medallion - GCS raw storage setup
#
# Creates/verifies the raw landing bucket.
# Idempotent: safe to run repeatedly.
#
# Does NOT create seven table folders.
# Files will be landed under:
#   gs://<bucket>/raw_bq/<filename>
#
# Does NOT create BigQuery datasets/tables or Composer environments.

set -euo pipefail

PROJECT_ID="${HOSPITAL_GCP_PROJECT_ID:-project-5fbc8bf7-2dd6-4f0a-a5f}"
REGION="${HOSPITAL_GCP_REGION:-asia-south1}"
BUCKET="${HOSPITAL_GCS_BUCKET:-gcp-hospital-medallion-data}"

echo "========================================"
echo "Hospital Medallion"
echo "GCS Raw Storage Setup"
echo "========================================"
echo
echo "Project : $PROJECT_ID"
echo "Region  : $REGION"
echo "Bucket  : $BUCKET"
echo

# --------------------------------------------------
# 1. Check gcloud
# --------------------------------------------------

if ! command -v gcloud >/dev/null 2>&1; then
    echo "[FAIL] Google Cloud CLI is not installed."
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
# 3. Check whether bucket exists
# --------------------------------------------------

echo "[1/4] Checking GCS bucket..."

if gcloud storage buckets describe "gs://$BUCKET" \
    --project="$PROJECT_ID" >/dev/null 2>&1
then
    echo "[ALREADY_EXISTS] gs://$BUCKET"
else
    echo "[CREATING] gs://$BUCKET"

    gcloud storage buckets create "gs://$BUCKET" \
        --project="$PROJECT_ID" \
        --location="$REGION" \
        --uniform-bucket-level-access

    echo "[CREATED] gs://$BUCKET"
fi

echo

# --------------------------------------------------
# 4. Verify bucket metadata
# --------------------------------------------------

echo "[2/4] Verifying bucket metadata..."

BUCKET_LOCATION="$(
    gcloud storage buckets describe "gs://$BUCKET" \
        --format="value(location)" 2>/dev/null || true
)"

if [[ -z "$BUCKET_LOCATION" ]]; then
    echo "[FAIL] Could not read bucket metadata."
    exit 1
fi

echo "[PASS] Bucket metadata is accessible."
echo

# --------------------------------------------------
# 5. Verify location
# --------------------------------------------------

echo "[3/4] Verifying bucket location..."

BUCKET_LOCATION="$(
    gcloud storage buckets describe "gs://$BUCKET" \
        --format="value(location)"
)"

BUCKET_LOCATION="$(echo "$BUCKET_LOCATION" | tr '[:upper:]' '[:lower:]')"
EXPECTED_LOCATION="$(echo "$REGION" | tr '[:upper:]' '[:lower:]')"

if [[ "$BUCKET_LOCATION" != "$EXPECTED_LOCATION" ]]; then
    echo "[FAIL] Bucket location does not match."
    echo "       Expected: $EXPECTED_LOCATION"
    echo "       Found   : $BUCKET_LOCATION"
    exit 1
fi

echo "[PASS] Bucket location: $BUCKET_LOCATION"
echo

# --------------------------------------------------
# 6. Verify access
# --------------------------------------------------

echo "[4/4] Verifying bucket access..."

if gcloud storage ls "gs://$BUCKET" >/dev/null 2>&1; then
    echo "[PASS] Bucket is accessible."
else
    echo "[FAIL] Bucket exists but is not accessible."
    exit 1
fi

echo

# --------------------------------------------------
# Final summary
# --------------------------------------------------

echo "========================================"
echo "GCS Storage Setup Summary"
echo "========================================"
echo
echo "[PASS] Bucket : gs://$BUCKET"
echo "[PASS] Project: $PROJECT_ID"
echo "[PASS] Region : $BUCKET_LOCATION"
echo
echo "Raw landing path:"
echo "  gs://$BUCKET/raw_bq/"
echo
echo "No table-specific folders were created."
echo "No BigQuery resources were created."
echo "No Composer environment was created."
echo
echo "GCS storage setup completed successfully."
