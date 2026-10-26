CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${BRONZE_DATASET}.admissions`
(
    admission_id STRING NOT NULL,
    registration_id STRING,
    encounter_id STRING,
    admission_date TIMESTAMP,
    admission_type STRING,
    ward STRING,
    status STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,

    source_file_name STRING NOT NULL,
    source_file_timestamp TIMESTAMP NOT NULL,
    ingestion_timestamp TIMESTAMP NOT NULL,
    run_id STRING,
    batch_id STRING

)
PARTITION BY DATE(admission_date)
CLUSTER BY registration_id, encounter_id, ward;
