terraform {
  backend "gcs" {
    bucket = "qwiklabs-gcp-03-df92b3e56f96-terraform-state"
    prefix = "dev"
  }
}
