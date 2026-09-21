#!/bin/bash

set -e

CONFIG_FILE="config/dev.env"

if [[ ! -f "$CONFIG_FILE" ]]
then
    echo "ERROR: Configuration file not found: $CONFIG_FILE"
    exit 1
fi

source "$CONFIG_FILE"

: "${PROJECT_ID:?PROJECT_ID is not set}"
: "${CONTROL_DATASET:?CONTROL_DATASET is not set}"
: "${RAW_BUCKET:?RAW_BUCKET is not set}"

export PROJECT_ID
export CONTROL_DATASET
export RAW_BUCKET

PROCESSING_DATE=""

while [[ $# -gt 0 ]]
do
    case "$1" in
        --processing-date)
            PROCESSING_DATE="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Usage: $0 --processing-date YYYY-MM-DD"
            exit 2
            ;;
    esac
done

if [[ -z "$PROCESSING_DATE" ]]
then
    echo "ERROR: --processing-date is required"
    echo "Usage: $0 --processing-date YYYY-MM-DD"
    exit 2
fi

echo "======================================"
echo "Hospital Raw File Ingestion"
echo "======================================"
echo "Processing date: $PROCESSING_DATE"
echo ""

python src/hospital_pipeline/ingestion/run_ingestion.py \
    --processing-date "$PROCESSING_DATE"

echo ""
echo "======================================"
echo "Raw file ingestion completed"
echo "======================================"
