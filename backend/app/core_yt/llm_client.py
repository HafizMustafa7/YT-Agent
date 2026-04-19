"""
Shared Gemini client singleton.
"""
from typing import Optional
import google.generativeai as genai

from app.core.config import settings

_gemini_configured: bool = False

def configure_gemini():
    """Configure Gemini client singleton."""
    global _gemini_configured
    if not _gemini_configured and settings.GEMINI_API_KEY:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        _gemini_configured = True

def get_gemini_model(system_instruction: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 8192, json_mode: bool = False) -> Optional[genai.GenerativeModel]:
    """Get a configured Gemini GenerativeModel instance."""
    configure_gemini()
    if not _gemini_configured:
        return None
        
    generation_config = genai.GenerationConfig(
        temperature=temperature,
        max_output_tokens=max_tokens,
    )
    if json_mode:
        generation_config.response_mime_type = "application/json"
        
    return genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=system_instruction,
        generation_config=generation_config
    )
