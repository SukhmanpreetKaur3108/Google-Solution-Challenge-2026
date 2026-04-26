"""
Tests for FairnessCertificate — sign/verify round-trip and tamper detection.
"""

import json
import pytest

from app.cert.certificate import FairnessCertificate, sign, verify, chain_hash


def _sample_cert(**kwargs) -> FairnessCertificate:
    defaults = dict(
        certificate_id="test-cert-001",
        issued_at="2026-04-25T10:00:00Z",
        model_id="default",
        model_version="1.0",
        decision_id="decision-001",
        decision_summary="Hire: James Smith",
        statistical_score=0.91,
        intersectional_worst_subgroup="N/A",
        causal_counterfactual_score=0.88,
        adversarial_flip_rate=0.05,
        regulatory_compliance_percent=91.7,
        regulatory_failures=[],
        evidence_uri="gs://pof-ai-evidence/test.json",
        previous_certificate_hash="",
        signature="",
    )
    defaults.update(kwargs)
    return FairnessCertificate(**defaults)


def test_sign_produces_demo_signature():
    cert = _sample_cert()
    signed = sign(cert, "fake-kms-key")
    # KMS unavailable in test — falls back to DEMO-SHA256
    assert signed.signature.startswith("DEMO-SHA256:")


def test_verify_valid_demo_signature():
    cert = _sample_cert()
    signed = sign(cert, "fake-kms-key")
    assert verify(signed, "unused-public-key-for-demo") is True


def test_tamper_detected():
    cert = _sample_cert()
    signed = sign(cert, "fake-kms-key")
    # Tamper with a field
    tampered = signed.model_copy(update={"statistical_score": 0.99})
    assert verify(tampered, "unused") is False


def test_tamper_detected_on_decision():
    cert = _sample_cert()
    signed = sign(cert, "fake-kms-key")
    tampered = signed.model_copy(update={"decision_summary": "Hire: IMPERSONATOR"})
    assert verify(tampered, "unused") is False


def test_chain_hash_changes_on_mutation():
    cert_a = _sample_cert(certificate_id="cert-a")
    cert_b = _sample_cert(certificate_id="cert-b")
    signed_a = sign(cert_a, "fake")
    signed_b = sign(cert_b, "fake")
    hash_a = chain_hash(signed_a)
    hash_b = chain_hash(signed_b)
    assert hash_a != hash_b
    assert len(hash_a) == 64  # SHA-256 hex


def test_all_cert_fields_survive_round_trip():
    cert = _sample_cert(regulatory_failures=["eu_ai_act.art_10", "gdpr.art_22"])
    signed = sign(cert, "fake")
    d = signed.model_dump()
    assert d["regulatory_failures"] == ["eu_ai_act.art_10", "gdpr.art_22"]
    assert d["statistical_score"] == 0.91
    assert d["adversarial_flip_rate"] == 0.05
