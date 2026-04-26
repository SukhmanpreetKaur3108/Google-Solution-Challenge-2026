variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "artifact_registry_repo" {
  description = "Artifact Registry repository name"
  type        = string
  default     = "pof-ai-repo"
}

variable "backend_image" {
  description = "Docker image for pof-ai-backend"
  type        = string
  default     = "us-central1-docker.pkg.dev/YOUR_PROJECT/pof-ai-repo/pof-ai-backend:latest"
}

variable "log_image" {
  description = "Docker image for pof-ai-log"
  type        = string
  default     = "us-central1-docker.pkg.dev/YOUR_PROJECT/pof-ai-repo/pof-ai-log:latest"
}

variable "gemini_api_key" {
  description = "Gemini API key (stored in Secret Manager)"
  type        = string
  sensitive   = true
}

variable "api_key" {
  description = "API Gateway key for service authentication"
  type        = string
  sensitive   = true
}
