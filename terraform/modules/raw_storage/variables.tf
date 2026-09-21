variable "project_id" {
  description = "GCP project ID where the Raw bucket will be created."
  type        = string
}

variable "bucket_name" {
  description = "Globally unique GCS bucket name."
  type        = string
}

variable "location" {
  description = "GCS bucket location."
  type        = string
  default     = "ASIA-SOUTH1"
}

variable "storage_class" {
  description = "Default storage class for the Raw bucket."
  type        = string
  default     = "STANDARD"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
}

variable "soft_delete_retention_seconds" {
  description = "Soft delete retention period in seconds."
  type        = number
  default     = 2592000
}

variable "nearline_age_days" {
  description = "Age after which objects move to Nearline."
  type        = number
  default     = 30
}

variable "coldline_age_days" {
  description = "Age after which objects move to Coldline."
  type        = number
  default     = 90
}

variable "archive_age_days" {
  description = "Age after which objects move to Archive."
  type        = number
  default     = 365
}

variable "labels" {
  description = "Additional labels for the bucket."
  type        = map(string)
  default     = {}
}