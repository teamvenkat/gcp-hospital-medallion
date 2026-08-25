# Gold Layer

## Objective

Create reporting-ready analytical models.

## Dimensions

```text
dim_date
dim_patient
dim_doctor
dim_department
```

## Facts

```text
fact_registrations
fact_encounters
fact_admissions
fact_discharges
fact_billing
```

## KPI marts

```text
hospital_daily_kpi
department_daily_kpi
doctor_daily_kpi
billing_daily_kpi
```

## Flow

```text
Silver
 ↓
dim/fact modelling
 ↓
KPI aggregation
 ↓
Gold
 ↓
Looker Studio
```
