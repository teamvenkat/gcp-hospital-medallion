output "bucket_name" {
  description = "Name of the Raw GCS bucket."
  value       = google_storage_bucket.raw.name
}

output "bucket_url" {
  description = "GCS URI of the Raw bucket."
  value       = "gs://${google_storage_bucket.raw.name}"
}

output "bucket_self_link" {
  description = "Self-link of the Raw GCS bucket."
  value       = google_storage_bucket.raw.self_link
}