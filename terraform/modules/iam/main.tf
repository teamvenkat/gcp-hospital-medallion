resource "google_service_account" "ingestion" {
  account_id   = var.ingestion_service_account_id
  display_name = "Hospital Medallion DEV Ingestion"
  description  = "Service account for CSV ingestion into Raw GCS and BigQuery Bronze."
  project      = var.project_id
}

resource "google_service_account" "composer" {
  account_id   = var.composer_service_account_id
  display_name = "Hospital Medallion DEV Composer"
  description  = "Service account for Cloud Composer orchestration."
  project      = var.project_id
}

resource "google_project_iam_member" "ingestion_bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_storage_bucket_iam_member" "ingestion_raw_bucket_admin" {
  bucket = var.raw_bucket_name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.ingestion.email}"
}

resource "google_bigquery_dataset_iam_member" "ingestion_bronze_editor" {
  project    = var.project_id
  dataset_id = var.bronze_dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.ingestion.email}"
}