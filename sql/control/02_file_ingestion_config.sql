CREATE TABLE IF NOT EXISTS `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.file_ingestion_config`
(
    entity_name STRING NOT NULL,
    filename_prefix STRING NOT NULL,
    mandatory BOOL NOT NULL,
    file_format STRING NOT NULL,
    target_bronze_table STRING NOT NULL,
    primary_key_column STRING,
    expected_file_date_rule STRING NOT NULL,
    retry_enabled BOOL NOT NULL,
    max_retries INT64 NOT NULL,
    is_active BOOL NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
