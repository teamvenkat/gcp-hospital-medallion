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
FROM `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.file_ingestion_config`
ORDER BY entity_name;
