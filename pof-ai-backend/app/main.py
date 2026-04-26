from __future__ import annotations

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

try:
    import google.cloud.logging as cloud_logging
    cloud_logging.Client().setup_logging()
except Exception:
    logging.basicConfig(level=logging.INFO)

from app.models.schemas import ScoringRequest, ScoringResponse, FairnessScore, CertificateStatus
from app.orchestrator import FairnessOrchestrator
from app.cert.certificate import FairnessCertificate, sign
from app.clients import vertex as vertex_client
from app.clients import firestore as firestore_client

logger = logging.getLogger(__name__)

app = FastAPI(
    title="PoF-AI Backend",
    version="1.0.0",
    description="Proof-of-Fairness AI — every decision comes with a signed Fairness Certificate.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_orchestrator = FairnessOrchestrator()
_EXPECTED_API_KEY = os.environ.get("API_KEY", "")


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    if request.url.path in ("/", "/health", "/docs", "/openapi.json", "/redoc"):
        return await call_next(request)
    if _EXPECTED_API_KEY:
        key = request.headers.get("X-API-Key", "")
        if key != _EXPECTED_API_KEY:
            return JSONResponse(status_code=401, content={"detail": "Invalid API key"})
    return await call_next(request)


@app.get("/")
async def root():
    return {"message": "PoF-AI Backend is running", "docs": "/docs", "health": "/health"}


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/score", response_model=ScoringResponse)
async def score(request: ScoringRequest) -> ScoringResponse:
    logger.info("Scoring request for applicant: %s", request.applicant.name)

    applicant_dict = request.applicant.model_dump()
    features = {
        "years_experience": request.applicant.years_experience,
        "skills_count": len(request.applicant.skills),
        "education": request.applicant.education,
        "gender": request.applicant.gender,
        "ethnicity": request.applicant.ethnicity,
        "age": request.applicant.age,
    }

    try:
        prediction = await vertex_client.predict(features)
    except Exception as exc:
        logger.warning("Vertex AI unavailable, using fallback scoring: %s", exc)
        from sklearn.linear_model import LogisticRegression
        score_val = min(1.0, max(0.0, request.applicant.years_experience / 10 +
                                 len(request.applicant.skills) * 0.05))
        prediction = {"score": score_val, "should_hire": score_val >= 0.5, "attributions": {}}

    fairness_reports = await _orchestrator.evaluate(prediction, applicant_dict)

    stat = fairness_reports["statistical"]
    inter = fairness_reports["intersectional"]
    causal = fairness_reports["causal"]
    adv = fairness_reports["adversarial"]
    reg = fairness_reports["regulatory"]

    decision_id = str(uuid.uuid4())
    certificate_id = str(uuid.uuid4())
    base_url = os.environ.get("CERT_BASE_URL", "https://verify.pof-ai.app/cert")

    statistical_score = stat.get("bias_score", 1.0)
    intersectional_worst = inter.get("worst_subgroup", "N/A")
    causal_score = causal.get("counterfactual_fairness_score", 1.0)
    flip_rate = adv.get("flip_rate", 0.0)
    compliance_pct = reg.get("compliance_percent", 100.0)
    reg_failures = reg.get("failed_clauses", [])

    overall_score = (statistical_score + causal_score + (1 - flip_rate)) / 3
    if overall_score >= 0.8 and compliance_pct >= 80:
        status = CertificateStatus.FAIR
    elif overall_score >= 0.6 or compliance_pct >= 60:
        status = CertificateStatus.REVIEW_NEEDED
    else:
        status = CertificateStatus.BIASED

    cert = FairnessCertificate(
        certificate_id=certificate_id,
        issued_at=datetime.now(timezone.utc).isoformat(),
        model_id=request.model_id,
        model_version="1.0",
        decision_id=decision_id,
        decision_summary=f"{'Hire' if prediction['should_hire'] else 'Reject'}: {request.applicant.name}",
        statistical_score=statistical_score,
        intersectional_worst_subgroup=str(intersectional_worst),
        causal_counterfactual_score=causal_score,
        adversarial_flip_rate=flip_rate,
        regulatory_compliance_percent=compliance_pct,
        regulatory_failures=reg_failures,
        evidence_uri=f"gs://{os.environ.get('GCS_BUCKET_EVIDENCE', 'pof-ai-evidence')}/{certificate_id}.json",
        previous_certificate_hash="",
        signature="",
    )

    kms_key = os.environ.get(
        "KMS_KEY_CERT",
        f"projects/{os.environ.get('GCP_PROJECT_ID','demo')}/locations/global/keyRings/pof-ai-keyring/cryptoKeys/cert-signing-key/cryptoKeyVersions/1",
    )
    try:
        signed_cert = sign(cert, kms_key)
    except Exception as exc:
        logger.warning("KMS signing unavailable, using demo signature: %s", exc)
        import hashlib, json
        canon = json.dumps(cert.model_dump(), sort_keys=True, separators=(",", ":"))
        signed_cert = cert.model_copy(update={"signature": "DEMO:" + hashlib.sha256(canon.encode()).hexdigest()})

    cert_dict = signed_cert.model_dump()
    cert_dict["@context"] = "https://pof-ai.app/context/v1"
    cert_dict["@type"] = "FairnessCertificate"

    try:
        await firestore_client.write_certificate(certificate_id, cert_dict)
    except Exception as exc:
        logger.warning("Firestore write failed: %s", exc)

    return ScoringResponse(
        decision_id=decision_id,
        candidate_score=prediction["score"],
        should_hire=prediction["should_hire"],
        certificate_id=certificate_id,
        certificate_status=status,
        fairness=FairnessScore(
            statistical_score=statistical_score,
            intersectional_worst_subgroup=str(intersectional_worst),
            causal_counterfactual_score=causal_score,
            adversarial_flip_rate=flip_rate,
            regulatory_compliance_percent=compliance_pct,
            regulatory_failures=reg_failures,
        ),
        verification_url=f"{base_url}/{certificate_id}",
        certificate_json=cert_dict,
    )


@app.get("/cert/{certificate_id}")
async def get_certificate(certificate_id: str):
    cert = await firestore_client.read_certificate(certificate_id)
    if cert is None:
        raise HTTPException(status_code=404, detail="Certificate not found")
    return cert
