module "raw_storage" {
  source = "../../modules/raw_storage"

  project_id    = var.project_id
  bucket_name   = var.raw_bucket_name
  environment   = var.environment
  location      = var.raw_bucket_location
  storage_class = var.raw_bucket_storage_class
}

module "bigquery" {
  source = "../../modules/bigquery"

  project_id  = var.project_id
  location    = var.region
  environment = var.environment

  datasets = {
    bronze = {
      dataset_id  = "hospital_bronze_dev"
      description = "Bronze layer containing source-aligned hospital data."
      layer       = "bronze"
    }

    silver = {
      dataset_id  = "hospital_silver_dev"
      description = "Silver layer containing cleaned and standardized hospital data."
      layer       = "silver"
    }

    gold = {
      dataset_id  = "hospital_gold_dev"
      description = "Gold layer containing analytics-ready hospital data."
      layer       = "gold"
    }

    control = {
      dataset_id  = "hospital_control_dev"
      description = "Operational control, audit, reconciliation, and data quality metadata."
      layer       = "control"
    }
  }
}


module "iam" {
  source = "../../modules/iam"

  project_id = var.project_id

  ingestion_service_account_id = "hospital-ingestion-dev"
  composer_service_account_id  = "hospital-composer-dev"

  raw_bucket_name   = var.raw_bucket_name
  bronze_dataset_id = "hospital_bronze_dev"
}

