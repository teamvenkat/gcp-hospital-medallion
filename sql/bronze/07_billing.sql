CREATE TABLE IF NOT EXISTS `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_bronze_ven.billing`
(
    bill_id STRING NOT NULL,
    registration_id STRING,
    encounter_id STRING,
    admission_id STRING,
    discharge_id STRING,
    bill_date TIMESTAMP,
    bill_type STRING,
    bill_description STRING,
    consultation_amount FLOAT64,
    procedure_amount FLOAT64,
    room_amount FLOAT64,
    other_amount FLOAT64,
    total_amount FLOAT64,
    payment_status STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,

    source_file_name STRING NOT NULL,
    source_file_timestamp TIMESTAMP NOT NULL,
    ingestion_timestamp TIMESTAMP NOT NULL,
    run_id STRING,
    batch_id STRING

)
PARTITION BY DATE(bill_date)
CLUSTER BY registration_id, encounter_id, payment_status;
