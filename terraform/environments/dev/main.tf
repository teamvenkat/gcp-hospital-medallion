module "raw_storage" {
  source = "../../modules/raw_storage"

  project_id    = var.project_id
  bucket_name   = var.raw_bucket_name
  environment   = var.environment
  location      = var.raw_bucket_location
  storage_class = var.raw_bucket_storage_class
}