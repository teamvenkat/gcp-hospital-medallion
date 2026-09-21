variable "project_id" {
  type        = string
  description = "Existing GCP project that will host the Terraform state bucket."
}

variable "region" {
  type    = string
  default = "asia-south1"
}

variable "state_bucket_name" {
  type        = string
  description = "Globally unique GCS bucket name used only for Terraform remote state."
}

variable "soft_delete_days" {
  type    = number
  default = 30

  validation {
    condition     = var.soft_delete_days >= 7 && var.soft_delete_days <= 90
    error_message = "soft_delete_days must be between 7 and 90."
  }
}
