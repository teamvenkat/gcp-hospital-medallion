#!/bin/bash

set -e

echo "======================================"
echo "Creating Hospital Control Tables"
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

for file in sql/control/ddl/*.sql
do
    echo ""
    echo "===== Executing $file ====="

    sed \
        -e "s|\${PROJECT_ID}|${PROJECT_ID}|g" \
        -e "s|\${CONTROL_DATASET}|${CONTROL_DATASET}|g" \
        "$file" |
    bq query \
        --use_legacy_sql=false

    echo "===== SUCCESS: $file ====="
done

echo ""
echo "======================================"
echo "All control tables created successfully"
echo "======================================"