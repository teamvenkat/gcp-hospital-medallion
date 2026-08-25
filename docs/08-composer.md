# Cloud Composer / Airflow

## Target DAG

```text
START
  ↓
Raw ingestion check
  ↓
Raw completeness
  ↓
Bronze
  ↓
Bronze DQ
  ↓
Silver
  ↓
Silver DQ
  ↓
Gold
  ↓
Gold DQ
  ↓
Reconciliation
  ↓
SUCCESS
```

## Failure behavior

```text
mandatory task failure
        ↓
Airflow task failure
        ↓
downstream tasks blocked
```

## Planned scheduling

Daily processing is expected to use the source/processing-date convention already established in Raw.

## Implementation order

1. Build layers independently.
2. Create individual tasks.
3. Add dependencies.
4. Add retries.
5. Add alerts.
6. Add scheduling.
