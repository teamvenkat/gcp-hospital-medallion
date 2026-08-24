#!/usr/bin/env python3

"""
Hospital raw-file ingestion framework - audit v5.

Pipeline status contract:
    SUCCESS
        All mandatory entities have a valid T-1 file and no mandatory
        file-level failure exists.

    FAILED
        Any mandatory file is missing OR any mandatory file fails validation
        or landing.

    PARTIAL_FAILURE
        Only non-mandatory files have failures.

Other behavior:
- T-1 validation
- CSV validation
- SHA-256 duplicate protection
- GCS upload with configured retry
- Mandatory-file completeness
- Append-only pipeline_run
- file_ingestion_log and validation_error_log
- No Bronze processing
"""

import argparse
import csv
import hashlib
import re
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from google.cloud import bigquery, storage

PROJECT_ID = "project-5fbc8bf7-2dd6-4f0a-a5f"
CONTROL_DATASET = "hospital_control"
CONFIG_TABLE = "file_ingestion_config"
FILE_LOG_TABLE = "file_ingestion_log"
PIPELINE_RUN_TABLE = "pipeline_run"
VALIDATION_ERROR_TABLE = "validation_error_log"

GCS_BUCKET = "gcp-hospital-medallion-data"
GCS_PREFIX = "raw_bq"
DEFAULT_INPUT_DIR = Path("data/raw_bq")
PIPELINE_NAME = "hospital_raw_file_ingestion"

DEFAULT_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2

FILENAME_RE = re.compile(
    r"^(?P<entity>[a-z][a-z0-9_]*)_(?P<timestamp>\d{14})\.csv$"
)


@dataclass
class FileResult:
    file_name: str
    entity_name: Optional[str]
    status: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    checksum: Optional[str] = None
    source_timestamp: Optional[datetime] = None
    gcs_uri: Optional[str] = None
    row_count: Optional[int] = None
    retryable: bool = False
    attempt_number: int = 1
    file_size_bytes: Optional[int] = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def count_csv_rows(path: Path) -> int:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        return sum(1 for _ in reader)


def load_config(client: bigquery.Client) -> Dict[str, dict]:
    query = f"""
        SELECT
            entity_name,
            filename_prefix,
            mandatory,
            file_format,
            target_bronze_table,
            primary_key_column,
            expected_file_date_rule,
            retry_enabled,
            max_retries,
            is_active
        FROM `{PROJECT_ID}.{CONTROL_DATASET}.{CONFIG_TABLE}`
        WHERE is_active = TRUE
    """
    rows = client.query(query).result()
    return {row["entity_name"]: dict(row.items()) for row in rows}


def get_processed_file_state(client: bigquery.Client) -> Dict[str, List[dict]]:
    query = f"""
        SELECT file_name, file_checksum, processing_status
        FROM `{PROJECT_ID}.{CONTROL_DATASET}.{FILE_LOG_TABLE}`
        WHERE file_checksum IS NOT NULL
    """
    result: Dict[str, List[dict]] = {}
    for row in client.query(query).result():
        result.setdefault(row["file_name"], []).append({
            "checksum": row["file_checksum"],
            "processing_status": row["processing_status"],
        })
    return result


def insert_file_log(
    client: bigquery.Client,
    run_id: str,
    result: FileResult,
    expected_source_date: date,
) -> None:
    table = f"{PROJECT_ID}.{CONTROL_DATASET}.{FILE_LOG_TABLE}"
    now = utc_now()

    validation_status = (
        "PASSED" if result.status in ("SUCCESS", "SKIPPED") else "FAILED"
    )
    processing_status = {
        "SUCCESS": "UPLOADED",
        "SKIPPED": "SKIPPED",
        "FAILED": "FAILED",
    }[result.status]

    row = {
        "run_id": run_id,
        "batch_id": None,
        "file_name": result.file_name,
        "entity_name": result.entity_name or "UNKNOWN",
        "source_file_timestamp": (
            result.source_timestamp.isoformat()
            if result.source_timestamp else None
        ),
        "expected_source_date": expected_source_date.isoformat(),
        "file_size_bytes": result.file_size_bytes,
        "file_checksum": result.checksum,
        "gcs_uri": result.gcs_uri,
        "attempt_number": result.attempt_number,
        "validation_status": validation_status,
        "processing_status": processing_status,
        "row_count": result.row_count,
        "accepted_count": result.row_count if result.status == "SUCCESS" else 0,
        "rejected_count": 0,
        "retryable": result.retryable,
        "error_code": result.error_code,
        "error_message": result.error_message,
        "started_at": now.isoformat(),
        "completed_at": now.isoformat(),
        "created_at": now.isoformat(),
    }

    errors = client.insert_rows_json(table, [row])
    if errors:
        raise RuntimeError(f"Failed to insert file_ingestion_log: {errors}")


def insert_validation_error(
    client: bigquery.Client,
    run_id: str,
    result: FileResult,
) -> None:
    if result.status != "FAILED":
        return

    table = f"{PROJECT_ID}.{CONTROL_DATASET}.{VALIDATION_ERROR_TABLE}"

    row = {
        "error_id": str(uuid.uuid4()),
        "run_id": run_id,
        "batch_id": None,
        "file_name": result.file_name,
        "entity_name": result.entity_name,
        "validation_stage": "RAW_LANDING",
        "error_type": result.error_code or "UNKNOWN",
        "error_code": result.error_code or "UNKNOWN",
        "column_name": None,
        "record_identifier": None,
        "raw_value": None,
        "error_message": result.error_message or "Unknown validation error",
        "severity": "ERROR",
        "retryable": result.retryable,
        "attempt_number": result.attempt_number,
        "error_timestamp": utc_now().isoformat(),
    }

    errors = client.insert_rows_json(table, [row])
    if errors:
        raise RuntimeError(f"Failed to insert validation_error_log: {errors}")


def insert_missing_mandatory_error(
    client: bigquery.Client,
    run_id: str,
    entity_name: str,
    expected_source_date: date,
) -> None:
    table = f"{PROJECT_ID}.{CONTROL_DATASET}.{VALIDATION_ERROR_TABLE}"

    row = {
        "error_id": str(uuid.uuid4()),
        "run_id": run_id,
        "batch_id": None,
        "file_name": None,
        "entity_name": entity_name,
        "validation_stage": "FILE_COMPLETENESS",
        "error_type": "MISSING_MANDATORY_FILE",
        "error_code": "MISSING_MANDATORY_FILE",
        "column_name": None,
        "record_identifier": None,
        "raw_value": expected_source_date.isoformat(),
        "error_message": (
            f"Mandatory file for entity '{entity_name}' was not received "
            f"for source date {expected_source_date}"
        ),
        "severity": "ERROR",
        "retryable": False,
        "attempt_number": 0,
        "error_timestamp": utc_now().isoformat(),
    }

    errors = client.insert_rows_json(table, [row])
    if errors:
        raise RuntimeError(
            f"Failed to insert missing mandatory error for {entity_name}: {errors}"
        )


def insert_final_pipeline_run(
    client: bigquery.Client,
    run_id: str,
    processing_date: date,
    total_files_received: int,
    processed: int,
    skipped: int,
    failed: int,
    total_records_uploaded: int,
    missing_mandatory_count: int,
    mandatory_failed_count: int,
    error_message: Optional[str],
) -> str:
    table = f"{PROJECT_ID}.{CONTROL_DATASET}.{PIPELINE_RUN_TABLE}"

    if missing_mandatory_count > 0 or mandatory_failed_count > 0:
        status = "FAILED"
    elif failed > 0:
        status = "PARTIAL_FAILURE"
    else:
        status = "SUCCESS"

    row = {
        "run_id": run_id,
        "batch_id": None,
        "pipeline_name": PIPELINE_NAME,
        "run_date": processing_date.isoformat(),
        "expected_source_date": (processing_date - timedelta(days=1)).isoformat(),
        "start_time": utc_now().isoformat(),
        "end_time": utc_now().isoformat(),
        "status": status,
        "total_files_expected": 7,
        "total_files_received": total_files_received,
        "total_files_processed": processed,
        "total_files_failed": failed,
        "total_records_received": total_records_uploaded,
        "total_records_rejected": 0,
        "error_message": error_message,
        "created_at": utc_now().isoformat(),
        "updated_at": utc_now().isoformat(),
    }

    errors = client.insert_rows_json(table, [row])
    if errors:
        raise RuntimeError(f"Failed to insert final pipeline_run: {errors}")

    return status


def upload_to_gcs(
    storage_client: storage.Client,
    path: Path,
    max_attempts: int,
) -> tuple[str, int]:
    bucket = storage_client.bucket(GCS_BUCKET)
    destination = f"{GCS_PREFIX}/{path.name}"
    blob = bucket.blob(destination)

    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            blob.upload_from_filename(
                str(path),
                content_type="text/csv",
            )
            return f"gs://{GCS_BUCKET}/{destination}", attempt
        except Exception as exc:
            last_error = exc

            if attempt < max_attempts:
                sleep_seconds = RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
                print(
                    f"  Retryable GCS error on attempt {attempt}: {exc}"
                    f" | retrying in {sleep_seconds}s"
                )
                time.sleep(sleep_seconds)

    raise RuntimeError(
        f"GCS upload failed after {max_attempts} attempts: {last_error}"
    )


def validate_csv(path: Path) -> Optional[str]:
    try:
        with path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            header = next(reader, None)

            if not header:
                return "CSV file is empty"

            if any(not column.strip() for column in header):
                return "CSV header contains an empty column name"

            for _ in reader:
                pass

    except UnicodeDecodeError:
        return "File is not valid UTF-8 CSV"
    except csv.Error as exc:
        return f"Invalid CSV format: {exc}"

    return None


def process_file(
    path: Path,
    processing_date: date,
    config: Dict[str, dict],
    bq_client: bigquery.Client,
    storage_client: storage.Client,
    processed_state: Dict[str, List[dict]],
) -> FileResult:

    file_size = path.stat().st_size
    match = FILENAME_RE.match(path.name)

    if not match:
        return FileResult(
            path.name,
            None,
            "FAILED",
            "INVALID_FILENAME",
            "Filename must follow <entity>_YYYYMMDDHHMMSS.csv",
            file_size_bytes=file_size,
        )

    entity = match.group("entity")
    timestamp_text = match.group("timestamp")

    if entity not in config:
        return FileResult(
            path.name,
            entity,
            "FAILED",
            "UNKNOWN_ENTITY",
            f"No active ingestion configuration exists for entity '{entity}'",
            file_size_bytes=file_size,
        )

    cfg = config[entity]

    if not path.name.startswith(cfg["filename_prefix"]):
        return FileResult(
            path.name,
            entity,
            "FAILED",
            "INVALID_FILENAME_PREFIX",
            f"Expected filename prefix '{cfg['filename_prefix']}'",
            file_size_bytes=file_size,
        )

    try:
        source_timestamp = datetime.strptime(
            timestamp_text,
            "%Y%m%d%H%M%S",
        )
    except ValueError:
        return FileResult(
            path.name,
            entity,
            "FAILED",
            "INVALID_TIMESTAMP",
            "Timestamp in filename is not a valid YYYYMMDDHHMMSS value",
            file_size_bytes=file_size,
        )

    if cfg["expected_file_date_rule"] == "T-1":
        expected = processing_date - timedelta(days=1)

        if source_timestamp.date() != expected:
            return FileResult(
                path.name,
                entity,
                "FAILED",
                "NOT_T_MINUS_1",
                f"Expected source date {expected} but found {source_timestamp.date()}",
                source_timestamp=source_timestamp,
                file_size_bytes=file_size,
            )

    if cfg["file_format"].upper() != "CSV":
        return FileResult(
            path.name,
            entity,
            "FAILED",
            "UNSUPPORTED_FILE_FORMAT",
            f"Configured format is {cfg['file_format']}",
            source_timestamp=source_timestamp,
            file_size_bytes=file_size,
        )

    csv_error = validate_csv(path)

    if csv_error:
        return FileResult(
            path.name,
            entity,
            "FAILED",
            "INVALID_CSV",
            csv_error,
            source_timestamp=source_timestamp,
            file_size_bytes=file_size,
        )

    row_count = count_csv_rows(path)
    checksum = sha256_file(path)

    previous = processed_state.get(path.name, [])

    if previous:
        if any(item["checksum"] == checksum for item in previous):
            return FileResult(
                path.name,
                entity,
                "SKIPPED",
                "ALREADY_PROCESSED",
                "Same filename and SHA-256 checksum were previously processed",
                checksum=checksum,
                source_timestamp=source_timestamp,
                row_count=row_count,
                file_size_bytes=file_size,
            )

        return FileResult(
            path.name,
            entity,
            "FAILED",
            "CHECKSUM_MISMATCH",
            "Same filename was previously processed with a different SHA-256 checksum",
            checksum=checksum,
            source_timestamp=source_timestamp,
            row_count=row_count,
            file_size_bytes=file_size,
        )

    duplicate_query = f"""
        SELECT file_name
        FROM `{PROJECT_ID}.{CONTROL_DATASET}.{FILE_LOG_TABLE}`
        WHERE file_checksum = @checksum
        LIMIT 1
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "checksum",
                "STRING",
                checksum,
            )
        ]
    )

    duplicate = list(
        bq_client.query(
            duplicate_query,
            job_config=job_config,
        ).result()
    )

    if duplicate:
        return FileResult(
            path.name,
            entity,
            "FAILED",
            "DUPLICATE_CONTENT",
            f"Same SHA-256 checksum already exists for file '{duplicate[0]['file_name']}'",
            checksum=checksum,
            source_timestamp=source_timestamp,
            row_count=row_count,
            file_size_bytes=file_size,
        )

    max_retries = cfg["max_retries"] or DEFAULT_RETRIES

    if not cfg["retry_enabled"]:
        max_retries = 1

    try:
        gcs_uri, attempts = upload_to_gcs(
            storage_client,
            path,
            max_retries,
        )

        return FileResult(
            path.name,
            entity,
            "SUCCESS",
            checksum=checksum,
            source_timestamp=source_timestamp,
            gcs_uri=gcs_uri,
            row_count=row_count,
            attempt_number=attempts,
            file_size_bytes=file_size,
        )

    except Exception as exc:
        return FileResult(
            path.name,
            entity,
            "FAILED",
            "GCS_UPLOAD_ERROR",
            str(exc),
            checksum=checksum,
            source_timestamp=source_timestamp,
            row_count=row_count,
            retryable=True,
            attempt_number=max_retries,
            file_size_bytes=file_size,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processing-date", required=True)
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_INPUT_DIR),
    )
    args = parser.parse_args()

    try:
        processing_date = datetime.strptime(
            args.processing_date,
            "%Y-%m-%d",
        ).date()
    except ValueError:
        print(
            "ERROR: --processing-date must be YYYY-MM-DD",
            file=sys.stderr,
        )
        return 2

    input_dir = Path(args.input_dir)

    if not input_dir.exists():
        print(
            f"ERROR: Input directory does not exist: {input_dir}",
            file=sys.stderr,
        )
        return 2

    files = sorted(input_dir.glob("*.csv"))

    if not files:
        print(
            f"ERROR: No CSV files found under {input_dir}",
            file=sys.stderr,
        )
        return 1

    bq_client = bigquery.Client(project=PROJECT_ID)
    storage_client = storage.Client(project=PROJECT_ID)

    config = load_config(bq_client)
    processed_state = get_processed_file_state(bq_client)

    if not config:
        print(
            "ERROR: No active file ingestion configuration found",
            file=sys.stderr,
        )
        return 1

    run_id = str(uuid.uuid4())
    expected_source = processing_date - timedelta(days=1)

    print(f"Processing date : {processing_date}")
    print(f"Expected source : {expected_source}")
    print(f"Input directory : {input_dir}")
    print(f"Files discovered : {len(files)}")
    print(f"Run ID          : {run_id}")
    print()

    results: List[FileResult] = []
    audit_errors: List[str] = []
    received_entities = set()

    for path in files:
        print(f"===== {path.name} =====")

        try:
            result = process_file(
                path,
                processing_date,
                config,
                bq_client,
                storage_client,
                processed_state,
            )

            results.append(result)

            # A valid T-1 file counts as received even when it is skipped
            # because the same checksum was already processed.
            if (
                result.source_timestamp
                and result.source_timestamp.date() == expected_source
                and result.entity_name in config
            ):
                received_entities.add(result.entity_name)

            try:
                insert_file_log(
                    bq_client,
                    run_id,
                    result,
                    expected_source,
                )
                insert_validation_error(
                    bq_client,
                    run_id,
                    result,
                )
            except Exception as exc:
                audit_errors.append(str(exc))
                print(f"AUDIT ERROR: {exc}")

            if result.status == "SUCCESS":
                print(
                    f"SUCCESS (GCS, attempt {result.attempt_number})"
                )
            elif result.status == "SKIPPED":
                print(
                    f"SKIPPED: {result.error_code} - {result.error_message}"
                )
            else:
                print(
                    f"FAILED: {result.error_code} - {result.error_message}"
                )

        except Exception as exc:
            result = FileResult(
                path.name,
                None,
                "FAILED",
                "UNHANDLED_ERROR",
                str(exc),
                file_size_bytes=path.stat().st_size,
            )
            results.append(result)

            try:
                insert_file_log(
                    bq_client,
                    run_id,
                    result,
                    expected_source,
                )
                insert_validation_error(
                    bq_client,
                    run_id,
                    result,
                )
            except Exception as audit_exc:
                audit_errors.append(str(audit_exc))

            print(
                f"FAILED: UNHANDLED_ERROR - {exc}"
            )

        print()

    mandatory_entities = {
        entity
        for entity, cfg in config.items()
        if cfg["mandatory"]
    }

    missing_entities = sorted(
        mandatory_entities - received_entities
    )

    if missing_entities:
        print("======================================")
        print("MANDATORY FILE CHECK")
        print("======================================")

        for entity in missing_entities:
            print(
                f"MISSING_MANDATORY_FILE: {entity} "
                f"for source date {expected_source}"
            )

            try:
                insert_missing_mandatory_error(
                    bq_client,
                    run_id,
                    entity,
                    expected_source,
                )
            except Exception as exc:
                audit_errors.append(str(exc))
                print(f"AUDIT ERROR: {exc}")

        print()

    # Determine mandatory failures only for mandatory entities that do NOT
    # have a valid T-1 file satisfying the mandatory requirement.
    #
    # A valid T-1 file that was already processed is represented as SKIPPED
    # and is therefore considered satisfied. A stale/non-T-1 file for an
    # entity must not be counted as a mandatory failure when the entity is
    # already satisfied by a valid T-1 file.
    mandatory_failed_entities = set()

    for result in results:
        if result.status != "FAILED":
            continue

        entity = result.entity_name

        if entity not in mandatory_entities:
            continue

        if entity in received_entities:
            continue

        # Only a failed file for a mandatory entity with no valid T-1 file
        # counts as a mandatory failure. Missing entities are separately
        # captured as MISSING_MANDATORY_FILE.
        if result.source_timestamp and result.source_timestamp.date() == expected_source:
            mandatory_failed_entities.add(entity)

    success = sum(
        r.status == "SUCCESS"
        for r in results
    )

    skipped = sum(
        r.status == "SKIPPED"
        for r in results
    )

    failed = sum(
        r.status == "FAILED"
        for r in results
    )

    uploaded_records = sum(
        r.row_count or 0
        for r in results
        if r.status == "SUCCESS"
    )

    error_parts = []

    if failed:
        error_parts.append(
            f"{failed} file(s) failed during raw landing"
        )

    if missing_entities:
        error_parts.append(
            f"{len(missing_entities)} mandatory file(s) missing"
        )

    if mandatory_failed_entities:
        error_parts.append(
            f"{len(mandatory_failed_entities)} mandatory file(s) failed"
        )

    if audit_errors:
        error_parts.append(
            f"{len(audit_errors)} audit operation(s) failed"
        )

    final_error = "; ".join(error_parts) or None

    run_status = insert_final_pipeline_run(
        bq_client,
        run_id,
        processing_date,
        len(files),
        success,
        skipped,
        failed,
        uploaded_records,
        len(missing_entities),
        len(mandatory_failed_entities),
        final_error,
    )

    print("======================================")
    print("INGESTION SUMMARY")
    print("======================================")
    print(f"Run ID               : {run_id}")
    print(f"Discovered           : {len(results)}")
    print(f"Success              : {success}")
    print(f"Skipped              : {skipped}")
    print(f"Failed               : {failed}")
    print(f"Mandatory missing    : {len(missing_entities)}")
    print(f"Mandatory failed     : {len(mandatory_failed_entities)}")
    print(f"Toal Records Identified     : {uploaded_records}")
    print("Total Records Rejected     : 0")
    print(f"Run status           : {run_status}")

    return 1 if run_status != "SUCCESS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
