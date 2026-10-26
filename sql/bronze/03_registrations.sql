CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${BRONZE_DATASET}.registrations`
(
    registration_id STRING NOT NULL,
    first_name STRING,
    last_name STRING,
    date_of_birth DATE,
    gender STRING,
    city STRING,
    registration_date TIMESTAMP,
    status STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,

    source_file_name STRING NOT NULL,
    source_file_timestamp TIMESTAMP NOT NULL,
    ingestion_timestamp TIMESTAMP NOT NULL,
    run_id STRING,
    batch_id STRING

)
PARTITION BY DATE(registration_date)
CLUSTER BY registration_id, city, status;
