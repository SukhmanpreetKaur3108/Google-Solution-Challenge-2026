from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.engines.statistical import StatisticalFairnessEngine
from app.engines.intersectional import IntersectionalSurfaceEngine
from app.engines.causal import CausalFairnessEngine
from app.engines.adversarial import AdversarialRedTeamEngine
from app.engines.regulatory import RegulatoryComplianceEngine
from app.clients import bigquery as bq_client

logger = logging.getLogger(__name__)


class FairnessOrchestrator:
    def __init__(self) -> None:
        self.statistical = StatisticalFairnessEngine()
        self.intersectional = IntersectionalSurfaceEngine()
        self.causal = CausalFairnessEngine()
        self.adversarial = AdversarialRedTeamEngine()
        self.regulatory = RegulatoryComplianceEngine()

    async def evaluate(
        self,
        prediction: dict[str, Any],
        applicant: dict[str, Any],
    ) -> dict[str, Any]:
        """Run all five engines in parallel and assemble the fairness report."""
        try:
            historical_batch = await bq_client.fetch_historical_decisions()
        except Exception as exc:
            logger.warning("BigQuery fetch failed, using empty DataFrame: %s", exc)
            import pandas as pd
            historical_batch = pd.DataFrame()

        stat_task = self.statistical.evaluate(prediction, applicant, historical_batch)
        inter_task = self.intersectional.evaluate(historical_batch)
        causal_task = self.causal.counterfactual_score(applicant, prediction)
        adversarial_task = self.adversarial.evaluate(prediction, applicant)
        regulatory_task = self._regulatory_later(stat_task, inter_task, causal_task, adversarial_task)

        stat_report, inter_report, causal_report, adversarial_report = await asyncio.gather(
            stat_task, inter_task, causal_task, adversarial_task
        )

        regulatory_report = await self.regulatory.evaluate(
            stat_report, inter_report, causal_report, adversarial_report
        )

        return {
            "statistical": stat_report,
            "intersectional": inter_report,
            "causal": causal_report,
            "adversarial": adversarial_report,
            "regulatory": regulatory_report,
        }

    async def _regulatory_later(self, *tasks):
        """Placeholder — regulatory runs after other engines."""
        pass
