"""
Tests for IntersectionalSurfaceEngine.

Critical test: "Gender Shades" pattern — a model that appears fair across
gender alone and race alone but is unfair at their intersection.
The engine must identify the intersectional subgroup as worst-case while
aggregate-only metrics miss it.
"""

import asyncio
import numpy as np
import pandas as pd
import pytest

from app.engines.intersectional import IntersectionalSurfaceEngine


def _gender_shades_df(n_per_group=200, seed=42):
    """
    Construct a dataset where:
    - Overall gender hire rates: male=50%, female=50% (fair-looking)
    - Overall ethnicity hire rates: white=50%, black=50% (fair-looking)
    - BUT: Black women are only hired 25% of the time (biased intersection)
    """
    rng = np.random.default_rng(seed)
    rows = []
    for gender in ["male", "female"]:
        for eth in ["white", "black"]:
            for _ in range(n_per_group):
                if gender == "female" and eth == "black":
                    # Score biased low so score>=0.5 captures discrimination
                    score = rng.uniform(0.15, 0.44)
                else:
                    score = rng.uniform(0.55, 0.92)
                hired = int(score >= 0.5)
                age = int(rng.integers(25, 45))
                rows.append({
                    "gender": gender, "ethnicity": eth,
                    "age": age, "age_bucket": "25-34" if age < 35 else "35-44",
                    "score": score, "hired": hired,
                })
    return pd.DataFrame(rows)


@pytest.mark.asyncio
async def test_gender_shades_identifies_intersectional_worst():
    """
    The engine must catch 'female × black' as worst subgroup
    even though marginal gender and race metrics look acceptable.
    """
    engine = IntersectionalSurfaceEngine()
    df = _gender_shades_df()

    report = await engine.evaluate(df)

    worst = report["worst_subgroup"]
    assert "female" in worst.lower() or "black" in worst.lower(), (
        f"Expected worst subgroup to contain 'female' or 'black', got: {worst}"
    )
    assert report["worst_disparity_score"] > 0.1, (
        f"Expected disparity > 0.1, got: {report['worst_disparity_score']}"
    )


@pytest.mark.asyncio
async def test_surface_grid_populated():
    engine = IntersectionalSurfaceEngine()
    df = _gender_shades_df()
    report = await engine.evaluate(df)
    assert len(report["surface_grid"]) > 0, "Surface grid should have points"
    for pt in report["surface_grid"]:
        assert "x" in pt and "y" in pt and "z" in pt


@pytest.mark.asyncio
async def test_empty_df_returns_gracefully():
    engine = IntersectionalSurfaceEngine()
    report = await engine.evaluate(pd.DataFrame())
    assert report["worst_subgroup"] == "N/A"
    assert report["subgroups"] == []


@pytest.mark.asyncio
async def test_all_subgroup_fields_present():
    engine = IntersectionalSurfaceEngine()
    df = _gender_shades_df()
    report = await engine.evaluate(df)
    for sub in report["subgroups"]:
        assert "label" in sub
        assert "sample_size" in sub
        assert "selection_rate" in sub
        assert "disparity_score" in sub
        assert sub["sample_size"] >= 30
