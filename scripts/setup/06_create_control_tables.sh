#!/bin/bash

set -e

echo "======================================"
echo "Creating Hospital Control Tables"
echo "======================================"

for file in sql/control/ddl/*.sql
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
echo "All control tables created successfully"
echo "======================================"