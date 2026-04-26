"""
Tests for AdversarialRedTeamEngine — mocks Gemini and Vertex AI.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.engines.adversarial import AdversarialRedTeamEngine


SAMPLE_APPLICANT = {
    "name": "James Smith", "age": 32, "gender": "male", "ethnicity": "white",
    "education": "master", "years_experience": 7,
    "skills": ["python", "sql", "ml"], "current_employer": "Google",
}

SAMPLE_PREDICTION = {"score": 0.72, "should_hire": True}

MOCK_GEMINI_PROBES = [
    {"name": "Lakisha Jones", "gender": "female", "ethnicity": "black",
     "age": 32, "years_experience": 7, "education": "master",
     "skills": ["python", "sql", "ml"], "current_employer": "Google"},
    {"name": "Carlos Garcia", "gender": "male", "ethnicity": "hispanic",
     "age": 32, "years_experience": 7, "education": "master",
     "skills": ["python", "sql", "ml"], "current_employer": "Google"},
]


@pytest.mark.asyncio
async def test_engine_returns_required_fields():
    engine = AdversarialRedTeamEngine()

    # Mock Gemini to return probes
    with patch("app.engines.adversarial.gemini_client.generate_json",
               new_callable=AsyncMock) as mock_gemini, \
         patch("app.engines.adversarial.vertex_client.predict_batch",
               new_callable=AsyncMock) as mock_vertex:

        mock_gemini.return_value = {
            "probes": MOCK_GEMINI_PROBES,
            "bias_pattern_summary": "Female and Hispanic names score lower.",
        }
        mock_vertex.return_value = [
            {"score": 0.55, "should_hire": True},  # flip
            {"score": 0.45, "should_hire": False},  # flip
        ]

        report = await engine.evaluate(SAMPLE_PREDICTION, SAMPLE_APPLICANT)

    assert "flip_rate" in report
    assert "probes" in report
    assert "bias_pattern_summary" in report
    assert "most_damaging_probe" in report
    assert 0.0 <= report["flip_rate"] <= 1.0


@pytest.mark.asyncio
async def test_flip_rate_calculated_correctly():
    engine = AdversarialRedTeamEngine()

    with patch("app.engines.adversarial.gemini_client.generate_json",
               new_callable=AsyncMock) as mock_gemini, \
         patch("app.engines.adversarial.vertex_client.predict_batch",
               new_callable=AsyncMock) as mock_vertex:

        mock_gemini.return_value = {
            "probes": MOCK_GEMINI_PROBES,
            "bias_pattern_summary": "Test summary",
        }
        # Original score 0.72 → hire; probe scores 0.45 and 0.40 → reject (both flip)
        mock_vertex.return_value = [
            {"score": 0.45, "should_hire": False},
            {"score": 0.40, "should_hire": False},
        ]

        report = await engine.evaluate(SAMPLE_PREDICTION, SAMPLE_APPLICANT)

    assert report["flip_rate"] == 1.0  # 2/2 flipped


@pytest.mark.asyncio
async def test_gemini_failure_uses_fallback():
    engine = AdversarialRedTeamEngine()

    with patch("app.engines.adversarial.gemini_client.generate_json",
               side_effect=Exception("Gemini unavailable")), \
         patch("app.engines.adversarial.vertex_client.predict_batch",
               new_callable=AsyncMock) as mock_vertex:

        mock_vertex.return_value = [{"score": 0.65, "should_hire": True}] * 10

        report = await engine.evaluate(SAMPLE_PREDICTION, SAMPLE_APPLICANT)

    assert report["fallback_used"] is True
    assert len(report["probes"]) > 0


@pytest.mark.asyncio
async def test_no_flips_gives_zero_flip_rate():
    engine = AdversarialRedTeamEngine()

    with patch("app.engines.adversarial.gemini_client.generate_json",
               new_callable=AsyncMock) as mock_gemini, \
         patch("app.engines.adversarial.vertex_client.predict_batch",
               new_callable=AsyncMock) as mock_vertex:

        mock_gemini.return_value = {
            "probes": MOCK_GEMINI_PROBES,
            "bias_pattern_summary": "No bias found.",
        }
        # All probes get same score as original
        mock_vertex.return_value = [
            {"score": 0.72, "should_hire": True},
            {"score": 0.71, "should_hire": True},
        ]

        report = await engine.evaluate(SAMPLE_PREDICTION, SAMPLE_APPLICANT)

    assert report["flip_rate"] == 0.0
