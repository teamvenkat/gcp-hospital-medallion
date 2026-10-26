CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${BRONZE_DATASET}.doctors`
(
    doctor_id STRING NOT NULL,
    first_name STRING,
    last_name STRING,
    specialization STRING,
    department_id STRING,
    city STRING,

    source_file_name STRING NOT NULL,
    source_file_timestamp TIMESTAMP NOT NULL,
    ingestion_timestamp TIMESTAMP NOT NULL,
    run_id STRING,
    batch_id STRING

)
CLUSTER BY doctor_id, department_id, city;
