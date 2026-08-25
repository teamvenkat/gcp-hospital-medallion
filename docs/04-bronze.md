# Bronze Layer

## Objective

Create queryable structured representations of Raw data while preserving source meaning.

## Flow

```text
GCS Raw
   ↓
Dataproc / PySpark
   ↓
BigQuery Bronze
```

## Rules

- Preserve source values.
- Apply explicit schemas.
- Add ingestion metadata.
- Avoid business transformations.
- Reconcile source and Bronze counts.

## Planned metadata

```text
source_file_name
source_file_timestamp
ingestion_run_id
ingestion_timestamp
source_system
record_hash
```

## Tables

Expected source-aligned Bronze tables:

```text
registrations
encounters
admissions
discharges
billing
departments
doctors
```

## Next implementation

1. Define Bronze schemas.
2. Read GCS Raw.
3. Write BigQuery.
4. Add metadata.
5. Add reconciliation.
6. Add Bronze DQ.
