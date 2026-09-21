resource "google_storage_bucket" "raw" {
  name                        = var.bucket_name
  project                     = var.project_id
  location                    = var.location
  storage_class               = var.storage_class
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  soft_delete_policy {
    retention_duration_seconds = var.soft_delete_retention_seconds
  }

  lifecycle_rule {
    condition {
      age = var.nearline_age_days
    }

    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = var.coldline_age_days
    }

    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = var.archive_age_days
    }

    action {
      type          = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
  }

  labels = merge(
    var.labels,
    {
      managed_by  = "terraform"
      environment = var.environment
      layer       = "raw"
    }
  )
}