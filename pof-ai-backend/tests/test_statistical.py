"""
Tests for StatisticalFairnessEngine — proves true positives (biased data flagged)
and true negatives (fair data passes).
"""

import asyncio
import numpy as np
import pandas as pd
import pytest

from app.engines.statistical import StatisticalFairnessEngine, DIFF_THRESHOLD


def _make_df(n=500, biased=True, seed=42):
    rng = np.random.default_rng(seed)
    genders    = rng.choice(["male", "female"], size=n)
    ethnicities = rng.choice(["white", "black"], size=n)
    ages       = rng.integers(25, 55, size=n)
    exp        = rng.integers(1, 20, size=n)
    skills     = rng.integers(1, 10, size=n)

    # Scale to [0,1] centred near 0.5 so the 0.5 threshold is meaningful
    merit = np.clip(exp / 40 + skills / 20, 0, 1)
    score = merit + rng.normal(0, 0.04, size=n)
    score = np.clip(score, 0, 1)

    minority_mask = (genders == "female") | (ethnicities == "black")
    if biased:
        # Push minority scores down by 0.22 — large enough to cross the 0.1 DP threshold
        score[minority_mask] -= 0.22
        score = np.clip(score, 0, 1)

    hired = (score >= 0.5).astype(int)

    age_bucket = []
    for a in ages:
        if a < 35: age_bucket.append("25-34")
        elif a < 45: age_bucket.append("35-44")
        else: age_bucket.append("45-54")

    return pd.DataFrame({
        "gender": genders, "ethnicity": ethnicities,
        "age": ages, "age_bucket": age_bucket,
        "score": score, "hired": hired,
    })


@pytest.mark.asyncio
async def test_biased_data_is_flagged():
    engine = StatisticalFairnessEngine()
    df = _make_df(biased=True)
    prediction = {"score": 0.65, "should_hire": True}
    applicant  = {"gender": "female", "ethnicity": "white", "age": 30}

    report = await engine.evaluate(prediction, applicant, df)

    # Must flag at least one metric for gender or ethnicity
    assert len(report["flagged_metrics"]) > 0, "Expected at least one flagged metric on biased data"
    assert report["bias_score"] < 0.9, f"Bias score too high on biased data: {report['bias_score']}"


@pytest.mark.asyncio
async def test_fair_data_passes():
    engine = StatisticalFairnessEngine()
    df = _make_df(biased=False)
    prediction = {"score": 0.65, "should_hire": True}
    applicant  = {"gender": "male", "ethnicity": "white", "age": 30}

    report = await engine.evaluate(prediction, applicant, df)

    # May have a flag or two due to sampling noise, but bias_score should be high
    assert report["bias_score"] >= 0.7, f"Fair data produced low bias_score: {report['bias_score']}"


@pytest.mark.asyncio
async def test_empty_dataframe_returns_fallback():
    engine = StatisticalFairnessEngine()
    report = await engine.evaluate({}, {}, pd.DataFrame())
    assert report["bias_score"] == 1.0
    assert "insufficient_data" in report["flagged_metrics"]
    assert report["sample_size"] == 0


@pytest.mark.asyncio
async def test_report_has_required_fields():
    engine = StatisticalFairnessEngine()
    df = _make_df(biased=True)
    report = await engine.evaluate({"score": 0.5}, {"gender": "male"}, df)
    assert "bias_score" in report
    assert "flagged_metrics" in report
    assert "per_attribute_metrics" in report
    assert "sample_size" in report
    assert 0.0 <= report["bias_score"] <= 1.0
