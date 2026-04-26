terraform {
  required_version = ">= 1.7"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  backend "gcs" {
    bucket = "pof-ai-tf-state"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ── Artifact Registry ────────────────────────────────────────────────────────

resource "google_artifact_registry_repository" "pof_ai" {
  repository_id = var.artifact_registry_repo
  format        = "DOCKER"
  location      = var.region
  description   = "PoF-AI Docker images"
}

# ── Firestore ────────────────────────────────────────────────────────────────

resource "google_firestore_database" "pof_ai" {
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
}

# ── Cloud Storage ────────────────────────────────────────────────────────────

resource "google_storage_bucket" "evidence" {
  name                        = "${var.project_id}-pof-ai-evidence"
  location                    = var.region
  uniform_bucket_level_access = true
  versioning { enabled = true }
}

resource "google_storage_bucket" "log" {
  name                        = "${var.project_id}-pof-ai-log"
  location                    = var.region
  uniform_bucket_level_access = true
  versioning { enabled = true }
}

# ── Cloud KMS ────────────────────────────────────────────────────────────────

resource "google_kms_key_ring" "pof_ai" {
  name     = "pof-ai-keyring"
  location = "global"
}

resource "google_kms_crypto_key" "cert_signing" {
  name     = "cert-signing-key"
  key_ring = google_kms_key_ring.pof_ai.id
  purpose  = "ASYMMETRIC_SIGN"
  version_template {
    algorithm = "EC_SIGN_ED25519"
  }
}

resource "google_kms_crypto_key" "log_signing" {
  name     = "log-signing-key"
  key_ring = google_kms_key_ring.pof_ai.id
  purpose  = "ASYMMETRIC_SIGN"
  version_template {
    algorithm = "EC_SIGN_ED25519"
  }
}

# ── Secret Manager ───────────────────────────────────────────────────────────

resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "gemini-api-key"
  replication { auto {} }
}

resource "google_secret_manager_secret_version" "gemini_api_key" {
  secret      = google_secret_manager_secret.gemini_api_key.id
  secret_data = var.gemini_api_key
}

resource "google_secret_manager_secret" "api_key" {
  secret_id = "pof-ai-api-key"
  replication { auto {} }
}

resource "google_secret_manager_secret_version" "api_key" {
  secret      = google_secret_manager_secret.api_key.id
  secret_data = var.api_key
}

# ── Cloud Run: pof-ai-backend ─────────────────────────────────────────────

resource "google_cloud_run_v2_service" "backend" {
  name     = "pof-ai-backend"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = var.backend_image

      resources {
        limits   = { memory = "2Gi", cpu = "2" }
        cpu_idle = true
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }
      env {
        name  = "GCS_BUCKET_EVIDENCE"
        value = google_storage_bucket.evidence.name
      }
      env {
        name  = "KMS_KEY_CERT"
        value = "${google_kms_crypto_key.cert_signing.id}/cryptoKeyVersions/1"
      }
      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.api_key.secret_id
            version = "latest"
          }
        }
      }
    }
    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }
  }
}

# ── Cloud Run: pof-ai-log ────────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "log" {
  name     = "pof-ai-log"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = var.log_image
      resources {
        limits   = { memory = "512Mi", cpu = "1" }
        cpu_idle = true
      }
      env { name = "GCP_PROJECT_ID", value = var.project_id }
      env { name = "GCS_BUCKET_LOG",  value = google_storage_bucket.log.name }
      env {
        name  = "KMS_KEY_LOG"
        value = "${google_kms_crypto_key.log_signing.id}/cryptoKeyVersions/1"
      }
    }
    scaling { min_instance_count = 0, max_instance_count = 3 }
  }
}

# ── Vertex AI Endpoint ───────────────────────────────────────────────────────

resource "google_vertex_ai_endpoint" "hiring" {
  name         = "pof-ai-hiring-endpoint"
  display_name = "PoF-AI Hiring Model Endpoint"
  location     = var.region
  description  = "XGBoost hiring model with intentional bias — audited by PoF-AI"
}

# ── Firebase Hosting ─────────────────────────────────────────────────────────
# Note: Firebase Hosting is managed via firebase.json and firebase CLI.
# The Terraform resource below creates the site, firebase deploy handles content.

resource "google_firebase_hosting_site" "dashboard" {
  provider = google
  project  = var.project_id
  site_id  = "${var.project_id}-pof-ai"
}
