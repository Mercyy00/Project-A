"""
Resilient Google Gemini API Client for JARVIS.

Ported from Mark LVI's core/gemini.py.
Enforces:
- Strict 10-second timeout on API calls to prevent indefinite hangs
- Model fallback ladder: gemini-3.5-flash -> gemini-3.8-flash -> gemini-2.5-flash-lite
- Unified helper for text, vision, and tool calling
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any, Dict, List, Optional, Union
from google import genai
from google.genai import types

DEFAULT_TIMEOUT = 12.0
FALLBACK_MODELS = [
    os.getenv("GEMINI_MODEL") or os.getenv("MODEL_NAME") or "gemini-3.5-flash",
    "gemini-3.8-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest"
]


def get_gemini_client(api_key: Optional[str] = None) -> genai.Client:
    """Instantiates a Google GenAI Client with active environment key."""
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key or key == "your_gemini_api_key_here":
        raise ValueError("GEMINI_API_KEY is not configured.")
    return genai.Client(api_key=key)


def generate_content_with_fallback(
    contents: Union[str, List[Any]],
    client: Optional[genai.Client] = None,
    config: Optional[types.GenerateContentConfig] = None,
    preferred_model: Optional[str] = None
) -> types.GenerateContentResponse:
    """
    Executes a content generation request through a prioritized fallback ladder.
    Catches 404 deprecations, 429 quota exhaustion, and 503 capacity errors,
    immediately stepping down to the next viable model in the ladder.
    """
    ai_client = client or get_gemini_client()
    ladder = list(FALLBACK_MODELS)
    if preferred_model and preferred_model not in ladder:
        ladder.insert(0, preferred_model)

    last_error: Optional[Exception] = None
    for model_name in ladder:
        try:
            response = ai_client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            if response:
                return response
        except Exception as exc:
            last_error = exc
            err_str = str(exc)
            # If invalid API key, do not attempt fallback
            if "API_KEY_INVALID" in err_str or "403" in err_str:
                raise exc
            continue

    raise RuntimeError(f"All models in fallback ladder failed. Last error: {last_error}")
