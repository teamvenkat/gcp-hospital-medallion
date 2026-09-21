resource "google_bigquery_dataset" "datasets" {
  for_each = var.datasets

  project    = var.project_id
  dataset_id = each.value.dataset_id
  location   = var.location

  description = each.value.description

  delete_contents_on_destroy = false

  labels = merge(
    var.labels,
    {
      managed_by  = "terraform"
      environment = var.environment
      layer       = each.value.layer
    }
  )
}