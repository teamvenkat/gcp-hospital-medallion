CREATE TABLE IF NOT EXISTS `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.pipeline_run`
(
    run_id STRING NOT NULL,
    batch_id STRING,
    pipeline_name STRING NOT NULL,
    run_date DATE NOT NULL,
    expected_source_date DATE NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status STRING NOT NULL,
    total_files_expected INT64,
    total_files_received INT64,
    total_files_processed INT64,
    total_files_failed INT64,
    total_records_received INT64,
    total_records_rejected INT64,
    error_message STRING,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
)
PARTITION BY run_date
CLUSTER BY pipeline_name, status;
