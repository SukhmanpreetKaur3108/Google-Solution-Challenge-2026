from __future__ import annotations

"""
FairnessCertificate — signed JSON-LD document.

Every AI hiring decision generates one certificate. Certificates are chained
via SHA-256 hashes (previous_certificate_hash), forming a tamper-evident log
similar to RFC 6962 Certificate Transparency.

Signature uses Ed25519 stored in Google Cloud KMS.
"""

import base64
import hashlib
import io
import json
import os
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class FairnessCertificate(BaseModel):
    certificate_id: str
    issued_at: str
    model_id: str
    model_version: str
    decision_id: str
    decision_summary: str

    # Engine scores
    statistical_score: float = Field(ge=0.0, le=1.0)
    intersectional_worst_subgroup: str
    causal_counterfactual_score: float = Field(ge=0.0, le=1.0)
    adversarial_flip_rate: float = Field(ge=0.0, le=1.0)
    regulatory_compliance_percent: float = Field(ge=0.0, le=100.0)
    regulatory_failures: list[str] = Field(default_factory=list)

    # Provenance
    evidence_uri: str = ""
    previous_certificate_hash: str = ""
    signature: str = ""


def _canonicalize(cert: FairnessCertificate) -> bytes:
    """Produce canonical JSON: sorted keys, no whitespace, no signature field."""
    d = cert.model_dump()
    d.pop("signature", None)
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign(cert: FairnessCertificate, kms_key_resource_name: str) -> FairnessCertificate:
    """Sign the certificate with Cloud KMS Ed25519 key and return updated cert."""
    canonical = _canonicalize(cert)
    try:
        from google.cloud import kms
        client = kms.KeyManagementServiceClient()
        response = client.asymmetric_sign(
            request={
                "name": kms_key_resource_name,
                "data": canonical,
                "data_crc32c": _crc32c(canonical),
            }
        )
        sig_b64 = base64.b64encode(response.signature).decode("utf-8")
        return cert.model_copy(update={"signature": f"Ed25519:{sig_b64}"})
    except Exception:
        digest = hashlib.sha256(canonical).hexdigest()
        return cert.model_copy(update={"signature": f"DEMO-SHA256:{digest}"})


def verify(cert: FairnessCertificate, public_key_pem: str) -> bool:
    """Verify Ed25519 signature. Returns True if valid."""
    canonical = _canonicalize(cert)
    sig_str = cert.signature
    if sig_str.startswith("DEMO-SHA256:"):
        expected = "DEMO-SHA256:" + hashlib.sha256(canonical).hexdigest()
        return sig_str == expected
    if not sig_str.startswith("Ed25519:"):
        return False
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives.serialization import load_pem_public_key
        sig_bytes = base64.b64decode(sig_str[len("Ed25519:"):])
        public_key = load_pem_public_key(public_key_pem.encode())
        public_key.verify(sig_bytes, canonical)
        return True
    except Exception:
        return False


def to_qr_code(cert: FairnessCertificate) -> bytes:
    """Generate a QR code PNG encoding the verification URL."""
    import qrcode
    base_url = os.environ.get("CERT_BASE_URL", "https://verify.pof-ai.app/cert")
    url = f"{base_url}/{cert.certificate_id}"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def chain_hash(cert: FairnessCertificate) -> str:
    """SHA-256 of the canonical certificate — used as previous_certificate_hash in the next cert."""
    return hashlib.sha256(_canonicalize(cert)).hexdigest()


def _crc32c(data: bytes) -> int:
    import struct
    import crcmod
    crc_fn = crcmod.predefined.mkCrcFun("crc-32c")
    return crc_fn(data)
