variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "asia-south1"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
}

variable "raw_bucket_name" {
  description = "Globally unique name of the DEV Raw GCS bucket."
  type        = string
}

variable "raw_bucket_location" {
  description = "Location of the DEV Raw GCS bucket."
  type        = string
  default     = "ASIA-SOUTH1"
}

variable "raw_bucket_storage_class" {
  description = "Default storage class for the DEV Raw GCS bucket."
  type        = string
  default     = "STANDARD"
}