#!/bin/bash

set -e

echo "======================================"
echo "Creating Hospital Bronze Tables"
echo "======================================"

CONFIG_FILE="config/dev.env"

if [[ ! -f "$CONFIG_FILE" ]]
then
    echo "ERROR: Configuration file not found: $CONFIG_FILE"
    exit 1
fi

source "$CONFIG_FILE"

: "${PROJECT_ID:?PROJECT_ID is not set}"
: "${BRONZE_DATASET:?BRONZE_DATASET is not set}"

echo "Project: $PROJECT_ID"
echo "Bronze dataset: $BRONZE_DATASET"

for file in sql/bronze/*.sql
do
    echo ""
    echo "===== Executing $file ====="

    sed \
        -e "s|\${PROJECT_ID}|${PROJECT_ID}|g" \
        -e "s|\${BRONZE_DATASET}|${BRONZE_DATASET}|g" \
        "$file" |
    bq query \
        --use_legacy_sql=false

    echo "===== SUCCESS: $file ====="
done

echo ""
echo "======================================"
echo "All Bronze tables created successfully"
echo "======================================"