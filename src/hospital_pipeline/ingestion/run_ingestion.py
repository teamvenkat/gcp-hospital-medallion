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
- departments/doctors are warning-only master data
- Transaction T-1 failures/missing files fail the pipeline
- Append-only pipeline_run
- file_ingestion_log and validation_error_log
- Local incoming/processed/skipped/failed/non_processed lifecycle folders
- Failed and non-processed retry scan across +/- 7 processing-date folders
- Cumulative mandatory completeness across repeated runs for the same source date
- Local application logging to logs/ingestion/ingestion_YYYYMMDD.log
- No Bronze processing
"""

import argparse
import csv
import hashlib
import logging
import re
import shutil
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
INCOMING_DIR_NAME = "incoming"
PROCESSED_DIR_NAME = "processed"
SKIPPED_DIR_NAME = "skipped"
FAILED_DIR_NAME = "failed"
NON_PROCESSED_DIR_NAME = "non_processed"
FAILED_SCAN_DAYS = 7
PIPELINE_NAME = "hospital_raw_file_ingestion"

MASTER_ENTITIES = {"departments", "doctors"}
TRANSACTION_ENTITIES = {
    "registrations",
    "encounters",
    "admissions",
    "discharges",
    "billing",
}

DEFAULT_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2

FILENAME_RE = re.compile(
    r"^(?P<entity>[a-z][a-z0-9_]*)_(?P<timestamp>\d{14})\.csv$"
)

LOG_DIR = Path("logs/ingestion")
LOGGER = logging.getLogger("hospital_ingestion")


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


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOG_DIR / (
        f"ingestion_{utc_now().strftime('%Y%m%d')}.log"
    )

    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False

    if not LOGGER.handlers:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s"
        )
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        LOGGER.addHandler(file_handler)


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


def insert_master_warning(
    client: bigquery.Client,
    run_id: str,
    result: FileResult,
    expected_source_date: date,
) -> None:
    table = f"{PROJECT_ID}.{CONTROL_DATASET}.{VALIDATION_ERROR_TABLE}"
    now = utc_now()

    row = {
        "error_id": str(uuid.uuid4()),
        "run_id": run_id,
        "batch_id": None,
        "file_name": result.file_name or None,
        "entity_name": result.entity_name,
        "validation_stage": "FILE_COMPLETENESS",
        "error_type": result.error_code or "MASTER_WARNING",
        "error_code": result.error_code or "MASTER_WARNING",
        "column_name": None,
        "record_identifier": None,
        "raw_value": expected_source_date.isoformat(),
        "error_message": result.error_message or (
            f"Master file for entity '{result.entity_name}' was not "
            f"successfully processed for source date {expected_source_date}"
        ),
        "severity": "WARNING",
        "retryable": result.retryable,
        "attempt_number": result.attempt_number,
        "error_timestamp": now.isoformat(),
    }

    errors = client.insert_rows_json(table, [row])
    if errors:
        raise RuntimeError(f"Failed to insert master warning: {errors}")


def move_file_to_lifecycle_folder(
    input_dir: Path,
    path: Path,
    folder_name: str,
    processing_date: date,
) -> Path:
    if folder_name not in {
        PROCESSED_DIR_NAME,
        SKIPPED_DIR_NAME,
        FAILED_DIR_NAME,
        NON_PROCESSED_DIR_NAME,
    }:
        raise ValueError(f"Unsupported lifecycle folder: {folder_name}")

    destination_dir = (
        input_dir / folder_name / processing_date.isoformat()
    )
    destination_dir.mkdir(parents=True, exist_ok=True)

    destination = destination_dir / path.name

    if destination.exists():
        destination.unlink()

    shutil.move(str(path), str(destination))
    return destination


def extract_source_date(path: Path) -> Optional[date]:
    match = FILENAME_RE.match(path.name)
    if not match:
        return None

    try:
        return datetime.strptime(
            match.group("timestamp"),
            "%Y%m%d%H%M%S",
        ).date()
    except ValueError:
        return None


def discover_eligible_files(
    input_dir: Path,
    processing_date: date,
) -> tuple[List[Path], int, int]:
    expected_source = processing_date - timedelta(days=1)
    incoming_dir = input_dir / INCOMING_DIR_NAME
    candidates: List[Path] = []

    if incoming_dir.exists():
        candidates.extend(incoming_dir.glob("*.csv"))

    # Failed and non-processed files are retry candidates.
    failed_root = input_dir / FAILED_DIR_NAME
    if failed_root.exists():
        for offset in range(-FAILED_SCAN_DAYS, FAILED_SCAN_DAYS + 1):
            scan_date = processing_date + timedelta(days=offset)
            scan_dir = failed_root / scan_date.isoformat()
            if scan_dir.exists():
                candidates.extend(scan_dir.glob("*.csv"))

    # Non-processed files can also become eligible during a backfill.
    non_processed_root = input_dir / NON_PROCESSED_DIR_NAME
    if non_processed_root.exists():
        for offset in range(-FAILED_SCAN_DAYS, FAILED_SCAN_DAYS + 1):
            scan_date = processing_date + timedelta(days=offset)
            scan_dir = non_processed_root / scan_date.isoformat()
            if scan_dir.exists():
                candidates.extend(scan_dir.glob("*.csv"))


    eligible: List[Path] = []
    seen: Dict[str, str] = {}

    for path in candidates:
        if extract_source_date(path) != expected_source:
            continue

        existing = seen.get(path.name)
        if existing:
            existing_path = Path(existing)
            if existing_path.parent == incoming_dir:
                continue
            if path.parent == incoming_dir:
                eligible = [
                    item for item in eligible if item.name != path.name
                ]
                seen[path.name] = str(path)
                eligible.append(path)
            continue

        seen[path.name] = str(path)
        eligible.append(path)

    eligible.sort(key=lambda p: p.name)

    incoming_eligible = sum(
        1 for path in eligible if path.parent == incoming_dir
    )
    failed_eligible = sum(
        1
        for path in eligible
        if path.parent.parent.name == FAILED_DIR_NAME
    )
    non_processed_eligible = sum(
        1
        for path in eligible
        if path.parent.parent.name == NON_PROCESSED_DIR_NAME
    )

    return (
        eligible,
        incoming_eligible,
        failed_eligible,
        non_processed_eligible,
    )


def get_cumulative_entity_state(
    client: bigquery.Client,
    expected_source_date: date,
) -> tuple[set[str], set[str]]:
    """
    Return cumulative entity state for a source date.

    An entity is considered satisfied when any historical attempt for that
    source date has processing_status UPLOADED or SKIPPED.

    An entity is considered failed when it has a FAILED attempt and has not
    been successfully satisfied.
    """
    query = f"""
        SELECT
            entity_name,
            processing_status,
            completed_at,
            created_at
        FROM `{PROJECT_ID}.{CONTROL_DATASET}.{FILE_LOG_TABLE}`
        WHERE expected_source_date = @expected_source_date
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "expected_source_date",
                "DATE",
                expected_source_date.isoformat(),
            )
        ]
    )

    successful_entities: set[str] = set()
    failed_entities: set[str] = set()

    for row in client.query(query, job_config=job_config).result():
        entity = row["entity_name"]
        status = row["processing_status"]

        if status in {"UPLOADED", "SKIPPED"}:
            successful_entities.add(entity)
        elif status == "FAILED":
            failed_entities.add(entity)

    failed_entities -= successful_entities

    LOGGER.info(
        "Cumulative source-date state | source_date=%s | "
        "successful_entities=%s | unresolved_failed_entities=%s",
        expected_source_date,
        sorted(successful_entities),
        sorted(failed_entities),
    )

    return successful_entities, failed_entities


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
    fatal_transaction_failures: int,
) -> str:
    table = f"{PROJECT_ID}.{CONTROL_DATASET}.{PIPELINE_RUN_TABLE}"

    if (
        missing_mandatory_count > 0
        or mandatory_failed_count > 0
        or fatal_transaction_failures > 0
    ):
        status = "FAILED"
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
            LOGGER.info(
                "GCS upload attempt | file=%s | attempt=%s",
                path.name,
                attempt,
            )
            blob.upload_from_filename(
                str(path),
                content_type="text/csv",
            )
            LOGGER.info(
                "GCS upload success | file=%s | attempt=%s | uri=gs://%s/%s",
                path.name,
                attempt,
                GCS_BUCKET,
                destination,
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
                LOGGER.warning(
                    "GCS retry | file=%s | attempt=%s | error=%s | sleep=%ss",
                    path.name,
                    attempt,
                    exc,
                    sleep_seconds,
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
    setup_logging()
    LOGGER.info("Ingestion invocation started")

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

    expected_source = processing_date - timedelta(days=1)

    LOGGER.info(
        "Processing request | processing_date=%s | expected_source=%s | input_dir=%s",
        processing_date,
        expected_source,
        input_dir,
    )

    (
        files,
        incoming_eligible_count,
        failed_eligible_count,
        non_processed_eligible_count,
    ) = discover_eligible_files(input_dir, processing_date)

    # Move incoming files outside the current source-date scope to
    # non_processed/<processing-date>/. They are not run failures.
    incoming_dir = input_dir / INCOMING_DIR_NAME
    non_processed_count = 0

    if incoming_dir.exists():
        for incoming_path in list(incoming_dir.glob("*.csv")):
            if extract_source_date(incoming_path) != expected_source:
                try:
                    destination = move_file_to_lifecycle_folder(
                        input_dir,
                        incoming_path,
                        NON_PROCESSED_DIR_NAME,
                        processing_date,
                    )
                    non_processed_count += 1
                    print(
                        f"NON_PROCESSED: {incoming_path.name} "
                        f"-> {destination}"
                    )
                    LOGGER.info(
                        "File moved | state=NON_PROCESSED | file=%s | destination=%s",
                        incoming_path.name,
                        destination,
                    )
                except Exception as move_exc:
                    print(
                        f"FILE MOVE ERROR: could not move "
                        f"'{incoming_path.name}': {move_exc}"
                    )
                    LOGGER.exception(
                        "File move failed | state=NON_PROCESSED | file=%s",
                        incoming_path.name,
                    )

    if not files:
        print(
            f"ERROR: No eligible CSV files found for source date "
            f"{processing_date - timedelta(days=1)}",
            file=sys.stderr,
        )
        return 1

    bq_client = bigquery.Client(project=PROJECT_ID)
    storage_client = storage.Client(project=PROJECT_ID)

    config = load_config(bq_client)
    processed_state = get_processed_file_state(bq_client)

    LOGGER.info(
        "Configuration loaded | active_entities=%s | mandatory_entities=%s",
        sorted(config.keys()),
        sorted(
            entity for entity, cfg in config.items()
            if cfg["mandatory"]
        ),
    )

    if not config:
        print(
            "ERROR: No active file ingestion configuration found",
            file=sys.stderr,
        )
        return 1

    run_id = str(uuid.uuid4())
    expected_source = processing_date - timedelta(days=1)

    print(f"Processing date       : {processing_date}")
    print(f"Expected source       : {expected_source}")
    print(f"Input directory       : {input_dir}")
    print(f"Files discovered      : {len(files)}")
    print(f"  Incoming eligible   : {incoming_eligible_count}")
    print(f"  Failed retry        : {failed_eligible_count}")
    print(f"  Non-processed retry : {non_processed_eligible_count}")
    print(f"Failed scan window    : +/-{FAILED_SCAN_DAYS} days")
    print(f"Run ID                : {run_id}")
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

            LOGGER.info(
                "File result | file=%s | entity=%s | status=%s | "
                "error_code=%s | attempt=%s | rows=%s",
                result.file_name,
                result.entity_name,
                result.status,
                result.error_code,
                result.attempt_number,
                result.row_count,
            )

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
                LOGGER.exception("Audit insert failed")

            if result.status == "SUCCESS":
                print(
                    f"SUCCESS (GCS, attempt {result.attempt_number})"
                )
                try:
                    destination = move_file_to_lifecycle_folder(
                        input_dir,
                        path,
                        PROCESSED_DIR_NAME,
                        processing_date,
                    )
                    print(f"MOVED: {destination}")
                except Exception as move_exc:
                    audit_errors.append(
                        f"Failed to move successful file '{path.name}': "
                        f"{move_exc}"
                    )
                    print(f"FILE MOVE ERROR: {move_exc}")

            elif result.status == "SKIPPED":
                print(
                    f"SKIPPED: {result.error_code} - {result.error_message}"
                )
                try:
                    destination = move_file_to_lifecycle_folder(
                        input_dir,
                        path,
                        SKIPPED_DIR_NAME,
                        processing_date,
                    )
                    print(f"MOVED: {destination}")
                    LOGGER.info(
                        "File moved | state=SKIPPED | file=%s | destination=%s",
                        path.name,
                        destination,
                    )
                except Exception as move_exc:
                    audit_errors.append(
                        f"Failed to move skipped file '{path.name}': "
                        f"{move_exc}"
                    )
                    print(f"FILE MOVE ERROR: {move_exc}")

            else:
                print(
                    f"FAILED: {result.error_code} - {result.error_message}"
                )

                if result.entity_name in MASTER_ENTITIES:
                    print(
                        f"WARNING: MASTER FILE FAILURE - "
                        f"{result.entity_name}; pipeline continues"
                    )
                    try:
                        insert_master_warning(
                            bq_client,
                            run_id,
                            result,
                            expected_source,
                        )
                    except Exception as warning_exc:
                        audit_errors.append(str(warning_exc))
                        print(f"AUDIT ERROR: {warning_exc}")

                try:
                    destination = move_file_to_lifecycle_folder(
                        input_dir,
                        path,
                        FAILED_DIR_NAME,
                        processing_date,
                    )
                    print(f"MOVED: {destination}")
                    LOGGER.info(
                        "File moved | state=FAILED | file=%s | destination=%s",
                        path.name,
                        destination,
                    )
                except Exception as move_exc:
                    audit_errors.append(
                        f"Failed to move failed file '{path.name}': "
                        f"{move_exc}"
                    )
                    print(f"FILE MOVE ERROR: {move_exc}")

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
            LOGGER.exception(
                "Unhandled file-processing error | file=%s",
                path.name,
            )

            try:
                destination = move_file_to_lifecycle_folder(
                    input_dir,
                    path,
                    FAILED_DIR_NAME,
                    processing_date,
                )
                print(f"MOVED: {destination}")
            except Exception as move_exc:
                audit_errors.append(
                    f"Failed to move unhandled-error file '{path.name}': "
                    f"{move_exc}"
                )
                print(f"FILE MOVE ERROR: {move_exc}")

        print()

    mandatory_entities = {
        entity
        for entity, cfg in config.items()
        if cfg["mandatory"]
    }

    (
        cumulative_successful_entities,
        cumulative_failed_entities,
    ) = get_cumulative_entity_state(
        bq_client,
        expected_source,
    )

    missing_entities = sorted(
        mandatory_entities - cumulative_successful_entities
    )

    unresolved_failed_entities = sorted(
        mandatory_entities
        & cumulative_failed_entities
        - cumulative_successful_entities
    )

    LOGGER.info(
        "Mandatory cumulative state | mandatory=%s | satisfied=%s | "
        "missing=%s | unresolved_failed=%s",
        sorted(mandatory_entities),
        sorted(mandatory_entities & cumulative_successful_entities),
        missing_entities,
        unresolved_failed_entities,
    )

    if missing_entities:
        print("======================================")
        print("MANDATORY FILE CHECK")
        print("======================================")

        for entity in missing_entities:
            if entity in MASTER_ENTITIES:
                print(
                    f"WARNING: MISSING_MASTER_FILE: {entity} "
                    f"for source date {expected_source}"
                )
                warning_result = FileResult(
                    file_name="",
                    entity_name=entity,
                    status="WARNING",
                    error_code="MISSING_MASTER_FILE",
                    error_message=(
                        f"Master file for entity '{entity}' was not received "
                        f"for source date {expected_source}"
                    ),
                )
                try:
                    insert_master_warning(
                        bq_client,
                        run_id,
                        warning_result,
                        expected_source,
                    )
                except Exception as exc:
                    audit_errors.append(str(exc))
                    print(f"AUDIT ERROR: {exc}")
            else:
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

    # Only unresolved transaction entities can make the processing date fail.
    # A previous SUCCESS/SKIPPED for the same source date satisfies the entity,
    # even if the current invocation does not contain that file.
    mandatory_failed_entities = {
        entity
        for entity in unresolved_failed_entities
        if entity in TRANSACTION_ENTITIES
    }

    fatal_missing_entities = {
        entity
        for entity in missing_entities
        if entity in TRANSACTION_ENTITIES
    }

    success = sum(r.status == "SUCCESS" for r in results)
    skipped = sum(r.status == "SKIPPED" for r in results)
    failed = sum(r.status == "FAILED" for r in results)

    uploaded_records = sum(
        r.row_count or 0
        for r in results
        if r.status == "SUCCESS"
    )

    fatal_transaction_failures = len(mandatory_failed_entities)

    master_warning_count = (
        sum(
            1
            for r in results
            if r.status == "FAILED"
            and r.entity_name in MASTER_ENTITIES
        )
        + sum(
            1
            for entity in missing_entities
            if entity in MASTER_ENTITIES
        )
    )

    error_parts = []

    if fatal_transaction_failures:
        error_parts.append(
            f"{fatal_transaction_failures} transaction file(s) failed"
        )

    if fatal_missing_entities:
        error_parts.append(
            f"{len(fatal_missing_entities)} transaction file(s) missing"
        )

    if mandatory_failed_entities:
        error_parts.append(
            f"{len(mandatory_failed_entities)} transaction entity/entity(ies) "
            f"remain failed for source date {expected_source}"
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
        len(results),
        success,
        skipped,
        failed,
        uploaded_records,
        len(fatal_missing_entities),
        len(mandatory_failed_entities),
        final_error,
        fatal_transaction_failures,
    )

    print("======================================")
    print("INGESTION SUMMARY")
    print("======================================")
    print(f"Run ID                    : {run_id}")
    print(f"Processing date            : {processing_date}")
    print(f"Source date                : {expected_source}")
    print(f"Files discovered           : {len(results)}")
    print(f"  Incoming eligible        : {incoming_eligible_count}")
    print(f"  Failed retry             : {failed_eligible_count}")
    print(f"Files uploaded             : {success}")
    print(f"Files skipped              : {skipped}")
    print(f"Files failed               : {failed}")
    print(f"Non-processed moved        : {non_processed_count}")
    print(f"Mandatory missing          : {len(fatal_missing_entities)}")
    print(f"Mandatory failed           : {len(mandatory_failed_entities)}")
    print(
        f"Mandatory satisfied        : "
        f"{len(mandatory_entities & cumulative_successful_entities)}"
        f"/{len(mandatory_entities)}"
    )
    print(f"Master warnings            : {master_warning_count}")
    print(f"Records in uploaded files  : {uploaded_records}")
    print("Records rejected           : 0")
    print(f"Run status                 : {run_status}")

    LOGGER.info(
        "Ingestion completed | run_id=%s | processing_date=%s | "
        "source_date=%s | status=%s | current_uploaded=%s | "
        "current_skipped=%s | current_failed=%s | cumulative_satisfied=%s/%s | "
        "cumulative_missing=%s | cumulative_failed=%s | records=%s",
        run_id,
        processing_date,
        expected_source,
        run_status,
        success,
        skipped,
        failed,
        len(mandatory_entities & cumulative_successful_entities),
        len(mandatory_entities),
        sorted(fatal_missing_entities),
        sorted(mandatory_failed_entities),
        uploaded_records,
    )

    if audit_errors:
        LOGGER.error(
            "Audit errors encountered | count=%s | errors=%s",
            len(audit_errors),
            audit_errors,
        )

    return 1 if run_status != "SUCCESS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
