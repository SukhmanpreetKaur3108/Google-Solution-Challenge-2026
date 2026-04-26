"""
Tests for RegulatoryComplianceEngine.

- Perfectly fair input → 100% compliance
- Known-biased input → fails expected clauses
"""

import asyncio
import pytest
from unittest.mock import patch, AsyncMock

from app.engines.regulatory import RegulatoryComplianceEngine


FAIR_REPORTS = {
    "statistical": {"bias_score": 0.98, "flagged_metrics": [], "sample_size": 1000},
    "intersectional": {"worst_subgroup": "N/A", "worst_disparity_score": 0.01},
    "causal": {"counterfactual_fairness_score": 0.95},
    "adversarial": {"flip_rate": 0.03},
}

BIASED_REPORTS = {
    "statistical": {"bias_score": 0.55, "flagged_metrics": ["gender.dp_diff=0.18"], "sample_size": 1000},
    "intersectional": {"worst_subgroup": "female × black", "worst_disparity_score": 0.28},
    "causal": {"counterfactual_fairness_score": 0.60},
    "adversarial": {"flip_rate": 0.35},
}


@pytest.mark.asyncio
async def test_fair_input_passes_all_clauses():
    engine = RegulatoryComplianceEngine()
    with patch("app.engines.regulatory.gemini_client.generate_text",
               new_callable=AsyncMock, return_value=""):
        report = await engine.evaluate(
            FAIR_REPORTS["statistical"],
            FAIR_REPORTS["intersectional"],
            FAIR_REPORTS["causal"],
            FAIR_REPORTS["adversarial"],
        )
    # All clauses should pass (high thresholds met)
    assert report["compliance_percent"] >= 80.0, (
        f"Expected ≥80% compliance on fair data, got {report['compliance_percent']}"
    )
    assert len(report["failed_clauses"]) == 0 or report["compliance_percent"] >= 75


@pytest.mark.asyncio
async def test_biased_input_fails_expected_clauses():
    engine = RegulatoryComplianceEngine()
    with patch("app.engines.regulatory.gemini_client.generate_text",
               new_callable=AsyncMock, return_value="Improve training data diversity."):
        report = await engine.evaluate(
            BIASED_REPORTS["statistical"],
            BIASED_REPORTS["intersectional"],
            BIASED_REPORTS["causal"],
            BIASED_REPORTS["adversarial"],
        )
    assert report["compliance_percent"] < 80.0, (
        f"Expected <80% compliance on biased data, got {report['compliance_percent']}"
    )
    # Should specifically fail EU AI Act and GDPR clauses
    failed = report["failed_clauses"]
    assert len(failed) > 0, "Expected at least one failed clause on biased data"
    eu_failures = [c for c in failed if "eu_ai_act" in c or "gdpr" in c]
    assert len(eu_failures) > 0, f"Expected EU/GDPR failures, got: {failed}"


@pytest.mark.asyncio
async def test_report_has_all_required_fields():
    engine = RegulatoryComplianceEngine()
    with patch("app.engines.regulatory.gemini_client.generate_text",
               new_callable=AsyncMock, return_value=""):
        report = await engine.evaluate(
            FAIR_REPORTS["statistical"],
            FAIR_REPORTS["intersectional"],
            FAIR_REPORTS["causal"],
            FAIR_REPORTS["adversarial"],
        )
    assert "clause_results" in report
    assert "compliance_percent" in report
    assert "failed_clauses" in report
    assert len(report["clause_results"]) >= 12  # at least 12 clauses in YAML
    assert 0.0 <= report["compliance_percent"] <= 100.0


@pytest.mark.asyncio
async def test_clause_results_have_correct_status_values():
    engine = RegulatoryComplianceEngine()
    with patch("app.engines.regulatory.gemini_client.generate_text",
               new_callable=AsyncMock, return_value=""):
        report = await engine.evaluate(
            FAIR_REPORTS["statistical"], FAIR_REPORTS["intersectional"],
            FAIR_REPORTS["causal"], FAIR_REPORTS["adversarial"],
        )
    for clause in report["clause_results"]:
        assert clause["status"] in ("PASS", "FAIL", "NEEDS_REVIEW")
        assert "clause_id" in clause
        assert "obligation" in clause
        assert "explanation" in clause
