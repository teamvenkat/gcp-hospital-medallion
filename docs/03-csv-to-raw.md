# Hospital Medallion — CSV → GCS Raw

Practical cheatsheet — commands, folders, checks, retry/backfill, control tables, and logs.

## 1. Start

```bash
cd ~/Documents/gcp/gcp-hospital-medallion
source .venv/bin/activate
gcloud config get-value project
bq ls project-5fbc8bf7-2dd6-4f0a-a5f:hospital_control
```

## 2. Local file lifecycle

```text
data/raw_bq/
├── incoming/
├── processed/<processing-date>/
├── skipped/<processing-date>/
├── failed/<processing-date>/
└── non_processed/<processing-date>/
```

- `incoming/` → normal input
- `processed/` → successful upload
- `skipped/` → same filename + checksum already processed
- `failed/` → eligible file failed; retry candidate
- `non_processed/` → not eligible for this processing date; backfill candidate

## 3. Filename / source date

```text
<entity>_YYYYMMDDHHMMSS.csv
```

Example:

```text
admissions_20260821184641.csv
```

```text
Processing date 2026-08-22
        ↓
Expected source date 2026-08-21
```

**Keep filenames unchanged when moving lifecycle files.**

The filename timestamp is used to determine source date.

## 4. Entities

### Master — warning only

```text
departments
doctors
```

### Transaction — mandatory

```text
registrations
encounters
admissions
discharges
billing
```

## 5. Check ingestion configuration

```bash
bq query --use_legacy_sql=false '
SELECT entity_name, mandatory, filename_prefix, file_format,
       target_bronze_table, primary_key_column,
       expected_file_date_rule, retry_enabled, max_retries, is_active
FROM `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.file_ingestion_config`
ORDER BY entity_name;
'
```

Expected mandatory classification:

```text
admissions       true
billing          true
departments      false
discharges       true
doctors          false
encounters       true
registrations    true
```

## 6. Put files into incoming

```bash
cp /path/to/*.csv data/raw_bq/incoming/

ls -lh data/raw_bq/incoming/

find data/raw_bq/incoming \
  -maxdepth 1 \
  -type f \
  -name '*.csv' \
  -print
```

## 7. Run ingestion

```bash
./scripts/upload_raw_files.sh --processing-date 2026-08-22
```

Example:

```bash
./scripts/upload_raw_files.sh --processing-date 2026-08-24
```

The script derives:

```text
expected source date = processing date - 1 day
```

It scans:

```text
incoming/
failed/<processing-date ± 7 days>/
non_processed/<processing-date ± 7 days>/
```

## 8. Run summary

```text
Files discovered
    Eligible files processed in this invocation

Incoming eligible
    Eligible files found in incoming/

Failed retry
    Eligible files found in failed/<±7 days>/

Non-processed retry
    Eligible files found in non_processed/<±7 days>/

Files uploaded
    SUCCESS in this invocation

Files skipped
    Already successfully processed

Files failed
    Failures in this invocation

Mandatory missing
    Unresolved transaction entities

Mandatory failed
    Unresolved transaction failures

Mandatory satisfied
    Cumulative satisfied mandatory entities / total mandatory

Master warnings
    Missing/failed departments or doctors

Records in uploaded files
    Rows in SUCCESS files

Run status
    SUCCESS or FAILED
```

## 9. Lifecycle

### SUCCESS

```text
incoming/file.csv
        ↓
GCS Raw
        ↓
processed/<processing-date>/file.csv
```

### SKIPPED

```text
incoming/file.csv
        ↓
same filename + same checksum already processed
        ↓
skipped/<processing-date>/file.csv
```

### FAILED

```text
incoming/file.csv
        ↓
validation/upload failure
        ↓
failed/<processing-date>/file.csv
```

### NOT ELIGIBLE

```text
incoming/file.csv
        ↓
source date does not match current expected date
        ↓
non_processed/<processing-date>/file.csv
```

## 10. Retry / backfill

### Retry failed files

Correct the file while it is under:

```text
data/raw_bq/failed/<date>/
```

Then run:

```bash
./scripts/upload_raw_files.sh --processing-date 2026-08-24
```

### Backfill non-processed files

Correct/place the file under:

```text
data/raw_bq/non_processed/<date>/
```

Then run:

```bash
./scripts/upload_raw_files.sh --processing-date 2026-08-24
```

Important:

- Do not manually move retry files to `incoming/`.
- Eligible files in `failed/` and `non_processed/` are automatically discovered within the ±7 processing-date scan window.
- Successful retry moves to `processed/<current-processing-date>/`.

## 11. Cumulative mandatory behavior

Mandatory state is cumulative for the source date.

Example:

```text
Run 1
5 mandatory entities
3 SUCCESS
1 FAILED
1 MISSING

→ FAILED
```

Later:

```text
Run 2
Previously successful: 3
Previously failed:    1
Previously missing:   1

Failed file succeeds
Missing file still missing

→ 4/5
→ FAILED
```

Later:

```text
Run 3
Missing file succeeds

→ 5/5
→ SUCCESS
```

A previous:

```text
SUCCESS
```

or:

```text
SKIPPED / ALREADY_PROCESSED
```

satisfies that mandatory entity for the source date.

Master failures/missing files:

```text
WARNING only
```

They do not fail the pipeline.

## 12. Check local application logs

```bash
ls -lh logs/ingestion/
```

Current day's log:

```bash
cat logs/ingestion/ingestion_$(date +%Y%m%d).log
```

Last 100 lines:

```bash
tail -n 100 logs/ingestion/ingestion_$(date +%Y%m%d).log
```

Errors/warnings/retries:

```bash
grep -E 'ERROR|WARNING|FAILED|SUCCESS|retry' \
  logs/ingestion/ingestion_$(date +%Y%m%d).log
```

Log file pattern:

```text
logs/ingestion/ingestion_YYYYMMDD.log
```

## 13. GCS checks

```bash
gcloud storage ls gs://gcp-hospital-medallion-data/raw_bq/
```

Recursive:

```bash
gcloud storage ls -r \
  gs://gcp-hospital-medallion-data/raw_bq/
```

First 100 entries:

```bash
gcloud storage ls -r \
  gs://gcp-hospital-medallion-data/raw_bq/ | head -100
```

## 14. Control tables — quick inspection

### pipeline_run

```bash
bq query --use_legacy_sql=false '
SELECT *
FROM `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.pipeline_run`
ORDER BY end_time DESC
LIMIT 50;
'
```

### file_ingestion_config

```bash
bq query --use_legacy_sql=false '
SELECT *
FROM `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.file_ingestion_config`
ORDER BY entity_name;
'
```

### file_ingestion_log

```bash
bq query --use_legacy_sql=false '
SELECT *
FROM `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.file_ingestion_log`
ORDER BY created_at DESC
LIMIT 50;
'
```

### validation_error_log

```bash
bq query --use_legacy_sql=false '
SELECT *
FROM `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.validation_error_log`
ORDER BY error_timestamp DESC
LIMIT 50;
'
```

### rejected_record_log

```bash
bq query --use_legacy_sql=false '
SELECT *
FROM `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.rejected_record_log`
ORDER BY rejected_at DESC
LIMIT 50;
'
```

### record_reconciliation

```bash
bq query --use_legacy_sql=false '
SELECT *
FROM `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.record_reconciliation`
ORDER BY created_at DESC
LIMIT 50;
'
```

### dq_execution_log

```bash
bq query --use_legacy_sql=false '
SELECT *
FROM `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.dq_execution_log`
ORDER BY created_at DESC
LIMIT 50;
'
```

## 15. Useful control queries

### Latest history for one file

```bash
bq query --use_legacy_sql=false '
SELECT file_name, entity_name, expected_source_date,
       file_checksum, validation_status, processing_status,
       attempt_number, retryable, error_code, error_message, created_at
FROM `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.file_ingestion_log`
WHERE file_name = "admissions_20260821184641.csv"
ORDER BY created_at DESC;
'
```

### One source date

```bash
bq query --use_legacy_sql=false '
SELECT entity_name, processing_status, file_name,
       expected_source_date, attempt_number, error_code, created_at
FROM `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.file_ingestion_log`
WHERE expected_source_date = "2026-08-21"
ORDER BY entity_name, created_at DESC;
'
```

### Recent failures

```bash
bq query --use_legacy_sql=false '
SELECT file_name, entity_name, error_code, error_message,
       retryable, attempt_number, created_at
FROM `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.file_ingestion_log`
WHERE processing_status = "FAILED"
ORDER BY created_at DESC
LIMIT 50;
'
```

### Recent pipeline runs

```bash
bq query --use_legacy_sql=false '
SELECT run_id, run_date, expected_source_date, status,
       total_files_expected, total_files_received,
       total_files_processed, total_files_failed,
       total_records_received, total_records_rejected,
       start_time, end_time
FROM `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.pipeline_run`
ORDER BY end_time DESC
LIMIT 20;
'
```

## 16. Validate Python before running

```bash
python -m py_compile \
  src/hospital_pipeline/ingestion/run_ingestion.py
```

## 17. Development reset — destructive

```bash
./scripts/setup/00_reset_development.sh
```

Use only when intentionally resetting development.

Current reset behavior removes:

```text
GCS development bucket
BigQuery hospital_control dataset
```

while preserving the project, Bronze dataset, Composer, and local files according to the current reset script.

## 18. Main scripts

```text
scripts/
├── setup/
│   ├── 01_check_prerequisites.sh
│   ├── 02_configure_gcp.sh
│   ├── 03_enable_apis.sh
│   ├── 04_create_storage.sh
│   └── 05_create_datasets.sh
├── create_control_tables.sh
├── create_bronze_tables.sh
├── seed_file_ingestion_config.sh
├── validate_control_layer.sh
├── upload_raw_files.sh
└── inspect_practice_csvs.sh
```

## 19. Troubleshooting

### NO ELIGIBLE CSV

```text
Check:
1. source date in filename
2. incoming/
3. failed/<±7 days>/
4. non_processed/<±7 days>/
```

### MANDATORY MISSING

```text
Check file_ingestion_log for expected_source_date.

Verify that the entity has a historical:
UPLOADED
or
SKIPPED
state.
```

### FILE FAILED

```text
1. Read terminal error.
2. Inspect validation_error_log.
3. Correct the file.
4. Leave it in failed/<date>/.
5. Run the ingestion command again.
```

### ALREADY_PROCESSED

```text
Same filename + same SHA-256 checksum
→ SKIPPED
```

### SAME CONTENT, DIFFERENT FILENAME

```text
Different filename + same checksum
→ allowed
```

The checksum is not a global content-duplicate rejection.

### GCS ERROR

```text
1. Inspect local ingestion log.
2. Check bucket/access.
3. Check GCS retry messages.
4. Retry the ingestion if the file remains failed.
```

## 20. End-to-end command sequence

```bash
cd ~/Documents/gcp/gcp-hospital-medallion
source .venv/bin/activate

python -m py_compile \
  src/hospital_pipeline/ingestion/run_ingestion.py

ls -lh data/raw_bq/incoming/

./scripts/upload_raw_files.sh \
  --processing-date 2026-08-22

tail -n 100 \
  logs/ingestion/ingestion_$(date +%Y%m%d).log
```

Check latest pipeline run:

```bash
bq query --use_legacy_sql=false '
SELECT run_id, run_date, status,
       total_files_expected, total_files_received,
       total_files_processed, total_files_failed
FROM `project-5fbc8bf7-2dd6-4f0a-a5f.hospital_control.pipeline_run`
ORDER BY end_time DESC
LIMIT 10;
'
```

## 21. Current Raw-layer contract

```text
CSV source
   ↓
data/raw_bq/incoming/
   ↓
filename/date/config/CSV/checksum validation
   ↓
GCS Raw
gs://gcp-hospital-medallion-data/raw_bq/
   ↓
processed/
skipped/
failed/
non_processed/

Control layer:
   pipeline_run
   file_ingestion_config
   file_ingestion_log
   validation_error_log
   rejected_record_log
   record_reconciliation
   dq_execution_log

Application logs:
   logs/ingestion/ingestion_YYYYMMDD.log

Next layer:
   GCS Raw → Bronze → Silver → Gold
```
