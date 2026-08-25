# CI/CD

## Target flow

```text
Developer
 ↓
GitHub
 ↓
Jenkins
 ↓
tests / validation / build
 ↓
artifact
 ↓
Harness
 ↓
GCP deployment
```

## Jenkins

Planned checks:

```text
Python validation
unit tests
integration tests
build/package
```

## Harness

Planned responsibilities:

```text
deployment
environment promotion
release controls
```

CI/CD is a later phase after the pipeline is functionally complete.
