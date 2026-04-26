from __future__ import annotations

import os
import json
from typing import Any

# google-generativeai is deprecated; use google-genai (new SDK)
from google import genai
from google.genai import types as genai_types


_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        _client = genai.Client(api_key=api_key)
    return _client


def _model_name() -> str:
    return os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


async def generate_json(
    system_prompt: str,
    user_prompt: str,
    response_schema: dict[str, Any],
    temperature: float = 0.7,
) -> dict[str, Any]:
    """Call Gemini and return a parsed JSON response."""
    client = _get_client()
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    response = client.models.generate_content(
        model=_model_name(),
        contents=full_prompt,
        config=genai_types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
            system_instruction=system_prompt,
        ),
    )
    return json.loads(response.text)


async def generate_text(
    prompt: str,
    temperature: float = 0.4,
) -> str:
    """Call Gemini and return plain text."""
    client = _get_client()
    response = client.models.generate_content(
        model=_model_name(),
        contents=prompt,
        config=genai_types.GenerateContentConfig(temperature=temperature),
    )
    return response.text.strip()
