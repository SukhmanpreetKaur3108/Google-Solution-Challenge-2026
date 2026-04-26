from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
import uuid


class Applicant(BaseModel):
    name: str
    age: int
    gender: str
    ethnicity: str
    education: str
    years_experience: int
    skills: list[str]
    current_employer: str


class ScoringRequest(BaseModel):
    applicant: Applicant
    job_description: str
    model_id: str = "default"


class FairnessScore(BaseModel):
    statistical_score: float = Field(ge=0.0, le=1.0)
    intersectional_worst_subgroup: str
    causal_counterfactual_score: float = Field(ge=0.0, le=1.0)
    adversarial_flip_rate: float = Field(ge=0.0, le=1.0)
    regulatory_compliance_percent: float = Field(ge=0.0, le=100.0)
    regulatory_failures: list[str] = Field(default_factory=list)


class CertificateStatus(str, Enum):
    FAIR = "FAIR"
    REVIEW_NEEDED = "REVIEW_NEEDED"
    BIASED = "BIASED"


class ScoringResponse(BaseModel):
    decision_id: str
    candidate_score: float
    should_hire: bool
    certificate_id: str
    certificate_status: CertificateStatus
    fairness: FairnessScore
    verification_url: str
    certificate_json: dict[str, Any]


class StatisticalMetricResult(BaseModel):
    metric_name: str
    value: float
    threshold: float
    passed: bool


class SubgroupResult(BaseModel):
    label: str
    sample_size: int
    selection_rate: float
    true_positive_rate: float
    disparity_score: float


class SurfacePoint(BaseModel):
    x: float
    y: float
    z: float
    value: float
    label: str


class AdversarialProbe(BaseModel):
    probe_applicant: dict[str, Any]
    original_score: float
    probe_score: float
    decision_flipped: bool
    score_delta: float


class ClauseResult(BaseModel):
    clause_id: str
    obligation: str
    status: str  # PASS / FAIL / NEEDS_REVIEW
    explanation: str
    remediation: str | None = None
