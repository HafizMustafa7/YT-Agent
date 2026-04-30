"""
Shared AI client singletons.
Uses google-genai>=1.16.0 SDK.

Two client paths:
  1. Developer API (api_key) — used by topic suggestion + topic validation (cheap/fast tasks)
  2. Vertex AI (service account) — used by story generation (Gemini 2.5 Pro) + video generation (Veo)
"""
import os
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types

from app.core.config import settings

# ---------------------------------------------------------------------------
# Developer API client (topic suggestion, topic validation)
# ---------------------------------------------------------------------------

_gemini_client: Optional[genai.Client] = None


def _get_gemini_client() -> genai.Client:
    """Get or create Gemini Developer API client (Flash Lite — cheap tasks)."""
    global _gemini_client
    if _gemini_client is None:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set in .env")
        _gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _gemini_client


class _GenerativeModelShim:
    """
    Thin shim that mimics the old GenerativeModel interface
    (model.generate_content(msg, safety_settings=...))
    so that topic_suggestion_engine.py and topic_validator.py require zero changes.
    """

    def __init__(
        self,
        model_name: str,
        system_instruction: Optional[str],
        temperature: float,
        max_tokens: int,
        json_mode: bool,
    ):
        self._model_name = model_name
        self._system_instruction = system_instruction
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._json_mode = json_mode

    def generate_content(self, user_message: str, safety_settings=None):
        """
        Call Gemini Developer API and return a response object whose
        `.text` attribute contains the model reply (same as old SDK).
        """
        client = _get_gemini_client()

        config_kwargs = {
            "temperature": self._temperature,
            "max_output_tokens": self._max_tokens,
        }
        if self._json_mode:
            config_kwargs["response_mime_type"] = "application/json"
        if self._system_instruction:
            config_kwargs["system_instruction"] = self._system_instruction

        if safety_settings:
            config_kwargs["safety_settings"] = [
                types.SafetySetting(
                    category=s["category"],
                    threshold=s["threshold"],
                )
                for s in safety_settings
            ]

        gen_config = types.GenerateContentConfig(**config_kwargs)

        response = client.models.generate_content(
            model=self._model_name,
            contents=user_message,
            config=gen_config,
        )
        return response


def get_gemini_model(
    system_instruction: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 8192,
    json_mode: bool = False,
) -> Optional[_GenerativeModelShim]:
    """
    Get a configured Gemini Developer API model shim.
    Used by: topic_suggestion_engine.py, topic_validator.py
    NOT used by story_service.py (which uses get_vertex_ai_client() directly).
    Returns None if GEMINI_API_KEY is not set.
    """
    if not settings.GEMINI_API_KEY:
        return None
    return _GenerativeModelShim(
        model_name=settings.GEMINI_MODEL,
        system_instruction=system_instruction,
        temperature=temperature,
        max_tokens=max_tokens,
        json_mode=json_mode,
    )


# ---------------------------------------------------------------------------
# Vertex AI client (story generation + video generation — shared singleton)
# ---------------------------------------------------------------------------

_vertex_client: Optional[genai.Client] = None


def get_vertex_ai_client() -> genai.Client:
    """
    Get or create Vertex AI genai.Client authenticated via service account JSON.

    Used by:
      - story_service.py  → Gemini 2.5 Pro story generation (thinking model)
      - video_service.py  → Veo video generation

    Both share the same singleton so the service account is only initialised once,
    and both bill to the same Google Cloud project (your $300 credits).
    """
    global _vertex_client
    if _vertex_client is None:
        cred_value = settings.GOOGLE_APPLICATION_CREDENTIALS
        if not cred_value:
            raise ValueError(
                "GOOGLE_APPLICATION_CREDENTIALS is not set in .env. "
                "Set it to the service account JSON filename inside the backend/ folder."
            )
        if not settings.VERTEX_AI_PROJECT_ID:
            raise ValueError("VERTEX_AI_PROJECT_ID is not set in .env")

        # Resolve relative path to absolute (relative = relative to backend/)
        if not os.path.isabs(cred_value):
            backend_dir = Path(__file__).resolve().parents[2]
            cred_value = str(backend_dir / cred_value)

        if not os.path.exists(cred_value):
            raise FileNotFoundError(
                f"Service account JSON not found at: {cred_value}\n"
                f"Place the JSON file in the backend/ folder and set "
                f"GOOGLE_APPLICATION_CREDENTIALS=<filename> in .env"
            )

        # Set env var so google-auth picks it up automatically
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cred_value

        _vertex_client = genai.Client(
            vertexai=True,
            project=settings.VERTEX_AI_PROJECT_ID,
            location=settings.VERTEX_AI_LOCATION,
        )
    return _vertex_client
