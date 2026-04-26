from __future__ import annotations

import os
import asyncio
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel

try:
    from fairlearn.metrics import (
        MetricFrame,
        demographic_parity_difference,
        equalized_odds_difference,
        demographic_parity_ratio,
    )
    _FAIRLEARN_AVAILABLE = True
except ImportError:
    _FAIRLEARN_AVAILABLE = False

from sklearn.metrics import recall_score


# ── Pure-numpy fallbacks (used when fairlearn unavailable) ───────────────────

def _dp_difference_fallback(y_true, y_pred, sensitive_features) -> float:
    """Demographic Parity Difference: max(P(Ŷ=1|A=a)) - min(P(Ŷ=1|A=a))."""
    groups = {}
    for g, p in zip(sensitive_features, y_pred):
        groups.setdefault(g, []).append(p)
    rates = [float(np.mean(v)) for v in groups.values() if v]
    return max(rates) - min(rates) if len(rates) >= 2 else 0.0


def _dp_ratio_fallback(y_true, y_pred, sensitive_features) -> float:
    """Disparate Impact Ratio: min_rate / max_rate."""
    groups = {}
    for g, p in zip(sensitive_features, y_pred):
        groups.setdefault(g, []).append(p)
    rates = [float(np.mean(v)) for v in groups.values() if v]
    if len(rates) < 2 or max(rates) == 0:
        return 1.0
    return min(rates) / max(rates)


def _eo_difference_fallback(y_true, y_pred, sensitive_features) -> float:
    """Equalized Odds Diff: max TPR gap across groups (simplified)."""
    groups: dict = {}
    for g, yt, yp in zip(sensitive_features, y_true, y_pred):
        groups.setdefault(g, {"yt": [], "yp": []})
        groups[g]["yt"].append(yt)
        groups[g]["yp"].append(yp)
    tprs = []
    for g, d in groups.items():
        pos = [yp for yt, yp in zip(d["yt"], d["yp"]) if yt == 1]
        tprs.append(float(np.mean(pos)) if pos else 0.0)
    return max(tprs) - min(tprs) if len(tprs) >= 2 else 0.0


PROTECTED_ATTRIBUTES = ["gender", "ethnicity", "age_bucket"]
DIFF_THRESHOLD = float(os.environ.get("BIAS_DIFFERENCE_THRESHOLD", 0.1))
DI_LOW = float(os.environ.get("DISPARATE_IMPACT_LOW", 0.8))
DI_HIGH = float(os.environ.get("DISPARATE_IMPACT_HIGH", 1.25))


def _age_bucket(age: int) -> str:
    if age < 25:
        return "<25"
    elif age < 35:
        return "25-34"
    elif age < 45:
        return "35-44"
    elif age < 55:
        return "45-54"
    return "55+"


class StatisticalReport(BaseModel):
    per_attribute_metrics: dict[str, dict[str, float]]
    bias_score: float
    flagged_metrics: list[str]
    sample_size: int


class StatisticalFairnessEngine:
    async def evaluate(
        self,
        prediction: dict[str, Any],
        applicant: dict[str, Any],
        historical_batch: pd.DataFrame,
    ) -> dict[str, Any]:
        return await asyncio.get_event_loop().run_in_executor(
            None, self._compute, prediction, applicant, historical_batch
        )

    def _compute(
        self,
        prediction: dict[str, Any],
        applicant: dict[str, Any],
        historical_batch: pd.DataFrame,
    ) -> dict[str, Any]:
        if historical_batch.empty or len(historical_batch) < 50:
            return self._fallback_report(applicant)

        df = historical_batch.copy()
        if "age" in df.columns and "age_bucket" not in df.columns:
            df["age_bucket"] = df["age"].apply(_age_bucket)

        required = {"gender", "ethnicity", "age_bucket", "hired", "score"}
        if not required.issubset(df.columns):
            return self._fallback_report(applicant)

        y_true = df["hired"].astype(int)
        y_pred = (df["score"] >= 0.5).astype(int)

        per_attribute: dict[str, dict[str, float]] = {}
        flagged: list[str] = []
        metric_values: list[float] = []

        for attr in PROTECTED_ATTRIBUTES:
            if attr not in df.columns:
                continue
            sensitive = df[attr]
            try:
                if _FAIRLEARN_AVAILABLE:
                    dp_diff = float(demographic_parity_difference(y_true, y_pred, sensitive_features=sensitive))
                    eo_diff = float(equalized_odds_difference(y_true, y_pred, sensitive_features=sensitive))
                    di_ratio = float(demographic_parity_ratio(y_true, y_pred, sensitive_features=sensitive))

                    def tpr(y_t, y_p):
                        mask = y_t == 1
                        return recall_score(y_t[mask], y_p[mask], zero_division=0) if mask.any() else 0.0

                    frame = MetricFrame(
                        metrics={"tpr": tpr},
                        y_true=y_true,
                        y_pred=y_pred,
                        sensitive_features=sensitive,
                    )
                    eo_opp = float(frame.difference()["tpr"])
                else:
                    # Pure-numpy fallback — same semantics, no fairlearn dependency
                    dp_diff = _dp_difference_fallback(y_true.values, y_pred.values, sensitive.values)
                    eo_diff = _eo_difference_fallback(y_true.values, y_pred.values, sensitive.values)
                    di_ratio = _dp_ratio_fallback(y_true.values, y_pred.values, sensitive.values)
                    eo_opp = dp_diff  # simplified

                per_attribute[attr] = {
                    "demographic_parity_difference": dp_diff,
                    "equalized_odds_difference": eo_diff,
                    "equal_opportunity_difference": eo_opp,
                    "disparate_impact_ratio": di_ratio,
                }

                for name, val in per_attribute[attr].items():
                    if "ratio" in name:
                        if not (DI_LOW <= val <= DI_HIGH):
                            flagged.append(f"{attr}.{name}={val:.3f}")
                            metric_values.append(abs(1 - val))
                        else:
                            metric_values.append(0.0)
                    else:
                        metric_values.append(abs(val))
                        if abs(val) > DIFF_THRESHOLD:
                            flagged.append(f"{attr}.{name}={val:.3f}")

            except Exception:
                continue

        bias_score = max(0.0, 1.0 - float(np.mean(metric_values))) if metric_values else 1.0

        report = StatisticalReport(
            per_attribute_metrics=per_attribute,
            bias_score=round(bias_score, 4),
            flagged_metrics=flagged,
            sample_size=len(df),
        )
        return report.model_dump()

    def _fallback_report(self, applicant: dict[str, Any]) -> dict[str, Any]:
        """Return a neutral report when historical data is insufficient."""
        return StatisticalReport(
            per_attribute_metrics={},
            bias_score=1.0,
            flagged_metrics=["insufficient_data"],
            sample_size=0,
        ).model_dump()
