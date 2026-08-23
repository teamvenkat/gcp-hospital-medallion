#!/bin/bash
set -e

for file in data/raw_bq/*.csv
do
    echo "========================================"
    echo "$file"
    echo "========================================"
    head -n 3 "$file"
done