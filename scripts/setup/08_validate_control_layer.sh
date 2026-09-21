#!/bin/bash

set -e

echo "======================================"
echo "Validating Hospital Control Layer"
echo "======================================"

CONFIG_FILE="config/dev.env"

if [[ ! -f "$CONFIG_FILE" ]]
then
    echo "ERROR: Configuration file not found: $CONFIG_FILE"
    exit 1
fi

source "$CONFIG_FILE"

: "${PROJECT_ID:?PROJECT_ID is not set}"
: "${CONTROL_DATASET:?CONTROL_DATASET is not set}"

echo "Project: $PROJECT_ID"
echo "Control dataset: $CONTROL_DATASET"

sed \
    -e "s|\${PROJECT_ID}|${PROJECT_ID}|g" \
    -e "s|\${CONTROL_DATASET}|${CONTROL_DATASET}|g" \
    sql/control/validation/verify_file_ingestion_config.sql |
bq query \
    --use_legacy_sql=false

echo ""
echo "======================================"
echo "Control layer validation completed"
echo "======================================"