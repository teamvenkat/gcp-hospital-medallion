CREATE TABLE IF NOT EXISTS `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.validation_error_log`
(
    error_id STRING NOT NULL,
    run_id STRING NOT NULL,
    batch_id STRING,
    file_name STRING,
    entity_name STRING,
    validation_stage STRING NOT NULL,
    error_type STRING NOT NULL,
    error_code STRING NOT NULL,
    column_name STRING,
    record_identifier STRING,
    raw_value STRING,
    error_message STRING NOT NULL,
    severity STRING NOT NULL,
    retryable BOOL NOT NULL,
    attempt_number INT64,
    error_timestamp TIMESTAMP NOT NULL
)
PARTITION BY DATE(error_timestamp)
CLUSTER BY entity_name, error_type, error_code;
