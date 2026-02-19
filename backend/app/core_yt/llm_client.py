"""
Shared MegaLLM (OpenAI-compatible) client singleton.
Avoids creating duplicate OpenAI client instances across modules.
"""
from typing import Optional
from openai import OpenAI

from app.core.config import settings

_megallm_client: Optional[OpenAI] = None


def get_megallm_client() -> Optional[OpenAI]:
    """Get or create shared MegaLLM client singleton.
    Returns None if MEGALLM_API_KEY is not configured.
    """
    global _megallm_client
    if _megallm_client is None and settings.MEGALLM_API_KEY:
        _megallm_client = OpenAI(
            api_key=settings.MEGALLM_API_KEY,
            base_url=settings.MEGALLM_BASE_URL,
        )
    return _megallm_client
