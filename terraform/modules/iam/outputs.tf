output "ingestion_service_account_email" {
  description = "Email of the ingestion service account."
  value       = google_service_account.ingestion.email
}

output "composer_service_account_email" {
  description = "Email of the Composer service account."
  value       = google_service_account.composer.email
}