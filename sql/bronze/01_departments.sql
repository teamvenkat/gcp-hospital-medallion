CREATE TABLE IF NOT EXISTS `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_bronze_ven.departments`
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
