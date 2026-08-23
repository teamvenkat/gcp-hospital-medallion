#!/bin/bash

set -e

echo "======================================"
echo "Seeding File Ingestion Configuration"
echo "======================================"

bq query \
    --use_legacy_sql=false \
    < sql/control/seed/file_ingestion_config.sql

echo ""
echo "======================================"
echo "File ingestion configuration loaded"
echo "======================================"