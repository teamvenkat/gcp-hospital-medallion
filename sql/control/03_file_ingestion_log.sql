CREATE TABLE IF NOT EXISTS `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.file_ingestion_log`
(
    run_id STRING NOT NULL,
    batch_id STRING,
    file_name STRING NOT NULL,
    entity_name STRING NOT NULL,
    source_file_timestamp TIMESTAMP,
    expected_source_date DATE,
    file_size_bytes INT64,
    file_checksum STRING,
    gcs_uri STRING,
    attempt_number INT64 NOT NULL,
    validation_status STRING,
    processing_status STRING,
    row_count INT64,
    accepted_count INT64,
    rejected_count INT64,
    retryable BOOL,
    error_code STRING,
    error_message STRING,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(created_at)
CLUSTER BY entity_name, processing_status, file_name;
