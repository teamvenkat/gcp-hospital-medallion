variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "ingestion_service_account_id" {
  description = "Service account ID for the ingestion pipeline."
  type        = string
}

variable "composer_service_account_id" {
  description = "Service account ID for Cloud Composer."
  type        = string
}

variable "raw_bucket_name" {
  description = "Raw GCS bucket name."
  type        = string
}

variable "bronze_dataset_id" {
  description = "Bronze BigQuery dataset ID."
  type        = string
}