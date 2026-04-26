from __future__ import annotations

import asyncio
import os
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel

MIN_SAMPLES = int(os.environ.get("MIN_SUBGROUP_SAMPLES", 30))
PROTECTED = ["gender", "ethnicity", "age_bucket"]


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


class SubgroupRecord(BaseModel):
    label: str
    sample_size: int
    selection_rate: float
    true_positive_rate: float
    disparity_score: float
    attributes: dict[str, str]


class IntersectionalSurface(BaseModel):
    subgroups: list[SubgroupRecord]
    worst_subgroup: str
    worst_disparity_score: float
    surface_grid: list[dict[str, Any]]
    global_selection_rate: float
    global_tpr: float


class IntersectionalSurfaceEngine:
    async def evaluate(self, historical_batch: pd.DataFrame) -> dict[str, Any]:
        return await asyncio.get_event_loop().run_in_executor(
            None, self._compute, historical_batch
        )

    def _compute(self, df: pd.DataFrame) -> dict[str, Any]:
        if df.empty or len(df) < MIN_SAMPLES:
            return IntersectionalSurface(
                subgroups=[],
                worst_subgroup="N/A",
                worst_disparity_score=0.0,
                surface_grid=[],
                global_selection_rate=0.0,
                global_tpr=0.0,
            ).model_dump()

        df = df.copy()
        if "age" in df.columns and "age_bucket" not in df.columns:
            df["age_bucket"] = df["age"].apply(_age_bucket)

        available = [a for a in PROTECTED if a in df.columns]
        if "hired" not in df.columns or "score" not in df.columns:
            return IntersectionalSurface(
                subgroups=[],
                worst_subgroup="insufficient_columns",
                worst_disparity_score=0.0,
                surface_grid=[],
                global_selection_rate=0.0,
                global_tpr=0.0,
            ).model_dump()

        y_pred = (df["score"] >= 0.5).astype(int)
        y_true = df["hired"].astype(int)
        global_sr = float(y_pred.mean())
        global_tpr = float(y_pred[y_true == 1].mean()) if (y_true == 1).any() else 0.0

        subgroups: list[SubgroupRecord] = []
        # Powerset of protected attributes (1,2,3-way intersections)
        for r in range(1, len(available) + 1):
            for combo in combinations(available, r):
                groups = df.groupby(list(combo))
                for keys, group in groups:
                    if not isinstance(keys, tuple):
                        keys = (keys,)
                    if len(group) < MIN_SAMPLES:
                        continue
                    sr = float((group["score"] >= 0.5).mean())
                    positives = group[group["hired"] == 1]
                    tpr = float((positives["score"] >= 0.5).mean()) if len(positives) > 0 else 0.0
                    disparity = abs(sr - global_sr)
                    label_parts = [f"{k}={v}" for k, v in zip(combo, keys)]
                    subgroups.append(SubgroupRecord(
                        label=", ".join(label_parts),
                        sample_size=len(group),
                        selection_rate=round(sr, 4),
                        true_positive_rate=round(tpr, 4),
                        disparity_score=round(disparity, 4),
                        attributes=dict(zip(combo, keys)),
                    ))

        if not subgroups:
            return IntersectionalSurface(
                subgroups=[],
                worst_subgroup="no_eligible_subgroups",
                worst_disparity_score=0.0,
                surface_grid=[],
                global_selection_rate=round(global_sr, 4),
                global_tpr=round(global_tpr, 4),
            ).model_dump()

        worst = max(subgroups, key=lambda s: s.disparity_score)

        # Build 3D grid: x=gender index, y=ethnicity index, z=disparity
        gender_vals = sorted({s.attributes.get("gender", "") for s in subgroups if "gender" in s.attributes})
        eth_vals = sorted({s.attributes.get("ethnicity", "") for s in subgroups if "ethnicity" in s.attributes})
        g_map = {v: i for i, v in enumerate(gender_vals)}
        e_map = {v: i for i, v in enumerate(eth_vals)}

        surface_grid = []
        for s in subgroups:
            if "gender" in s.attributes and "ethnicity" in s.attributes:
                surface_grid.append({
                    "x": g_map.get(s.attributes["gender"], 0),
                    "y": e_map.get(s.attributes["ethnicity"], 0),
                    "z": s.disparity_score,
                    "value": s.selection_rate,
                    "label": s.label,
                })

        return IntersectionalSurface(
            subgroups=subgroups,
            worst_subgroup=worst.label,
            worst_disparity_score=worst.disparity_score,
            surface_grid=surface_grid,
            global_selection_rate=round(global_sr, 4),
            global_tpr=round(global_tpr, 4),
        ).model_dump()

    def worst_case_subgroup(self, surface: dict[str, Any]) -> str:
        return surface.get("worst_subgroup", "N/A")
