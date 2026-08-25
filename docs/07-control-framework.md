# Control Framework

## Tables

```text
file_ingestion_config
file_ingestion_log
pipeline_run
validation_error_log
rejected_record_log
record_reconciliation
dq_execution_log
```

## Responsibilities

```text
file_ingestion_config → rules
file_ingestion_log    → file attempts
pipeline_run          → run-level state
validation_error_log  → validation failures
rejected_record_log   → rejected records
record_reconciliation → count/reconciliation results
dq_execution_log      → DQ execution
```

## State model

```text
current run
    +
historical source-date attempts
    ↓
cumulative mandatory state
    ↓
SUCCESS / FAILED
```

Master data failures are warnings only.
