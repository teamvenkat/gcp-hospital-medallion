terraform {
  backend "gcs" {
    bucket = "gcp-hospital-medallion-tfstate"
    prefix = "terraform/state/dev"
  }
}
