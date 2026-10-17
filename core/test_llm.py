"""LLM connectivity test script for Project Jarvis Core.

Validates API connectivity to Google Gemini using the google-genai SDK,
measures end-to-end request latency, and verifies model response.
Adheres strictly to the Project Jarvis architecture and modular boundary rules.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import errors


def get_gemini_api_key(env_path: Optional[Path] = None) -> str:
    """Retrieve the GEMINI_API_KEY from environment variables or .env file.

    Loads environment variables from .env using python-dotenv. If no explicit
    path is provided, checks the project root directory.

    Args:
        env_path: Optional explicit filesystem path to the .env file.

    Returns:
        The validated Gemini API key string.

    Raises:
        ValueError: If GEMINI_API_KEY is not set or retains template placeholder text.
    """
    if env_path is not None:
        load_dotenv(dotenv_path=env_path)
    else:
        # Resolve project root relative to core/ directory
        project_root: Path = Path(__file__).resolve().parent.parent
        default_env: Path = project_root / ".env"
        if default_env.exists():
            load_dotenv(dotenv_path=default_env)
        else:
            load_dotenv()

    api_key: Optional[str] = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.strip() == "" or api_key.strip() == "your_gemini_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY is missing or invalid. "
            "Please copy .env.example to .env and configure your GEMINI_API_KEY."
        )
    return api_key.strip()


def run_llm_test(
    model_name: str = "gemini-2.5-flash",
    prompt: str = "Hello, confirm your identity as Jarvis Core.",
) -> Optional[str]:
    """Initialize the Gemini client and verify connectivity with model.

    Sends the specified prompt to Gemini, prints the returned model
    response, and reports elapsed round-trip latency in seconds.

    Args:
        model_name: Gemini model name identifier (default: 'gemini-2.5-flash').
        prompt: Initial prompt verifying Jarvis Core identity.

    Returns:
        The response text string if successful, or None if the request failed.
    """
    print(f"[*] Initializing Gemini client with model: {model_name}")

    try:
        api_key: str = get_gemini_api_key()
    except ValueError as err:
        print(f"[!] Configuration Error: {err}", file=sys.stderr)
        return None

    try:
        client: genai.Client = genai.Client(api_key=api_key)

        print(f"[*] Sending prompt: '{prompt}'")
        start_time: float = time.perf_counter()

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )

        elapsed_latency: float = time.perf_counter() - start_time
        response_text: str = response.text.strip() if response.text else ""

        print("\n--- Jarvis Response ---")
        print(response_text)
        print("-----------------------")
        print(f"Jarvis core initialized successfully. Latency: {elapsed_latency:.2f}s")
        return response_text

    except errors.APIError as err:
        print(f"[!] Gemini API Error: {err.message} (Code: {err.code})", file=sys.stderr)
        return None
    except Exception as err:
        print(f"[!] Unexpected error during LLM connection test: {err}", file=sys.stderr)
        return None


def main() -> None:
    """CLI entry point for running the LLM test runner."""
    result: Optional[str] = run_llm_test()
    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    main()
