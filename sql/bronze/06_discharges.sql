CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${BRONZE_DATASET}.discharges`
(
    discharge_id STRING NOT NULL,
    admission_id STRING,
    registration_id STRING,
    discharge_date TIMESTAMP,
    discharge_status STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,

    source_file_name STRING NOT NULL,
    source_file_timestamp TIMESTAMP NOT NULL,
    ingestion_timestamp TIMESTAMP NOT NULL,
    run_id STRING,
    batch_id STRING

)
PARTITION BY DATE(discharge_date)
CLUSTER BY admission_id, registration_id, discharge_status;
