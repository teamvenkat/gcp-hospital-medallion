#!/bin/bash

set -e

echo "======================================"
echo "Validating Hospital Control Layer"
echo "======================================"

bq query \
    --use_legacy_sql=false \
    < sql/control/validation/verify_file_ingestion_config.sql

echo ""
echo "======================================"
echo "Control layer validation completed"
echo "======================================"