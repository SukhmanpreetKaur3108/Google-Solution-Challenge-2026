from __future__ import annotations

import os
from typing import Any

from google.cloud import firestore


_db: firestore.AsyncClient | None = None


def _get_db() -> firestore.AsyncClient:
    global _db
    if _db is None:
        _db = firestore.AsyncClient(project=os.environ["GCP_PROJECT_ID"])
    return _db


async def write_certificate(certificate_id: str, data: dict[str, Any]) -> None:
    db = _get_db()
    collection = os.environ.get("FIRESTORE_COLLECTION_CERTIFICATES", "certificates")
    await db.collection(collection).document(certificate_id).set(data)


async def read_certificate(certificate_id: str) -> dict[str, Any] | None:
    db = _get_db()
    collection = os.environ.get("FIRESTORE_COLLECTION_CERTIFICATES", "certificates")
    doc = await db.collection(collection).document(certificate_id).get()
    return doc.to_dict() if doc.exists else None


async def list_certificates(limit: int = 50) -> list[dict[str, Any]]:
    db = _get_db()
    collection = os.environ.get("FIRESTORE_COLLECTION_CERTIFICATES", "certificates")
    docs = db.collection(collection).order_by(
        "issued_at", direction=firestore.Query.DESCENDING
    ).limit(limit).stream()
    results = []
    async for doc in docs:
        results.append({"id": doc.id, **doc.to_dict()})
    return results
