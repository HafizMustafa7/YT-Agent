"""
Topic Suggestion Engine

Calls Gemini with a trend summary and returns the Top-N ranked topic
suggestions for YouTube Shorts content.

Uses the same shared Gemini client singleton and JSON-guard pattern
as topic_validator.py.
"""
import json
import logging
import re
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.core_yt.llm_client import get_gemini_model

logger = logging.getLogger(__name__)


def _build_suggestion_prompt(trend_summary: str, niche: str, top_n: int) -> str:
    """Construct the LLM prompt for topic suggestion."""
    return f"""You are a VIRAL YouTube Shorts creator who has built multiple 1M+ subscriber channels.
You think like a human content creator, NOT like an AI assistant or corporate marketer.

Your job: study the trending video data below and generate the TOP {top_n} YouTube Shorts topic ideas
that a REAL creator in the '{niche}' niche would actually make and title themselves.

--- TREND DATA ---
{trend_summary}
--- END TREND DATA ---

STRICT RULES — READ THESE CAREFULLY:

1. GROUND YOUR TOPICS IN THE TREND DATA.
   Study the titles, tags, and engagement signals. Your topics must be inspired by what is ALREADY
   performing well. Don't invent unrelated concepts out of thin air.

2. WRITE LIKE A HUMAN CREATOR, NOT AN AI.
   NEVER use robotic, corporate, or AI-sounding phrasing. Here are examples of what to AVOID:
   ❌ "AI-Generated 3D Room Construction"
   ❌ "A Comprehensive Analysis of Modern Architecture"
   ❌ "Exploring the Possibilities of Digital Fabrication"
   
   Instead, write how a real YouTuber would — punchy, casual, emotionally charged:
   ✅ "I built my dream room using nothing but AI (insane)"
   ✅ "This sneaky trick makes ANY room look bigger instantly"
   ✅ "Why your favorite creator is secretly doing THIS"

3. USE PROVEN VIRAL TITLE FORMATS. Choose the best fitting one per topic:
   - Curiosity Gap: "The hidden reason why [X] actually [Y]"
   - Personal Challenge: "I tried [X] for 30 days — here's what happened"
   - Myth Bust: "Stop [X] immediately (everyone gets this wrong)"
   - Shocking Fact: "No one talks about this [X] trick"
   - Speed/Stakes: "I only had 24 hours to [X]"
   - Listicle Hook: "[N] [X] that will [strong outcome]"
   - Controversy: "Unpopular opinion: [X]"

4. BE SPECIFIC. Vague topics get skipped. 
   ❌ "Interesting AI tools" → ✅ "5 AI tools that literally do your homework for you"

5. NO fluff like "In this video I explore..." — just the title concept.

Return ONLY a valid JSON object. No markdown, no code fences, no extra text:

{{
    "topics": [
        {{
            "rank": 1,
            "topic": "Catchy human-written title here",
            "rationale": "One casual sentence: why this will blow up based on the trend data",
            "score": 92
        }},
        ...
    ]
}}

Return exactly {top_n} topics. Score 80-100 = viral, 60-79 = solid, below 60 = average.
Respond with JSON only:"""


async def generate_topic_suggestions(
    trend_summary: str,
    niche: str,
    top_n: int = 5,
) -> List[Dict[str, Any]]:
    """
    Generate Top-N ranked topic suggestions via LLM based on trend data.

    Args:
        trend_summary: Text block from build_trend_summary().
        niche:         The content niche (used for context in prompt).
        top_n:         How many topics to return. Default 5.

    Returns:
        List of dicts: [{ rank, topic, rationale, score }, ...]
        Returns empty list if LLM is unavailable or parsing fails.
    """
    model = get_gemini_model(
        system_instruction=(
            "You are a helpful assistant that responds only in valid JSON format. "
            "Do not include any text before or after the JSON."
        ),
        temperature=0.85, # Higher = more creative, less robotic topic output
        max_tokens=2048,
        json_mode=True
    )

    if not model:
        logger.warning("Gemini client not available — returning empty suggestions")
        return []

    prompt = _build_suggestion_prompt(trend_summary, niche, top_n)

    try:
        logger.info("Calling Gemini for topic suggestions (niche=%s, top_n=%d)", niche, top_n)

        response = model.generate_content(prompt)

        response_text = response.text.strip()
        logger.debug("LLM suggestion response (first 300 chars): %s", response_text[:300])

        # Parse JSON — with fallback extraction guard (same pattern as topic_validator.py)
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError:
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                result = json.loads(json_match.group())
            else:
                logger.error("Could not parse LLM response as JSON: %s", response_text[:200])
                return []

        topics: List[Dict] = result.get("topics", [])

        # Validate and normalise each topic entry
        validated: List[Dict[str, Any]] = []
        for raw in topics:
            if not isinstance(raw, dict):
                continue
            validated.append({
                "rank": int(raw.get("rank", len(validated) + 1)),
                "topic": str(raw.get("topic", "")).strip(),
                "rationale": str(raw.get("rationale", "")).strip(),
                "score": max(0, min(100, int(raw.get("score", 70)))),
            })

        # Ensure rank order is correct
        validated.sort(key=lambda t: t["rank"])
        logger.info("Generated %d topic suggestions for niche '%s'", len(validated), niche)
        return validated[:top_n]

    except Exception as e:
        logger.error("Topic suggestion engine error: %s", e)
        return []
