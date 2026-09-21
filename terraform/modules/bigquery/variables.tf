variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "location" {
  description = "BigQuery dataset location."
  type        = string
  default     = "asia-south1"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
}

variable "datasets" {
  description = "BigQuery datasets to create."
  type = map(object({
    dataset_id  = string
    description = string
    layer       = string
  }))
}

variable "labels" {
  description = "Additional labels applied to all datasets."
  type        = map(string)
  default     = {}
}