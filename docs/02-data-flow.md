# Data Flow

## End-to-end

```text
Source
  ↓
Local / SFTP / DB extract
  ↓
Raw ingestion
  ↓
GCS Raw
  ↓
Bronze
  ↓
Silver
  ↓
Gold
  ↓
Looker Studio
```

## Operational flow

```text
File
 ↓
filename/date validation
 ↓
CSV validation
 ↓
checksum/idempotency
 ↓
GCS upload
 ↓
control logging
 ↓
processed / skipped / failed / non_processed
```
