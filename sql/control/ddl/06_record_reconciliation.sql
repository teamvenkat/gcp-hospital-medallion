CREATE TABLE IF NOT EXISTS `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.record_reconciliation`
(
    run_id STRING NOT NULL,
    batch_id STRING,
    entity_name STRING NOT NULL,
    source_record_count INT64,
    bronze_insert_count INT64,
    bronze_record_count INT64,
    silver_insert_count INT64,
    silver_update_count INT64,
    silver_delete_count INT64,
    rejected_record_count INT64,
    expected_record_count INT64,
    actual_record_count INT64,
    reconciliation_status STRING NOT NULL,
    created_at TIMESTAMP NOT NULL
)
PARTITION BY DATE(created_at)
CLUSTER BY entity_name, reconciliation_status;
