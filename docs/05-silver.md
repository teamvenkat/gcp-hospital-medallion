# Silver Layer

## Objective

Create trusted, clean, reusable business data.

## Flow

```text
Bronze
 ↓
type standardisation
 ↓
null handling
 ↓
deduplication
 ↓
referential validation
 ↓
business rules
 ↓
Silver
```

## Planned examples

```text
silver.registrations
silver.encounters
silver.admissions
silver.discharges
silver.billing
```

## Key checks

- Primary/business key uniqueness
- Valid dates
- Valid statuses
- Referential integrity
- Duplicate resolution
- Standardised values

## Next implementation

Silver should be built only after Bronze is queryable and reconciled.
