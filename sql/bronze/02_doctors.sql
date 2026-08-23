CREATE TABLE IF NOT EXISTS `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_bronze_ven.doctors`
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
