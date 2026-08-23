CREATE TABLE IF NOT EXISTS `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.dq_execution_log`
(
    run_id STRING NOT NULL,
    batch_id STRING,
    entity_name STRING NOT NULL,
    test_name STRING NOT NULL,
    test_type STRING,
    severity STRING NOT NULL,
    expected_result STRING,
    actual_result STRING,
    failed_record_count INT64,
    status STRING NOT NULL,
    error_message STRING,
    execution_start TIMESTAMP,
    execution_end TIMESTAMP,
    created_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(created_at)
CLUSTER BY entity_name, status, test_name;
