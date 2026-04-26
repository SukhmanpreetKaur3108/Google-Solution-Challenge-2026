from __future__ import annotations

import os
import json
from typing import Any

from google.cloud import aiplatform
from google.protobuf import json_format
from google.protobuf.struct_pb2 import Value


_endpoint: aiplatform.Endpoint | None = None


def _get_endpoint() -> aiplatform.Endpoint:
    global _endpoint
    if _endpoint is None:
        aiplatform.init(
            project=os.environ["GCP_PROJECT_ID"],
            location=os.environ.get("VERTEX_LOCATION", "us-central1"),
        )
        _endpoint = aiplatform.Endpoint(
            endpoint_name=os.environ["VERTEX_ENDPOINT_ID"]
        )
    return _endpoint


async def predict(features: dict[str, Any]) -> dict[str, Any]:
    """Call Vertex AI endpoint and return prediction + attributions."""
    endpoint = _get_endpoint()
    instance = json_format.ParseDict(features, Value())
    response = endpoint.predict(instances=[features])
    predictions = response.predictions
    if not predictions:
        raise ValueError("Vertex AI returned no predictions")
    pred = predictions[0]
    score = float(pred.get("score", pred) if isinstance(pred, dict) else pred)
    return {
        "score": score,
        "should_hire": score >= 0.5,
        "attributions": pred.get("attributions", {}) if isinstance(pred, dict) else {},
    }


async def predict_batch(feature_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Batch predict for adversarial probes."""
    endpoint = _get_endpoint()
    response = endpoint.predict(instances=feature_list)
    results = []
    for pred in response.predictions:
        score = float(pred.get("score", pred) if isinstance(pred, dict) else pred)
        results.append({"score": score, "should_hire": score >= 0.5})
    return results
