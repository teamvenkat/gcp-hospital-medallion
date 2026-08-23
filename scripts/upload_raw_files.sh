#!/bin/bash

set -e

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
