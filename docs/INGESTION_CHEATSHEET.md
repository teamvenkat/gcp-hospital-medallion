# Hospital Medallion — Setup & Ingestion Cheat Sheet

## 0. Project

```bash
cd ~/Documents/gcp/gcp-hospital-medallion
source .venv/bin/activate
```

Current GCP configuration:

```text
PROJECT_ID = project-5fbc8bf7-2dd6-4f0a-a5f
REGION     = asia-south1
BUCKET     = gcp-hospital-medallion-data
RAW PATH   = raw_bq/
```

---

# 1. Setup — Run in Order

```bash
./scripts/setup/01_check_prerequisites.sh
```

```bash
./scripts/setup/02_configure_gcp.sh
```

```bash
./scripts/setup/03_enable_apis.sh
```

```bash
./scripts/setup/04_create_storage.sh
```

```bash
./scripts/setup/05_create_datasets.sh
```

```bash
./scripts/setup/06_create_control_tables.sh
```

```bash
./scripts/setup/07_seed_file_ingestion_config.sh
```

```bash
./scripts/setup/08_validate_control_layer.sh
```

### Complete setup flow

```text
01 prerequisites
      ↓
02 GCP config
      ↓
03 APIs
      ↓
04 GCS
      ↓
05 BigQuery datasets
      ↓
06 control tables
      ↓
07 ingestion config
      ↓
08 validation
```

---

# 2. GCP Quick Checks

### Current project

```bash
gcloud config get-value project
```

### Current account

```bash
gcloud config get-value account
```

### Region

```bash
gcloud config get-value compute/region
```

### Authentication

```bash
gcloud auth list
```

### ADC

```bash
gcloud auth application-default login
```

---

# 3. APIs

Check enabled APIs:

```bash
gcloud services list --enabled
```

Check specific API:

```bash
gcloud services list \
  --enabled \
  --filter="config.name=bigquery.googleapis.com"
```

```bash
gcloud services list \
  --enabled \
  --filter="config.name=storage.googleapis.com"
```

Composer:

```bash
gcloud services list \
  --enabled \
  --filter="config.name=composer.googleapis.com"
```

Enable manually if required:

```bash
gcloud services enable bigquery.googleapis.com
gcloud services enable storage.googleapis.com
```

---

# 4. GCS

### Bucket

```bash
gcloud storage ls
```

### Bucket contents

```bash
gcloud storage ls gs://gcp-hospital-medallion-data/raw_bq/
```

### Bucket details

```bash
gcloud storage buckets describe \
  gs://gcp-hospital-medallion-data
```

### Upload manually — normally don't use this

```bash
gcloud storage cp file.csv \
  gs://gcp-hospital-medallion-data/raw_bq/
```

Our ingestion script handles this instead.

---

# 5. BigQuery Datasets

### List datasets

```bash
bq ls --project_id=project-5fbc8bf7-2dd6-4f0a-a5f
```

Our datasets:

```text
hospital_bronze_ven
hospital_silver_ven
hospital_gold_ven
hospital_control
```

Existing datasets — **DO NOT TOUCH**:

```text
hospital_bronze
hospital_silver
hospital_gold
```

### Show dataset

```bash
bq show \
  project-5fbc8bf7-2dd6-4f0a-a5f:hospital_control
```

---

# 6. Control Tables

### List control tables

```bash
bq ls \
  project-5fbc8bf7-2dd6-4f0a-a5f:hospital_control
```

Expected:

```text
pipeline_run
file_ingestion_config
file_ingestion_log
validation_error_log
rejected_record_log
record_reconciliation
dq_execution_log
```

### Control DDL

```text
sql/control/ddl/
├── 01_pipeline_run.sql
├── 02_file_ingestion_config.sql
├── 03_file_ingestion_log.sql
├── 04_validation_error_log.sql
├── 05_rejected_record_log.sql
├── 06_record_reconciliation.sql
└── 07_dq_execution_log.sql
```

### Recreate/verify control layer

```bash
./scripts/setup/06_create_control_tables.sh
./scripts/setup/07_seed_file_ingestion_config.sh
./scripts/setup/08_validate_control_layer.sh
```

---

# 7. Raw Files

Local source directory:

```text
data/raw_bq/
```

Files:

```text
admissions_YYYYMMDDHHMMSS.csv
billing_YYYYMMDDHHMMSS.csv
departments_YYYYMMDDHHMMSS.csv
discharges_YYYYMMDDHHMMSS.csv
doctors_YYYYMMDDHHMMSS.csv
encounters_YYYYMMDDHHMMSS.csv
registrations_YYYYMMDDHHMMSS.csv
```

No table folders:

```text
data/raw_bq/
├── admissions_...
├── billing_...
├── departments_...
└── ...
```

Same principle in GCS:

```text
gs://gcp-hospital-medallion-data/raw_bq/
```

---

# 8. Inspect Practice Files

```bash
./scripts/inspect_practice_csvs.sh
```

This is useful before running ingestion.

---

# 9. Daily Ingestion

Normal command:

```bash
./scripts/upload_raw_files.sh \
  --processing-date 2026-08-23
```

For:

```text
processing date = 2026-08-23
```

expected source date:

```text
2026-08-22
```

---

# 10. File Timestamp Rules

Valid:

```text
registrations_20260822122217.csv
```

Source date:

```text
2026-08-22
```

For processing date:

```text
2026-08-23
```

→ valid.

Older:

```text
registrations_20260821112217.csv
```

→ `NOT_T_MINUS_1`

Current/future:

```text
registrations_20260823132217.csv
```

→ `NOT_T_MINUS_1`

---

# 11. Ingestion Outcomes

### New valid file

```text
VALID T-1
   ↓
GCS upload
   ↓
SUCCESS
```

### Already processed

```text
same file/checksum
   ↓
SKIPPED
```

### Invalid date

```text
T-2 / T / future
   ↓
NOT_T_MINUS_1
   ↓
FAILED
```

### Mandatory file missing

```text
departments missing
   ↓
MISSING_MANDATORY_FILE
   ↓
FAILED
```

---

# 12. Typical Ingestion Summary

```text
======================================
INGESTION SUMMARY
======================================

Run ID               : <UUID>
Discovered            : 22
Success               : 5
Skipped               : 0
Failed                : 17
Mandatory missing     : 2
Mandatory failed      : 0
Records uploaded      : 12
Records rejected      : 0
Run status             : FAILED
```

Remember:

```text
Success = files newly uploaded
Skipped = already processed
Failed  = individual file failures
```

A run can therefore have:

```text
Success > 0
AND
Run status = FAILED
```

if mandatory files are missing or another fatal condition exists.

---

# 13. Query Pipeline Runs

```bash
bq query --use_legacy_sql=false "
SELECT *
FROM \`project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.pipeline_run\`
ORDER BY run_date DESC
LIMIT 20;
"
```

---

# 14. Query File Ingestion

```bash
bq query --use_legacy_sql=false "
SELECT
  file_name,
  entity_name,
  processing_status,
  validation_status,
  row_count,
  gcs_uri
FROM \`project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.file_ingestion_log\`
ORDER BY created_at DESC
LIMIT 50;
"
```

For a specific run:

```bash
bq query --use_legacy_sql=false "
SELECT
  file_name,
  entity_name,
  processing_status,
  validation_status,
  row_count,
  gcs_uri
FROM \`project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.file_ingestion_log\`
WHERE run_id = '<RUN_ID>'
ORDER BY entity_name;
"
```

---

# 15. Validation Errors

```bash
bq query --use_legacy_sql=false "
SELECT *
FROM \`project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.validation_error_log\`
ORDER BY error_timestamp DESC
LIMIT 50;
"
```

---

# 16. Rejected Records

```bash
bq query --use_legacy_sql=false "
SELECT *
FROM \`project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.rejected_record_log\`
ORDER BY rejected_at DESC
LIMIT 50;
"
```

---

# 17. Check GCS After Ingestion

```bash
gcloud storage ls \
  gs://gcp-hospital-medallion-data/raw_bq/
```

Detailed:

```bash
gcloud storage ls -l \
  gs://gcp-hospital-medallion-data/raw_bq/
```

---

# 18. Bronze

Bronze dataset:

```text
hospital_bronze_ven
```

Existing Bronze SQL:

```text
sql/bronze/
├── 01_departments.sql
├── 02_doctors.sql
├── 03_registrations.sql
├── 04_encounters.sql
├── 05_admissions.sql
├── 06_discharges.sql
└── 07_billing.sql
```

Existing script:

```bash
./scripts/create_bronze_tables.sh
```

**Don't run this as part of the raw-ingestion setup.**

Our architecture:

```text
Local CSV
    ↓
GCS raw_bq
    ↓
Bronze append
    ↓
Silver MERGE
    ↓
Gold
```

---

# 19. Useful `bq` Commands

List tables:

```bash
bq ls project-5fbc8bf7-2dd6-4f0a-a5f:hospital_control
```

Show table:

```bash
bq show \
  project-5fbc8bf7-2dd6-4f0a-a5f:hospital_control.pipeline_run
```

Run SQL:

```bash
bq query --use_legacy_sql=false "SELECT 1"
```

Run SQL file:

```bash
bq query --use_legacy_sql=false < file.sql
```

---

# 20. Useful `gcloud` Commands

```bash
gcloud config list
```

```bash
gcloud config get-value project
```

```bash
gcloud config get-value account
```

```bash
gcloud config get-value compute/region
```

```bash
gcloud projects describe project-5fbc8bf7-2dd6-4f0a-a5f
```

---

# 21. Composer

Check environments:

```bash
gcloud composer environments list \
  --locations=asia-south1
```

Composer API:

```bash
gcloud services list \
  --enabled \
  --filter="config.name=composer.googleapis.com"
```

For now:

```text
Composer environment = NOT required for raw-ingestion testing
```

We will bring Composer in when we have the pipeline stages ready to orchestrate.

---

# 22. Repository Structure

```text
scripts/
├── setup/
│   ├── 01_check_prerequisites.sh
│   ├── 02_configure_gcp.sh
│   ├── 03_enable_apis.sh
│   ├── 04_create_storage.sh
│   ├── 05_create_datasets.sh
│   ├── 06_create_control_tables.sh
│   ├── 07_seed_file_ingestion_config.sh
│   └── 08_validate_control_layer.sh
│
├── create_bronze_tables.sh
├── inspect_practice_csvs.sh
├── upload_raw_files.sh
└── validate_control_layer.sh
```

SQL:

```text
sql/
├── bronze/
│   ├── 01_departments.sql
│   ├── 02_doctors.sql
│   ├── 03_registrations.sql
│   ├── 04_encounters.sql
│   ├── 05_admissions.sql
│   ├── 06_discharges.sql
│   └── 07_billing.sql
│
└── control/
    ├── ddl/
    ├── seed/
    └── validation/
```

---

# 23. Full Fresh Setup

If another developer clones the repository:

```bash
git clone <REPO_URL>
cd gcp-hospital-medallion
```

Create environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Then:

```bash
./scripts/setup/01_check_prerequisites.sh
./scripts/setup/02_configure_gcp.sh
./scripts/setup/03_enable_apis.sh
./scripts/setup/04_create_storage.sh
./scripts/setup/05_create_datasets.sh
./scripts/setup/06_create_control_tables.sh
./scripts/setup/07_seed_file_ingestion_config.sh
./scripts/setup/08_validate_control_layer.sh
```

Then inspect:

```bash
./scripts/inspect_practice_csvs.sh
```

Then run daily ingestion:

```bash
./scripts/upload_raw_files.sh \
  --processing-date YYYY-MM-DD
```

---

## The one-line mental model

```text
SETUP → GCS → CONTROL → VALIDATE → INGEST → BRONZE → SILVER → GOLD → COMPOSER
```

And for the current phase:

```text
CSV → T-1 validation → GCS → audit/control → SUCCESS/FAILED
```
