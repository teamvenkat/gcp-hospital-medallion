CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${CONTROL_DATASET}.rejected_record_log`
(
    run_id STRING NOT NULL,
    batch_id STRING,
    file_name STRING NOT NULL,
    entity_name STRING NOT NULL,
    record_identifier STRING,
    error_code STRING NOT NULL,
    error_message STRING NOT NULL,
    rejected_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(rejected_at)
CLUSTER BY entity_name, error_code;
