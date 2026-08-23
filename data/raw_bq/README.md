# Hospital Practice Source Data

Generated for the hospital near-real-time pipeline project.

## Normal source files

All normal files are in the root of this package. Filenames use:
`<entity>_YYYYMMDDHHMMSS.csv`

The source timestamps intentionally differ between files.

Entities:
- departments
- doctors
- registrations
- encounters
- admissions
- discharges
- billing

## Failure test files

`test_failure_files/` contains deliberately invalid examples:
- a T-2 source-date file
- a schema-change file

These should NOT be mixed into the normal daily input when first testing the happy path.

## Important

This dataset is separate from the existing dbt-learning dataset.
