from __future__ import annotations

import os
import pandas as pd
from google.cloud import bigquery


_client: bigquery.Client | None = None


def _get_client() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(project=os.environ["GCP_PROJECT_ID"])
    return _client


async def fetch_historical_decisions(limit: int | None = None) -> pd.DataFrame:
    """Return the last N decisions from BigQuery as a DataFrame."""
    if limit is None:
        limit = int(os.environ.get("BQ_HISTORICAL_BATCH_SIZE", 1000))
    project = os.environ["GCP_PROJECT_ID"]
    dataset = os.environ.get("BQ_DATASET", "pof_ai")
    table = os.environ.get("BQ_TABLE_DECISIONS", "decisions")

    query = f"""
        SELECT
            gender,
            ethnicity,
            age,
            education,
            years_experience,
            score,
            hired,
            timestamp
        FROM `{project}.{dataset}.{table}`
        ORDER BY timestamp DESC
        LIMIT @limit
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("limit", "INT64", limit)]
    )
    client = _get_client()
    job = client.query(query, job_config=job_config)
    df = job.result().to_dataframe()
    return df
