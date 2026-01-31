"""
LLM-based topic validation using MegaLLM.
Validates topics for YouTube Shorts content with AI-powered analysis.
"""
import json
import re
from typing import Dict, Any, Optional
from openai import OpenAI

from app.config.settings import settings

# Configure MegaLLM client
client = None
if settings.MEGALLM_API_KEY:
    client = OpenAI(
        api_key=settings.MEGALLM_API_KEY,
        base_url=settings.MEGALLM_BASE_URL
    )


def normalize_topic(topic: str) -> str:
    """
    Normalize a topic by cleaning whitespace and basic formatting.
    """
    topic = ' '.join(topic.split())
    if topic:
        topic = topic[0].upper() + topic[1:]
    return topic.strip()


async def validate_topic(topic: str, niche_hint: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate a topic for YouTube Shorts content using LLM.
    
    Args:
        topic: The topic to validate
        niche_hint: Optional hint about the niche (e.g., from selected video)
        
    Returns:
        Dictionary with validation results including:
        - valid: bool
        - score: int (0-100)
        - reason: str (explanation of why valid/invalid)
        - issues: List[str]
        - suggestions: List[str]
        - normalized: dict with original and normalized topic
    """
    if not topic or not topic.strip():
        return {
            "valid": False,
            "score": 0,
            "reason": "Topic cannot be empty. Please enter a topic for your YouTube Short.",
            "issues": ["Topic cannot be empty"],
            "suggestions": ["Enter a descriptive topic for your YouTube Short video"],
            "normalized": {
                "original": topic,
                "normalized": ""
            }
        }
    
    topic = topic.strip()
    normalized = normalize_topic(topic)
    
    # If no API key, return basic validation
    if not client:
        return {
            "valid": True,
            "score": 70,
            "reason": "Topic accepted (LLM validation unavailable)",
            "issues": [],
            "suggestions": ["Consider making your topic more specific and engaging"],
            "normalized": {
                "original": topic,
                "normalized": normalized
            }
        }
    
    # Call LLM for validation
    validation_prompt = f"""You are a YouTube content expert. Analyze this topic for a YouTube Shorts video and determine if it's valid.

TOPIC: "{topic}"
{f'NICHE CONTEXT: {niche_hint}' if niche_hint else ''}

Evaluate the topic based on these criteria:
1. **YouTube Policy Compliance**: No hate, violence, illegal content, explicit/adult content, scams, or harmful content
2. **Content Quality**: Is the topic clear, specific, and makes sense for a short video?
3. **Engagement Potential**: Would this topic attract viewers? Is it interesting/viral-worthy?
4. **Clarity**: Is the topic understandable and well-defined?
5. **Feasibility**: Can this be made into a 30-60 second video?

You MUST respond with ONLY a valid JSON object (no markdown, no code blocks, no extra text):

{{
    "valid": true or false,
    "score": 0-100 (quality score),
    "reason": "Clear explanation of why the topic is valid or invalid",
    "issues": ["list of specific problems found, empty array if valid"],
    "suggestions": ["list of actionable suggestions to improve the topic"]
}}

IMPORTANT: 
- Be constructive, not harsh
- If the topic is acceptable but could be better, mark it as valid with suggestions
- Only mark as invalid for serious issues (policy violations, completely unclear, or impossible to make into a video)
- Provide helpful suggestions even for valid topics
- Score 70+ means valid, below 60 means invalid

Respond with JSON only:"""

    try:
        print(f"[DEBUG] Validating topic with LLM: {topic[:50]}...")
        
        response = client.chat.completions.create(
            model=settings.MEGALLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that responds only in valid JSON format. Do not include any text before or after the JSON."
                },
                {"role": "user", "content": validation_prompt}
            ],
            temperature=0.3,  # Lower temperature for more consistent validation
            max_tokens=1024
        )
        
        response_text = response.choices[0].message.content.strip()
        print(f"[DEBUG] LLM validation response: {response_text[:200]}...")
        
        # Parse JSON response
        try:
            # Try direct parse
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise ValueError("Could not parse LLM response as JSON")
        
        # Ensure all required fields are present
        return {
            "valid": result.get("valid", True),
            "score": result.get("score", 70),
            "reason": result.get("reason", "Topic validation completed"),
            "issues": result.get("issues", []),
            "suggestions": result.get("suggestions", []),
            "normalized": {
                "original": topic,
                "normalized": normalized
            }
        }
        
    except Exception as e:
        print(f"[ERROR] LLM validation failed: {e}")
        # Fallback to basic validation if LLM fails
        return {
            "valid": True,
            "score": 70,
            "reason": f"Topic accepted (LLM validation error: {str(e)[:50]})",
            "issues": [],
            "suggestions": ["Consider making your topic more specific"],
            "normalized": {
                "original": topic,
                "normalized": normalized
            }
        }
