output "backend_url" {
  description = "Cloud Run URL for pof-ai-backend"
  value       = google_cloud_run_v2_service.backend.uri
}

output "log_url" {
  description = "Cloud Run URL for pof-ai-log"
  value       = google_cloud_run_v2_service.log.uri
}

output "vertex_endpoint_id" {
  description = "Vertex AI Endpoint ID (set as VERTEX_ENDPOINT_ID in backend .env)"
  value       = google_vertex_ai_endpoint.hiring.name
}

output "cert_kms_key" {
  description = "KMS key resource name for certificate signing"
  value       = "${google_kms_crypto_key.cert_signing.id}/cryptoKeyVersions/1"
}

output "log_kms_key" {
  description = "KMS key resource name for log tree-head signing"
  value       = "${google_kms_crypto_key.log_signing.id}/cryptoKeyVersions/1"
}

output "evidence_bucket" {
  value = google_storage_bucket.evidence.name
}

output "log_bucket" {
  value = google_storage_bucket.log.name
}
