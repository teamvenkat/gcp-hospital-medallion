output "dataset_ids" {
  description = "Map of dataset keys to BigQuery dataset IDs."
  value = {
    for key, dataset in google_bigquery_dataset.datasets :
    key => dataset.dataset_id
  }
}

output "dataset_self_links" {
  description = "Map of dataset keys to BigQuery dataset self-links."
  value = {
    for key, dataset in google_bigquery_dataset.datasets :
    key => dataset.self_link
  }
}