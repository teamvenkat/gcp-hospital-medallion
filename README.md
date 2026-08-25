# GCP Hospital Medallion

Enterprise-style hospital data platform built on Google Cloud using the **Medallion Architecture**:

**Raw → Bronze → Silver → Gold → Looker Studio**

The project is designed as a practical production-style implementation using a hospital dataset, while keeping the implementation simple enough to build and demonstrate end-to-end.

---

## 1. Project Objective

Build a scalable hospital data platform on GCP that demonstrates:

- Source file ingestion
- Raw data landing
- File validation and control framework
- Bronze data storage
- Silver cleansing and standardisation
- Gold dimensional / analytical models
- Data quality and reconciliation
- Workflow orchestration with Cloud Composer / Airflow
- Infrastructure automation
- CI/CD
- Analytical reporting with Looker Studio

The emphasis is on **working deliverables and a realistic end-to-end flow**, rather than implementing every enterprise technology immediately.

---

## 2. High-Level Architecture

```text
                    ┌─────────────────────────────┐
                    │       Source Systems        │
                    │                             │
                    │ CSV / SFTP / DB Extracts    │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │        Local / Landing      │
                    │       incoming/ files       │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │      RAW INGESTION          │
                    │                             │
                    │ filename/date validation    │
                    │ CSV validation              │
                    │ checksum / idempotency      │
                    │ retry / backfill            │
                    │ control tables              │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
              ┌────────────────────────────────────────────┐
              │                  GCS RAW                   │
              │        gs://.../raw_bq/                    │
              └────────────────────┬───────────────────────┘
                                   │
                                   ▼
              ┌────────────────────────────────────────────┐
              │                 BRONZE                     │
              │       BigQuery / raw structured data       │
              │                                            │
              │ schema-aligned                             │
              │ minimally transformed                      │
              │ ingestion metadata                         │
              └────────────────────┬───────────────────────┘
                                   │
                                   ▼
              ┌────────────────────────────────────────────┐
              │                  SILVER                    │
              │                                            │
              │ cleansing                                  │
              │ standardisation                            │
              │ deduplication                              │
              │ joins / business rules                     │
              │ data quality                               │
              └────────────────────┬───────────────────────┘
                                   │
                                   ▼
              ┌────────────────────────────────────────────┐
              │                   GOLD                     │
              │                                            │
              │ dimensional / analytical models            │
              │ hospital KPIs                              │
              │ reporting-ready tables                     │
              └────────────────────┬───────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │       Looker Studio         │
                    │                             │
                    │ dashboards / KPIs / trends  │
                    └─────────────────────────────┘
```

Detailed architecture:
- [Architecture](docs/01-architecture.md)
- [Data flow](docs/02-data-flow.md)

---

## 3. Source Data

The current practice dataset contains hospital-style CSV entities:

```text
registrations
encounters
admissions
discharges
billing
departments
doctors
```

### Entity classification

| Entity | Type | Mandatory |
|---|---|---:|
| registrations | Transaction | Yes |
| encounters | Transaction | Yes |
| admissions | Transaction | Yes |
| discharges | Transaction | Yes |
| billing | Transaction | Yes |
| departments | Master | Warning only |
| doctors | Master | Warning only |

The configuration table is the source of truth for these rules.

---

## 4. Technology Stack

| Area | Technology |
|---|---|
| Cloud | Google Cloud Platform |
| Object storage / Raw | Google Cloud Storage |
| Processing | Dataproc / PySpark |
| Warehouse | BigQuery |
| Orchestration | Cloud Composer / Airflow |
| Infrastructure | Terraform |
| CI | Jenkins |
| CD | Harness |
| IAM / governance | Saviynt |
| Reporting | Looker Studio |
| Language | Python / PySpark |
| Version control | GitHub |

Not every component is introduced at once. The project is built incrementally.

---

# 5. Medallion Layers

## Raw

Purpose:

- Preserve source files
- Validate files
- Track ingestion
- Provide replay/backfill capability
- Maintain operational audit history

Current local lifecycle:

```text
data/raw_bq/
├── incoming/
├── processed/<processing-date>/
├── skipped/<processing-date>/
├── failed/<processing-date>/
└── non_processed/<processing-date>/
```

GCS:

```text
gs://gcp-hospital-medallion-data/raw_bq/
```

Detailed implementation:

- [CSV → GCS Raw](docs/03-csv-to-raw.md)

---

## Bronze

Purpose:

- Convert landed raw data into queryable structured data
- Preserve source-level meaning
- Add ingestion metadata
- Avoid business transformations

Planned pattern:

```text
GCS Raw
   ↓
Bronze ingestion
   ↓
BigQuery hospital_bronze_ven
```

Detailed implementation:

- [Bronze Layer](docs/04-bronze.md)

---

## Silver

Purpose:

- Clean data
- Standardise types
- Remove / resolve duplicates
- Apply business rules
- Create trusted reusable datasets

Typical flow:

```text
Bronze
  ↓
Data cleansing
  ↓
Standardisation
  ↓
Deduplication
  ↓
Business validation
  ↓
Silver tables
```

Detailed implementation:

- [Silver Layer](docs/05-silver.md)

---

## Gold

Purpose:

Create reporting-ready analytical models.

Examples:

```text
fact_admissions
fact_encounters
fact_billing
fact_discharges

dim_patient
dim_doctor
dim_department
dim_date
dim_admission_type
```

Potential KPI marts:

```text
hospital_daily_kpi
department_daily_kpi
doctor_activity_kpi
billing_daily_kpi
```

Detailed implementation:

- [Gold Layer](docs/06-gold.md)

---

# 6. Raw Ingestion Framework

The current ingestion framework supports:

```text
T-1 source-date validation
CSV validation
filename validation
configuration-driven entity rules
SHA-256 checksum
same-file idempotency
GCS retry
file lifecycle folders
failed-file retry
non-processed backfill
±7-day retry scan
cumulative mandatory state
master warning-only behavior
control-table audit
local application logging
```

### Mandatory business rule

```text
5 transaction entities
        ↓
all must eventually succeed
        ↓
processing date = SUCCESS
```

Master files:

```text
departments / doctors
        ↓
missing or failed
        ↓
WARNING
        ↓
pipeline continues
```

A failed transaction can be corrected and retried later. Once the entity becomes successful for that source date, the cumulative processing state can become `SUCCESS`.

Detailed implementation:

- [CSV → Raw ingestion](docs/03-csv-to-raw.md)

---

# 7. Control Layer

Current BigQuery control dataset:

```text
hospital_control
```

Tables:

```text
file_ingestion_config
file_ingestion_log
pipeline_run
validation_error_log
rejected_record_log
record_reconciliation
dq_execution_log
```

### Control flow

```text
Ingestion
   │
   ├── file_ingestion_log
   ├── validation_error_log
   └── pipeline_run
             │
             ▼
       source-date state
             │
             ▼
        SUCCESS / FAILED
```

Detailed implementation:

- [Control Framework](docs/07-control-framework.md)

---

# 8. Retry and Backfill Design

The design distinguishes between:

### Technical retry

Example:

```text
GCS upload attempt 1
       ↓
temporary error
       ↓
attempt 2
       ↓
attempt 3
```

Controlled through:

```text
retry_enabled
max_retries
```

### File retry

```text
failed/<date>/
        ↓
next ingestion run
        ↓
successful?
    ├── yes → processed/
    └── no  → failed/
```

### Backfill

```text
non_processed/<date>/
        ↓
correct processing date
        ↓
eligible scan
        ↓
GCS Raw
```

Detailed implementation:

- [CSV → Raw ingestion](docs/03-csv-to-raw.md)

---

# 9. Bronze Processing Plan

Once Raw is stable:

```text
GCS Raw
   ↓
Composer DAG
   ↓
Spark / Dataproc
   ↓
BigQuery Bronze
```

Bronze responsibilities:

- Read raw data
- Apply schema
- Preserve source values
- Add metadata
- Record ingestion batch
- Reconcile source row count vs Bronze row count

Suggested metadata:

```text
source_file_name
source_file_timestamp
ingestion_run_id
ingestion_timestamp
source_system
record_hash
```

Detailed implementation:

- [Bronze Layer](docs/04-bronze.md)

---

# 10. Silver Processing Plan

Silver will contain trusted business data.

Example:

```text
bronze.registrations
        +
bronze.encounters
        ↓
silver.patient_encounters
```

Typical transformations:

```text
type conversion
null handling
standardisation
deduplication
referential checks
business rules
derived fields
```

Example:

```text
Bronze admission
    ↓
validate registration
    ↓
validate encounter
    ↓
standardise admission_type
    ↓
standardise ward
    ↓
Silver admission
```

Detailed implementation:

- [Silver Layer](docs/05-silver.md)

---

# 11. Gold Modeling Plan

Gold is designed for analytics rather than operational ingestion.

### Dimensions

```text
dim_date
dim_patient
dim_doctor
dim_department
```

### Facts

```text
fact_registrations
fact_encounters
fact_admissions
fact_discharges
fact_billing
```

### KPI marts

```text
hospital_daily_kpi
department_daily_kpi
doctor_daily_kpi
billing_daily_kpi
```

Detailed implementation:

- [Gold Layer](docs/06-gold.md)

---

# 12. Data Quality

Data quality exists at multiple stages.

```text
RAW
 ↓
file-level validation
 ↓
BRONZE
 ↓
record/schema/reconciliation checks
 ↓
SILVER
 ↓
business/data-quality checks
 ↓
GOLD
 ↓
KPI/reconciliation checks
```

Examples:

### File level

```text
filename
source date
CSV structure
empty headers
checksum
mandatory files
```

### Bronze

```text
row count
schema
nulls
duplicates
record counts
```

### Silver

```text
referential integrity
business rules
valid status values
valid dates
duplicate business keys
```

### Gold

```text
fact/dimension consistency
KPI reconciliation
daily totals
department totals
billing totals
```

Detailed implementation:

- [Control Framework](docs/07-control-framework.md)

---

# 13. Cloud Composer / Airflow

Composer becomes the orchestration layer after the individual stages are working independently.

Target DAG:

```text
                    START
                      │
                      ▼
              Raw ingestion check
                      │
                      ▼
              Raw completeness
                      │
                      ▼
              Bronze processing
                      │
                      ▼
               Bronze DQ
                      │
                      ▼
              Silver processing
                      │
                      ▼
                Silver DQ
                      │
                      ▼
               Gold build
                      │
                      ▼
                 Gold DQ
                      │
                      ▼
              Reconciliation
                      │
                      ▼
                 SUCCESS
```

Failure path:

```text
Any mandatory stage failure
        ↓
Airflow task failure
        ↓
downstream tasks blocked
        ↓
alert / operational handling
```

Detailed implementation:

- [Composer / Airflow](docs/08-composer.md)

---

# 14. Incremental Processing

The platform is intended to support incremental ingestion.

Current Raw approach:

```text
processing date
      ↓
expected source date = T-1
```

Future Bronze/Silver/Gold approach:

```text
watermark
   ↓
read only new/changed data
   ↓
process
   ↓
advance watermark
```

Potential watermark columns:

```text
created_at
updated_at
source_file_timestamp
```

Detailed implementation:

- [Incremental Processing](docs/09-incremental.md)

---

# 15. Infrastructure as Code

Terraform will eventually manage:

```text
GCS buckets
BigQuery datasets
BigQuery tables
service accounts
IAM
Composer
Dataproc
networking where required
```

Target:

```text
Terraform
   ↓
GCP infrastructure
```

Detailed implementation:

- [Terraform / Infrastructure](docs/10-infrastructure.md)

---

# 16. CI/CD

Planned delivery flow:

```text
Developer
    ↓
GitHub
    ↓
Jenkins CI
    │
    ├── lint
    ├── unit tests
    ├── integration checks
    └── package/build
    ↓
Artifact
    ↓
Harness CD
    ↓
GCP deployment
```

The initial implementation will remain simple; CI/CD is a later phase.

Detailed implementation:

- [CI/CD](docs/11-cicd.md)

---

# 17. IAM / Governance

Planned enterprise governance:

```text
Users / service accounts
        ↓
IAM
        ↓
GCP resources

Data access / governance
        ↓
Saviynt
```

Principles:

- Least privilege
- Service-account based workloads
- Environment separation
- Controlled dataset access
- Auditability

Detailed implementation:

- [Infrastructure & Governance](docs/10-infrastructure.md)

---

# 18. Looker Studio

Final reporting layer:

```text
BigQuery Gold
      ↓
Looker Studio
      ↓
Dashboards
```

Potential dashboards:

### Hospital Overview

```text
Total registrations
Total encounters
Admissions
Discharges
Revenue / billing
Occupancy-style metrics
```

### Department Dashboard

```text
Admissions by department
Encounters by department
Doctor activity
Billing by department
Daily trends
```

### Doctor Dashboard

```text
Doctor encounters
Admissions
Discharges
Department activity
```

### Financial Dashboard

```text
Daily billing
Billing by department
Billing trends
```

Detailed implementation:

- [Looker Studio](docs/12-looker-studio.md)

---

# 19. Development Roadmap

## Phase 0 — Foundation

- [x] GitHub repository
- [x] Python project structure
- [x] GCP project
- [x] GCS
- [x] BigQuery
- [x] Control dataset
- [x] Configuration framework

## Phase 1 — Raw ingestion

- [x] Local incoming lifecycle
- [x] Filename validation
- [x] T-1 validation
- [x] CSV validation
- [x] SHA-256
- [x] GCS upload
- [x] GCS retry
- [x] Processed/skipped/failed/non_processed lifecycle
- [x] Retry scan
- [x] Backfill support
- [x] Cumulative mandatory state
- [x] Control logging
- [x] Local application logging

## Phase 2 — Bronze

- [ ] Bronze schema
- [ ] Raw → Bronze ingestion
- [ ] Spark processing
- [ ] Incremental processing
- [ ] Bronze reconciliation
- [ ] Bronze DQ

## Phase 3 — Silver

- [ ] Standardisation
- [ ] Deduplication
- [ ] Business rules
- [ ] Referential integrity
- [ ] Silver DQ

## Phase 4 — Gold

- [ ] Dimensions
- [ ] Facts
- [ ] KPI marts
- [ ] Gold reconciliation
- [ ] Performance optimisation

## Phase 5 — Composer

- [ ] Composer environment
- [ ] DAG structure
- [ ] Bronze task
- [ ] Silver task
- [ ] Gold task
- [ ] DQ tasks
- [ ] Failure handling
- [ ] Scheduling

## Phase 6 — Infrastructure

- [ ] Terraform
- [ ] IAM
- [ ] Service accounts
- [ ] Environment configuration
- [ ] Composer infrastructure

## Phase 7 — CI/CD

- [ ] Jenkins CI
- [ ] Tests
- [ ] Build
- [ ] Harness CD
- [ ] Deployment pipeline

## Phase 8 — Reporting

- [ ] Looker Studio connection
- [ ] Hospital dashboard
- [ ] Department dashboard
- [ ] Doctor dashboard
- [ ] Billing dashboard
- [ ] KPI validation

---

# 20. Final Target Architecture

```text
                           SOURCE SYSTEMS
                                │
                    ┌───────────┴───────────┐
                    │                       │
                  SFTP                    DB
                    │                       │
                    └───────────┬───────────┘
                                │
                                ▼
                         RAW INGESTION
                                │
                    ┌───────────┴───────────┐
                    │                       │
              Validation               Control
                    │                       │
                    ▼                       ▼
                 GCS RAW              BigQuery Control
                    │
                    ▼
                 BRONZE
              BigQuery / Spark
                    │
                    ▼
                 SILVER
              BigQuery / Spark
                    │
                    ▼
                  GOLD
                 BigQuery
                    │
                    ▼
              LOOKER STUDIO


ORCHESTRATION

                 Cloud Composer
                      │
       ┌──────────────┼──────────────┐
       ▼              ▼              ▼
     Bronze         Silver          Gold
       │              │              │
       └──────────────┴──────────────┘
                      │
                     DQ
                      │
                 Reconciliation


ENGINEERING

GitHub
  ↓
Jenkins
  ↓
Harness
  ↓
GCP

Terraform
  ↓
Infrastructure

Saviynt / IAM
  ↓
Access Governance
```

---

# 21. Documentation Index

| Document | Purpose |
|---|---|
| [Architecture](docs/01-architecture.md) | Overall platform architecture |
| [Data Flow](docs/02-data-flow.md) | End-to-end movement of data |
| [CSV → Raw](docs/03-csv-to-raw.md) | Detailed current Raw ingestion implementation |
| [Bronze](docs/04-bronze.md) | Bronze implementation plan |
| [Silver](docs/05-silver.md) | Silver implementation plan |
| [Gold](docs/06-gold.md) | Gold modeling and KPI plan |
| [Control Framework](docs/07-control-framework.md) | Control tables, DQ, reconciliation |
| [Composer](docs/08-composer.md) | Airflow / Composer orchestration |
| [Incremental](docs/09-incremental.md) | Watermarks and incremental processing |
| [Infrastructure](docs/10-infrastructure.md) | Terraform, IAM and GCP infrastructure |
| [CI/CD](docs/11-cicd.md) | Jenkins and Harness |
| [Looker Studio](docs/12-looker-studio.md) | Reporting and dashboard plan |

---

## 22. Build Order

The project should be implemented in this order:

```text
1. Foundation
       ↓
2. Raw ingestion
       ↓
3. Bronze
       ↓
4. Silver
       ↓
5. Gold
       ↓
6. Data quality / reconciliation
       ↓
7. Composer orchestration
       ↓
8. Terraform / infrastructure
       ↓
9. Jenkins / Harness
       ↓
10. Looker Studio
```

**Do not jump directly to Composer or Looker Studio.**

Each layer should first work independently and then be orchestrated.

---

## 23. Current Status

```text
Foundation       ██████████  Complete
Raw              ██████████  Complete
Bronze           ░░░░░░░░░░  Next
Silver           ░░░░░░░░░░  Planned
Gold             ░░░░░░░░░░  Planned
DQ/Reconciliation░░░░░░░░░░  Planned
Composer         ░░░░░░░░░░  Planned
Terraform        ░░░░░░░░░░  Planned
CI/CD            ░░░░░░░░░░  Planned
Looker Studio    ░░░░░░░░░░  Planned
```

**Next implementation target: Bronze.**
