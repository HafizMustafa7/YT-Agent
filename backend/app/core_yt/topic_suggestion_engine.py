"""
Topic Suggestion Engine

Calls MegaLLM with a trend summary and returns the Top-N ranked topic
suggestions for YouTube Shorts content.

Uses the same shared MegaLLM client singleton and JSON-guard pattern
as topic_validator.py.
"""
import json
import logging
import re
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.core_yt.llm_client import get_megallm_client

logger = logging.getLogger(__name__)


def _build_suggestion_prompt(trend_summary: str, niche: str, top_n: int) -> str:
    """Construct the LLM prompt for topic suggestion."""
    return f"""You are an expert YouTube Shorts content strategist with deep knowledge of viral trends.

Based on the following trending video data, generate the TOP {top_n} MOST VIRAL topic suggestions 
for a new YouTube Shorts video in the '{niche}' niche.

--- TREND DATA ---
{trend_summary}
--- END TREND DATA ---

INSTRUCTIONS:
- Analyse the titles, tags, and engagement signals from the trending data above.
- Generate {top_n} unique, specific, and highly engaging topic ideas for YouTube Shorts.
- Each topic should be a clear, concise video title/concept (not just a keyword).
- Rank them from most viral potential (#1) to least.
- For each topic, provide a one-sentence rationale explaining WHY it will perform well.
- Assign a virality score 0-100 based on trend alignment and engagement patterns.

You MUST respond with ONLY a valid JSON object (no markdown, no code blocks, no extra text):

{{
    "topics": [
        {{
            "rank": 1,
            "topic": "Specific viral topic title here",
            "rationale": "One sentence explaining why this will go viral based on the trend data",
            "score": 92
        }},
        ...
    ]
}}

IMPORTANT:
- Return exactly {top_n} topics in the array
- Topics must be specific and actionable (e.g. "5 AI Tools That Will Replace Your Job in 2025" NOT just "AI tools")
- Score 80-100 = highly viral, 60-79 = good potential, below 60 = moderate
- Base suggestions strictly on the trend data provided

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
    client = get_megallm_client()

    if not client:
        logger.warning("MegaLLM client not available — returning empty suggestions")
        return []

    prompt = _build_suggestion_prompt(trend_summary, niche, top_n)

    try:
        logger.info("Calling MegaLLM for topic suggestions (niche=%s, top_n=%d)", niche, top_n)

        response = client.chat.completions.create(
            model=settings.MEGALLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant that responds only in valid JSON format. "
                        "Do not include any text before or after the JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,   # Slightly higher for creative diversity
            max_tokens=2048,
        )

        response_text = response.choices[0].message.content.strip()
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
