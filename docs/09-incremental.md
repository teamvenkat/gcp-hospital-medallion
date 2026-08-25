# Incremental Processing

## Current Raw convention

```text
processing_date
      ↓
expected source date = T-1
```

## Future watermark approach

```text
last successful watermark
       ↓
read new/changed data
       ↓
process
       ↓
validate
       ↓
advance watermark
```

Potential watermark columns:

```text
created_at
updated_at
source_file_timestamp
```

The implementation should keep Raw replayable even when downstream processing is incremental.
