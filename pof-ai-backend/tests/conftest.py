import os
import pytest

# Set required env vars for tests before any imports
os.environ.setdefault("GCP_PROJECT_ID", "test-project")
os.environ.setdefault("VERTEX_ENDPOINT_ID", "test-endpoint")
os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("KMS_KEY_CERT", "fake-kms-key")
os.environ.setdefault("KMS_KEY_LOG", "fake-kms-log-key")
os.environ.setdefault("GCS_BUCKET_EVIDENCE", "test-bucket")
os.environ.setdefault("CERT_BASE_URL", "https://verify.pof-ai.app/cert")
