output "state_bucket_name" {
  value       = google_storage_bucket.terraform_state.name
  description = "Terraform remote state bucket."
}

output "state_bucket_uri" {
  value       = "gs://${google_storage_bucket.terraform_state.name}"
}

output "state_backend_prefix" {
  value       = "terraform/state"
}
