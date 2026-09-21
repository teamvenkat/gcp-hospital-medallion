#!/bin/bash

set -e

echo "======================================"
echo "Seeding File Ingestion Configuration"
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
: "${BRONZE_DATASET:?BRONZE_DATASET is not set}"

echo "Project: $PROJECT_ID"
echo "Control dataset: $CONTROL_DATASET"
echo "Bronze dataset: $BRONZE_DATASET"

sed \
    -e "s|\${PROJECT_ID}|${PROJECT_ID}|g" \
    -e "s|\${CONTROL_DATASET}|${CONTROL_DATASET}|g" \
    -e "s|\${BRONZE_DATASET}|${BRONZE_DATASET}|g" \
    sql/control/seed/file_ingestion_config.sql |
bq query \
    --use_legacy_sql=false

echo ""
echo "======================================"
echo "File ingestion configuration loaded"
echo "======================================"