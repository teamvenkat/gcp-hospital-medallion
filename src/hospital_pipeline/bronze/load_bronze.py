import argparse
import csv
import io
import os
import re
from datetime import datetime, timezone
from typing import Dict, List

from google.cloud import bigquery, storage


PROJECT_ID = os.environ["PROJECT_ID"]
CONTROL_DATASET = os.environ["CONTROL_DATASET"]
BRONZE_DATASET = os.environ["BRONZE_DATASET"]

CONFIG_TABLE = "file_ingestion_config"
FILE_LOG_TABLE = "file_ingestion_log"

SOURCE_TIMESTAMP_RE = re.compile(
    r"_(?P<timestamp>\d{14})\.csv$"
)

ENTITY_COLUMNS: Dict[str, List[str]] = {
    "departments": [
        "department_id",
        "department_name",
        "city",
    ],
    "doctors": [
        "doctor_id",
        "first_name",
        "last_name",
        "specialization",
        "department_id",
        "city",
    ],
    "registrations": [
        "registration_id",
        "first_name",
        "last_name",
        "date_of_birth",
        "gender",
        "city",
        "registration_date",
        "status",
        "created_at",
        "updated_at",
    ],
    "encounters": [
        "encounter_id",
        "registration_id",
        "doctor_id",
        "department_id",
        "encounter_date",
        "encounter_type",
        "diagnosis",
        "status",
        "created_at",
        "updated_at",
    ],
    "admissions": [
        "admission_id",
        "registration_id",
        "encounter_id",
        "admission_date",
        "admission_type",
        "ward",
        "status",
        "created_at",
        "updated_at",
    ],
    "discharges": [
        "discharge_id",
        "admission_id",
        "registration_id",
        "discharge_date",
        "discharge_status",
        "created_at",
        "updated_at",
    ],
    "billing": [
        "bill_id",
        "registration_id",
        "encounter_id",
        "admission_id",
        "discharge_id",
        "bill_date",
        "bill_type",
        "bill_description",
        "consultation_amount",
        "procedure_amount",
        "room_amount",
        "other_amount",
        "total_amount",
        "payment_status",
        "created_at",
        "updated_at",
    ],
}

BRONZE_METADATA_COLUMNS = [
    "source_file_name",
    "source_file_timestamp",
    "ingestion_timestamp",
    "run_id",
    "batch_id",
]


def get_file_records(
    client: bigquery.Client,
    run_id: str,
) -> List[dict]:
    query = f"""
        SELECT
            file_name,
            entity_name,
            gcs_uri,
            source_file_timestamp,
            processing_status,
            validation_status,
            batch_id
        FROM `{PROJECT_ID}.{CONTROL_DATASET}.{FILE_LOG_TABLE}`
        WHERE run_id = @run_id
            AND processing_status = 'UPLOADED'
            AND validation_status = 'PASSED'
        ORDER BY entity_name, file_name
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("run_id", "STRING", run_id)
        ]
    )

    return [dict(row) for row in client.query(query, job_config=job_config)]


def get_target_tables(
    client: bigquery.Client,
) -> Dict[str, str]:
    query = f"""
        SELECT
            entity_name,
            target_bronze_table
        FROM `{PROJECT_ID}.{CONTROL_DATASET}.{CONFIG_TABLE}`
        WHERE is_active = TRUE
    """

    result = {}

    for row in client.query(query):
        result[row["entity_name"]] = row["target_bronze_table"]

    return result


def parse_source_timestamp(file_name: str) -> datetime:
    match = SOURCE_TIMESTAMP_RE.search(file_name)

    if not match:
        raise ValueError(
            f"Unable to extract source timestamp from filename: {file_name}"
        )

    return datetime.strptime(
        match.group("timestamp"),
        "%Y%m%d%H%M%S",
    ).replace(tzinfo=timezone.utc)


def download_csv(
    storage_client: storage.Client,
    gcs_uri: str,
) -> List[dict]:
    if not gcs_uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {gcs_uri}")

    bucket_name, object_name = gcs_uri[5:].split("/", 1)

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(object_name)

    content = blob.download_as_text()

    reader = csv.DictReader(io.StringIO(content))

    if reader.fieldnames is None:
        raise ValueError(f"CSV has no header: {gcs_uri}")

    return list(reader)


def build_bronze_rows(
    entity_name: str,
    source_rows: List[dict],
    file_name: str,
    source_file_timestamp: datetime,
    run_id: str,
    batch_id: str | None,
) -> List[dict]:
    if entity_name not in ENTITY_COLUMNS:
        raise ValueError(
            f"No Bronze schema mapping defined for entity: {entity_name}"
        )

    expected_columns = ENTITY_COLUMNS[entity_name]

    ingestion_timestamp = datetime.now(timezone.utc)

    bronze_rows = []

    for source_row in source_rows:
        row = {}

        for column in expected_columns:
            row[column] = source_row.get(column) or None

        row["source_file_name"] = file_name
        row["source_file_timestamp"] = source_file_timestamp.isoformat()
        row["ingestion_timestamp"] = ingestion_timestamp.isoformat()
        row["run_id"] = run_id
        row["batch_id"] = batch_id

        bronze_rows.append(row)

    return bronze_rows


def load_to_bronze(
    client: bigquery.Client,
    target_table: str,
    rows: List[dict],
) -> int:
    if not rows:
        return 0

    errors = client.insert_rows_json(
        target_table,
        rows,
    )

    if errors:
        raise RuntimeError(
            f"BigQuery insert failed for {target_table}: {errors}"
        )

    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load successfully ingested Raw files into BigQuery Bronze."
    )

    parser.add_argument(
        "--run-id",
        required=True,
        help="Raw ingestion run ID to process.",
    )

    args = parser.parse_args()

    bq_client = bigquery.Client(project=PROJECT_ID)
    storage_client = storage.Client(project=PROJECT_ID)

    print("======================================")
    print("Hospital Bronze Loader")
    print("======================================")
    print(f"Project: {PROJECT_ID}")
    print(f"Bronze dataset: {BRONZE_DATASET}")
    print(f"Run ID: {args.run_id}")
    print("")

    target_tables = get_target_tables(bq_client)
    file_records = get_file_records(
        bq_client,
        args.run_id,
    )

    print(f"Successful Raw files found: {len(file_records)}")
    print("")

    total_rows = 0

    for record in file_records:
        entity_name = record["entity_name"]
        file_name = record["file_name"]
        gcs_uri = record["gcs_uri"]

        if entity_name not in target_tables:
            raise ValueError(
                f"No active Bronze target configured for entity: "
                f"{entity_name}"
            )

        target_table = target_tables[entity_name]

        if "." not in target_table:
            target_table = f"{BRONZE_DATASET}.{target_table}"

        target_table = f"{PROJECT_ID}.{target_table}"

        print(f"===== {file_name} =====")
        print(f"Entity: {entity_name}")
        print(f"Source: {gcs_uri}")
        print(f"Target: {target_table}")

        source_rows = download_csv(
            storage_client,
            gcs_uri,
        )

        source_file_timestamp = (
            record["source_file_timestamp"]
            if record["source_file_timestamp"]
            else parse_source_timestamp(file_name)
        )

        bronze_rows = build_bronze_rows(
            entity_name=entity_name,
            source_rows=source_rows,
            file_name=file_name,
            source_file_timestamp=source_file_timestamp,
            run_id=args.run_id,
            batch_id=record["batch_id"],
        )

        loaded = load_to_bronze(
            bq_client,
            target_table,
            bronze_rows,
        )

        total_rows += loaded

        print(f"Rows loaded: {loaded}")
        print("")

    print("======================================")
    print("BRONZE LOAD SUMMARY")
    print("======================================")
    print(f"Files processed: {len(file_records)}")
    print(f"Rows loaded: {total_rows}")
    print("Status: SUCCESS")
    print("======================================")


if __name__ == "__main__":
    main()