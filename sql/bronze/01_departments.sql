CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.${BRONZE_DATASET}.departments`
(
    department_id STRING NOT NULL,
    department_name STRING NOT NULL,
    city STRING NOT NULL,

    source_file_name STRING NOT NULL,
    source_file_timestamp TIMESTAMP NOT NULL,
    ingestion_timestamp TIMESTAMP NOT NULL,
    run_id STRING,
    batch_id STRING

)
CLUSTER BY department_id, city;
