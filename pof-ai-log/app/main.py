from __future__ import annotations

"""
pof-ai-log — Append-only Merkle Audit Log Service (RFC 6962-style).

Endpoints:
  POST /append       — append a signed FairnessCertificate leaf → returns inclusion proof + signed tree head
  GET  /entry/{idx}  — return leaf data + inclusion proof
  GET  /sth          — latest signed tree head
  GET  /verify/{cert_id} — inclusion proof for a given certificate ID
"""

import base64
import hashlib
import json
import logging
import os
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.merkle import MerkleTree

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PoF-AI Merkle Audit Log",
    version="1.0.0",
    description="Append-only RFC 6962-style certificate transparency log for Fairness Certificates.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory tree (backed by Firestore/GCS in production)
_tree = MerkleTree()
_entries: list[dict] = []          # list of {cert_id, data_json, index}
_cert_id_to_index: dict[str, int] = {}


# ── Pydantic models ──────────────────────────────────────────────────────────

class AppendRequest(BaseModel):
    certificate: dict


class InclusionProof(BaseModel):
    leaf_index: int
    tree_size: int
    leaf_hash: str
    proof_hashes: list[str]
    merkle_root: str
    signed_tree_head: dict


class AppendResponse(BaseModel):
    leaf_index: int
    merkle_root: str
    inclusion_proof: InclusionProof
    signed_tree_head: dict


class LeafResponse(BaseModel):
    leaf_index: int
    certificate: dict
    inclusion_proof: InclusionProof


class SignedTreeHead(BaseModel):
    tree_size: int
    merkle_root: str
    timestamp: str
    signature: str


# ── Helpers ──────────────────────────────────────────────────────────────────

def _sign_tree_head(root: str, size: int) -> dict:
    """Sign the tree head with Cloud KMS (or demo SHA-256 fallback)."""
    payload = json.dumps({"root": root, "size": size}, sort_keys=True).encode()
    try:
        from google.cloud import kms
        kms_key = os.environ.get(
            "KMS_KEY_LOG",
            f"projects/{os.environ.get('GCP_PROJECT_ID','demo')}/locations/global"
            f"/keyRings/pof-ai-keyring/cryptoKeys/log-signing-key/cryptoKeyVersions/1",
        )
        client = kms.KeyManagementServiceClient()
        response = client.asymmetric_sign(request={"name": kms_key, "data": payload})
        sig = "Ed25519:" + base64.b64encode(response.signature).decode()
    except Exception:
        sig = "DEMO-SHA256:" + hashlib.sha256(payload).hexdigest()

    return {
        "tree_size": size,
        "merkle_root": root,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signature": sig,
    }


def _build_proof_response(index: int) -> InclusionProof:
    root = _tree.root_hex()
    raw_proof = _tree.inclusion_proof(index)
    entry = _entries[index]
    leaf_hash = hashlib.sha256(b"\x00" + entry["data_bytes"]).hexdigest()
    sth = _sign_tree_head(root, len(_entries))
    return InclusionProof(
        leaf_index=index,
        tree_size=len(_entries),
        leaf_hash=leaf_hash,
        proof_hashes=[p.hex() for p in raw_proof],
        merkle_root=root,
        signed_tree_head=sth,
    )


def _persist_to_gcs(index: int, entry: dict):
    """Optional: persist leaf to Cloud Storage for durability."""
    try:
        from google.cloud import storage
        bucket_name = os.environ.get("GCS_BUCKET_LOG", "pof-ai-log")
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(f"leaves/{index:010d}.json")
        blob.upload_from_string(json.dumps(entry["cert"]), content_type="application/json")
    except Exception as e:
        logger.warning("GCS persist skipped: %s", e)


# ── Routes ───────────────────────────────────────────────────────────────────

@app.post("/append", response_model=AppendResponse)
async def append(request: AppendRequest):
    cert = request.certificate
    cert_id = cert.get("certificate_id", "")
    if cert_id in _cert_id_to_index:
        raise HTTPException(status_code=409, detail=f"Certificate {cert_id} already in log")

    data_bytes = json.dumps(cert, sort_keys=True, separators=(",", ":")).encode()
    index = _tree.append(data_bytes)
    _entries.append({"cert_id": cert_id, "data_bytes": data_bytes, "cert": cert})
    _cert_id_to_index[cert_id] = index

    _persist_to_gcs(index, _entries[index])

    root = _tree.root_hex()
    proof = _build_proof_response(index)
    sth = _sign_tree_head(root, len(_entries))

    logger.info("Appended cert %s at index %d, root=%s", cert_id, index, root[:16])
    return AppendResponse(
        leaf_index=index,
        merkle_root=root,
        inclusion_proof=proof,
        signed_tree_head=sth,
    )


@app.get("/entry/{idx}", response_model=LeafResponse)
async def get_entry(idx: int):
    if idx < 0 or idx >= len(_entries):
        raise HTTPException(status_code=404, detail=f"Index {idx} not in log")
    entry = _entries[idx]
    proof = _build_proof_response(idx)
    return LeafResponse(
        leaf_index=idx,
        certificate=entry["cert"],
        inclusion_proof=proof,
    )


@app.get("/sth", response_model=SignedTreeHead)
async def signed_tree_head():
    root = _tree.root_hex() or "0" * 64
    sth = _sign_tree_head(root, len(_entries))
    return SignedTreeHead(**sth)


@app.get("/verify/{cert_id}")
async def verify_certificate(cert_id: str):
    if cert_id not in _cert_id_to_index:
        raise HTTPException(status_code=404, detail=f"Certificate {cert_id} not found in log")
    index = _cert_id_to_index[cert_id]
    proof = _build_proof_response(index)
    root = _tree.root_hex()
    sth = _sign_tree_head(root, len(_entries))
    return {
        "cert_id": cert_id,
        "leaf_index": index,
        "inclusion_proof": proof.model_dump(),
        "signed_tree_head": sth,
        "verified": True,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "tree_size": len(_entries), "root": _tree.root_hex()}
