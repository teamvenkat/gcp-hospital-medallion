#!/bin/bash
set -e

echo "======================================"
echo "Creating Hospital Bronze Tables"
echo "======================================"

for file in sql/bronze/*.sql
do
    echo ""
    echo "===== Executing $file ====="

    bq query \
        --use_legacy_sql=false \
        < "$file"

    echo "===== SUCCESS: $file ====="
done

echo ""
echo "======================================"
echo "All Bronze tables created successfully"
echo "======================================"
