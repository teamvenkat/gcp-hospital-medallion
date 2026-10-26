CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${BRONZE_DATASET}.encounters`
(
    encounter_id STRING NOT NULL,
    registration_id STRING,
    doctor_id STRING,
    department_id STRING,
    encounter_date TIMESTAMP,
    encounter_type STRING,
    diagnosis STRING,
    status STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,

    source_file_name STRING NOT NULL,
    source_file_timestamp TIMESTAMP NOT NULL,
    ingestion_timestamp TIMESTAMP NOT NULL,
    run_id STRING,
    batch_id STRING

)
PARTITION BY DATE(encounter_date)
CLUSTER BY registration_id, doctor_id, department_id;
