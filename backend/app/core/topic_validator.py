"""
Strict topic validation with quality checks.
Ensures topics meet YouTube content policy and quality standards.
"""
import re
from typing import Dict, Any, Optional


def normalize_topic(topic: str) -> str:
    """
    Normalize a topic by cleaning whitespace and basic formatting.
    
    Args:
        topic: Raw topic string
        
    Returns:
        Normalized topic string
    """
    # Remove extra whitespace
    topic = ' '.join(topic.split())
    
    # Capitalize first letter
    if topic:
        topic = topic[0].upper() + topic[1:]
    
    return topic.strip()


def validate_topic(topic: str, niche_hint: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate a topic for YouTube Shorts content.
    Checks policy compliance and quality standards.
    
    Args:
        topic: The topic to validate
        niche_hint: Optional hint about the niche (e.g., from selected video)
        
    Returns:
        Dictionary with validation results:
        {
            "valid": bool,
            "score": int (0-100),
            "issues": List[str],
            "suggestions": List[str],
            "normalized": {
                "original": str,
                "normalized": str
            }
        }
    """
    if not topic or not topic.strip():
        return {
            "valid": False,
            "score": 0,
            "issues": ["Topic cannot be empty"],
            "suggestions": ["Enter a topic for your YouTube Short"],
            "normalized": {
                "original": topic,
                "normalized": ""
            }
        }
    
    topic = topic.strip()
    normalized = normalize_topic(topic)
    
    issues = []
    suggestions = []
    score = 100  # Start with perfect score, deduct for issues
    
    # ==================== Policy Violations (Auto-Reject) ====================
    
    # Check for prohibited content
    prohibited_keywords = [
        'hate', 'violence', 'terrorism', 'illegal', 'drugs', 'weapons',
        'scam', 'fraud', 'explicit', 'nsfw', 'adult', 'porn', 'xxx',
        'gambling', 'casino', 'bet', 'suicide', 'self-harm'
    ]
    
    topic_lower = topic.lower()
    for keyword in prohibited_keywords:
        if keyword in topic_lower:
            return {
                "valid": False,
                "score": 0,
                "issues": [f"Topic contains prohibited content: '{keyword}'"],
                "suggestions": ["Choose a topic that complies with YouTube's Community Guidelines"],
                "normalized": {
                    "original": topic,
                    "normalized": normalized
                }
            }
    
    # ==================== Quality Checks ====================
    
    # Length checks
    if len(topic) < 10:
        issues.append("Topic is too short. Add more detail (10-120 characters).")
        score -= 20
    elif len(topic) > 120:
        issues.append("Topic is too long. Keep it concise (15-120 characters).")
        score -= 15

    # Tokenize and clean words - FIXED STRING ESCAPING
    punctuation = '.,!?:;()[]"' + "'" + '`'
    raw_words = [w.strip(punctuation).lower() for w in topic.split() if w.strip()]
    words = [w for w in raw_words if len(w) > 2]
    if len(words) < 2:
        issues.append("Topic needs at least 2 meaningful words")
        score -= 25

    # Check for trending indicators (positive signals)
    trending_keywords = [
        'viral', 'trending', 'popular', 'top', 'best', 'amazing', 'incredible',
        'shocking', 'unbelievable', 'mind-blowing', 'epic', 'ultimate', 'secret',
        'hidden', 'unknown', 'rare', 'exclusive', 'breaking', 'new', 'latest'
    ]
    
    has_trending_indicator = any(kw in topic_lower for kw in trending_keywords)
    if has_trending_indicator:
        score += 10  # Bonus for trending keywords
    
    # Check for question format (engaging)
    if '?' in topic:
        score += 5  # Questions are engaging
    
    # Check for numbers (specific, engaging)
    if any(char.isdigit() for char in topic):
        score += 5  # Numbers make topics more specific
    
    # Word diversity check
    unique_words = set(words)
    if len(words) > 0 and len(unique_words) / len(words) < 0.5:
        issues.append("Topic has too much repetition")
        score -= 10
    
    # ==================== Suggestions ====================
    
    if score < 60:
        suggestions.append("Consider making your topic more specific and engaging")
    
    if len(topic) < 15:
        suggestions.append("Add more details to make your topic clearer")
    
    if not has_trending_indicator and score < 80:
        suggestions.append("Consider adding words like 'viral', 'trending', 'amazing' to increase appeal")
    
    if '?' not in topic and score < 80:
        suggestions.append("Try framing your topic as a question to increase engagement")
    
    if not any(char.isdigit() for char in topic):
        suggestions.append("Adding specific numbers (e.g., '5 ways', 'Top 10') can make topics more clickable")
    
    # ==================== Final Validation ====================
    
    # Topic is valid if score >= 60 and no critical issues
    is_valid = score >= 60 and len(issues) == 0
    
    # If score is low but no critical issues, still allow but warn
    if score < 60 and len(issues) == 0:
        issues.append("Topic quality is below recommended threshold")
    
    return {
        "valid": is_valid,
        "score": max(0, min(100, score)),  # Clamp between 0-100
        "issues": issues,
        "suggestions": suggestions,
        "normalized": {
            "original": topic,
            "normalized": normalized
        }
    }
