SELECT
    entity_name,
    filename_prefix,
    mandatory,
    file_format,
    target_bronze_table,
    primary_key_column,
    expected_file_date_rule,
    retry_enabled,
    max_retries,
    is_active
FROM `${PROJECT_ID}.${CONTROL_DATASET}.file_ingestion_config`
ORDER BY entity_name;