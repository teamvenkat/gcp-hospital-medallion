#!/usr/bin/env bash

# Hospital Medallion - GCP local CLI configuration
#
# This script configures only the local gcloud CLI.
# It does NOT enable APIs or create GCP resources.

set -euo pipefail

PROJECT_ID="${HOSPITAL_GCP_PROJECT_ID:-project-5fbc8bf7-2dd6-4f0a-a5f}"
REGION="${HOSPITAL_GCP_REGION:-asia-south1}"

echo "========================================"
echo "Hospital Medallion"
echo "GCP CLI Configuration"
echo "========================================"
echo
echo "Project : $PROJECT_ID"
echo "Region  : $REGION"
echo

# --------------------------------------------------
# 1. Check gcloud
# --------------------------------------------------

if ! command -v gcloud >/dev/null 2>&1; then
    echo "[FAIL] Google Cloud CLI is not installed."
    exit 1
fi

# --------------------------------------------------
# 2. Check authenticated account
# --------------------------------------------------

echo "[1/5] Checking authenticated account..."

ACCOUNT="$(gcloud config get-value account 2>/dev/null | tr -d '\r')"

if [[ -z "$ACCOUNT" || "$ACCOUNT" == "(unset)" ]]; then
    echo "[FAIL] No active gcloud account."
    echo "       Run: gcloud auth login"
    exit 1
fi

echo "[PASS] Account: $ACCOUNT"
echo

# --------------------------------------------------
# 3. Verify project access
# --------------------------------------------------

echo "[2/5] Verifying project access..."

if ! gcloud projects describe "$PROJECT_ID" \
    --format="value(projectId)" >/dev/null 2>&1
then
    echo "[FAIL] Project '$PROJECT_ID' could not be accessed."
    echo "       Check the project ID and your account permissions."
    exit 1
fi

echo "[PASS] Project is accessible."
echo

# --------------------------------------------------
# 4. Set active project
# --------------------------------------------------

echo "[3/5] Setting active project..."

gcloud config set project "$PROJECT_ID"

echo "[PASS] Active project set to $PROJECT_ID"
echo

# --------------------------------------------------
# 5. Set default region
# --------------------------------------------------

echo "[4/5] Setting default Compute region..."

gcloud config set compute/region "$REGION"

echo "[PASS] Default Compute region set to $REGION"
echo

# --------------------------------------------------
# Final verification
# --------------------------------------------------

echo "[5/5] Verifying resulting configuration..."
echo

FINAL_PROJECT="$(gcloud config get-value project 2>/dev/null | tr -d '\r')"
FINAL_ACCOUNT="$(gcloud config get-value account 2>/dev/null | tr -d '\r')"
FINAL_REGION="$(gcloud config get-value compute/region 2>/dev/null | tr -d '\r')"

echo "Project : $FINAL_PROJECT"
echo "Account : $FINAL_ACCOUNT"
echo "Region  : $FINAL_REGION"
echo

# --------------------------------------------------
# Validate final values
# --------------------------------------------------

if [[ "$FINAL_PROJECT" != "$PROJECT_ID" ]]; then
    echo "[FAIL] Project configuration verification failed."
    exit 1
fi

if [[ "$FINAL_REGION" != "$REGION" ]]; then
    echo "[FAIL] Region configuration verification failed."
    exit 1
fi

if [[ -z "$FINAL_ACCOUNT" || "$FINAL_ACCOUNT" == "(unset)" ]]; then
    echo "[FAIL] Account configuration verification failed."
    exit 1
fi

echo "========================================"
echo "GCP CLI Configuration Summary"
echo "========================================"
echo
echo "[PASS] Project : $FINAL_PROJECT"
echo "[PASS] Account : $FINAL_ACCOUNT"
echo "[PASS] Region  : $FINAL_REGION"
echo
echo "GCP CLI configuration completed successfully."
echo
echo "No APIs, buckets, datasets, tables, or other"
echo "GCP resources were created by this script."