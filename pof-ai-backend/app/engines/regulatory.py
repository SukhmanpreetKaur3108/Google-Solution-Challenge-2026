from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from app.clients import gemini as gemini_client

logger = logging.getLogger(__name__)

_KB_PATH = Path(__file__).parent / "regulations.yaml"


class ClauseResult(BaseModel):
    clause_id: str
    obligation: str
    status: str  # PASS / FAIL / NEEDS_REVIEW
    explanation: str
    remediation: str | None = None


class ComplianceReport(BaseModel):
    clause_results: list[ClauseResult]
    compliance_percent: float
    failed_clauses: list[str]
    remediation_suggestions: list[str]


def _load_kb() -> dict[str, Any]:
    with open(_KB_PATH, "r") as f:
        return yaml.safe_load(f)


def _get_metric(reports: dict[str, Any], metric_name: str) -> float | None:
    """Extract a named metric from the combined engine reports."""
    mapping = {
        "statistical_score": ("statistical", "bias_score"),
        "adversarial_flip_rate": ("adversarial", "flip_rate"),
        "causal_counterfactual_score": ("causal", "counterfactual_fairness_score"),
        "regulatory_compliance_percent": None,
    }
    path = mapping.get(metric_name)
    if path is None:
        return None
    try:
        return float(reports[path[0]][path[1]])
    except (KeyError, TypeError, ValueError):
        return None


def _evaluate_clause(
    clause_id: str,
    entry: dict[str, Any],
    reports: dict[str, Any],
) -> ClauseResult:
    metric_name = entry.get("metric", "")
    threshold = float(entry.get("threshold", 0.0))
    operator = entry.get("operator", "gte")
    obligation = entry.get("obligation", "").strip()

    value = _get_metric(reports, metric_name)
    if value is None:
        return ClauseResult(
            clause_id=clause_id,
            obligation=obligation,
            status="NEEDS_REVIEW",
            explanation=f"Metric '{metric_name}' not available — manual review required.",
        )

    if operator == "gte":
        passed = value >= threshold
    elif operator == "lte":
        passed = value <= threshold
    else:
        passed = False

    if passed:
        status = "PASS"
        explanation = f"{metric_name}={value:.3f} meets requirement ({operator} {threshold})."
    else:
        status = "FAIL"
        explanation = f"{metric_name}={value:.3f} does NOT meet requirement ({operator} {threshold})."

    return ClauseResult(
        clause_id=clause_id,
        obligation=obligation,
        status=status,
        explanation=explanation,
    )


class RegulatoryComplianceEngine:
    def __init__(self) -> None:
        self._kb = _load_kb()

    async def evaluate(
        self,
        statistical_report: dict[str, Any],
        intersectional_report: dict[str, Any],
        causal_report: dict[str, Any],
        adversarial_report: dict[str, Any],
    ) -> dict[str, Any]:
        reports = {
            "statistical": statistical_report,
            "intersectional": intersectional_report,
            "causal": causal_report,
            "adversarial": adversarial_report,
        }

        results: list[ClauseResult] = []
        for clause_id, entry in self._kb.items():
            results.append(_evaluate_clause(clause_id, entry, reports))

        total = len(results)
        passed = sum(1 for r in results if r.status == "PASS")
        compliance_pct = (passed / total * 100.0) if total > 0 else 100.0
        failed = [r.clause_id for r in results if r.status == "FAIL"]

        # Generate remediation for failed clauses via Gemini
        remediation_suggestions: list[str] = []
        if failed:
            try:
                rems = await self._generate_remediation(
                    [r for r in results if r.status == "FAIL"], reports
                )
                remediation_suggestions = rems
                # Attach to individual clause results
                for r in results:
                    if r.status == "FAIL" and rems:
                        r.remediation = rems.pop(0) if rems else None
            except Exception as exc:
                logger.warning("Gemini remediation generation failed: %s", exc)
                for r in results:
                    if r.status == "FAIL":
                        r.remediation = f"Improve {r.clause_id.split('.')[0]} compliance by reducing bias in training data and model outputs."

        return ComplianceReport(
            clause_results=results,
            compliance_percent=round(compliance_pct, 2),
            failed_clauses=failed,
            remediation_suggestions=remediation_suggestions,
        ).model_dump()

    async def _generate_remediation(
        self,
        failed_results: list[ClauseResult],
        reports: dict[str, Any],
    ) -> list[str]:
        prompt = "You are an AI compliance expert. For each failing regulatory clause, provide one concrete, actionable remediation suggestion.\n\nFailing clauses:\n"
        for r in failed_results:
            prompt += f"\n- [{r.clause_id}] {r.obligation[:200]}... Current status: {r.explanation}"

        response = await gemini_client.generate_text(prompt, temperature=0.3)
        lines = [line.strip("- •*").strip() for line in response.split("\n") if line.strip()]
        return [l for l in lines if len(l) > 20]
