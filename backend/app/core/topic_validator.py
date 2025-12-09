"""
Topic Validation Module - Strict validation for trending-worthy topics.
Focuses on YouTube policy compliance and quality checks for viral content.
"""
import re
from typing import Dict, Any, List


# YouTube policy violations
POLICY_VIOLATIONS = [
    r'\b(hack|cheat|scam|illegal|piracy|stolen|copyright)\b',
    r'\b(violence|gore|explicit|nsfw|adult)\b',
    r'\b(drug|weapon|knife|gun|bomb)\b',
    r'\b(hate|racist|discrimination)\b',
]

# Weak/low-quality topic patterns
WEAK_PATTERNS = [
    r'^(hi|hello|test|asdf|qwerty)',
    r'^(the|a|an)\s+\w{1,3}$',  # Too short with articles
    r'^\d+$',  # Only numbers
    r'^[^\w\s]+$',  # Only special chars
]

# Trending-worthy indicators
TRENDING_INDICATORS = [
    r'\b(trending|viral|hottest|newest|latest|best|top)\b',
    r'\b(amazing|incredible|shocking|unbelievable)\b',
    r'\b(tips|tricks|hacks|secrets|facts)\b',
    r'\b(before|after|transformation|journey)\b',
    r'\b(how|why|what|when|where)\b',
]


def normalize_topic(topic: str, niche_hint: str = None) -> Dict[str, Any]:
    """Normalize and clean a topic string."""
    if not topic or not topic.strip():
        raise ValueError("Topic cannot be empty.")
    
    cleaned = re.sub(r'\s+', ' ', topic.strip())
    
    return {
        "original": topic,
        "normalized": cleaned,
        "niche_hint": niche_hint,
    }


def check_policy_compliance(topic: str) -> Dict[str, Any]:
    """Check if topic violates YouTube policies."""
    topic_lower = topic.lower()
    violations = []
    
    for pattern in POLICY_VIOLATIONS:
        if re.search(pattern, topic_lower, re.IGNORECASE):
            violations.append(f"Violates policy: {pattern}")
    
    return {
        "compliant": len(violations) == 0,
        "violations": violations,
    }


def check_topic_quality(topic: str) -> Dict[str, Any]:
    """Check if topic has enough substance for trending content."""
    issues = []
    score = 100
    
    # Check for weak patterns
    for pattern in WEAK_PATTERNS:
        if re.match(pattern, topic, re.IGNORECASE):
            issues.append("Topic is too generic or low quality")
            score -= 30
    
    # Length requirements (stricter)
    if len(topic) < 10:
        issues.append("Topic is too short. Aim for 10-100 characters for better engagement.")
        score -= 25
    elif len(topic) > 100:
        issues.append("Topic is too long. Keep it concise (10-100 characters).")
        score -= 15
    
    # Must have meaningful words (not just filler)
    words = [w for w in topic.split() if len(w) > 2]
    if len(words) < 2:
        issues.append("Topic needs at least 2 meaningful words")
        score -= 20
    
    # Check for trending indicators (positive)
    has_trending_indicator = any(re.search(pattern, topic, re.IGNORECASE) for pattern in TRENDING_INDICATORS)
    if has_trending_indicator:
        score += 10  # Bonus for trending keywords
    
    # Check word diversity (avoid repetitive topics)
    unique_words = len(set([w.lower() for w in words]))
    if len(words) > 0 and unique_words / len(words) < 0.5:
        issues.append("Topic has too many repetitive words")
        score -= 15
    
    # Must contain alphabetic characters
    if not re.search(r'[a-zA-Z]', topic):
        issues.append("Topic must contain at least one letter")
        score -= 50
    
    return {
        "quality_score": max(0, score),
        "issues": issues,
        "has_trending_indicator": has_trending_indicator,
    }


def validate_topic(topic: str, niche_hint: str = None) -> Dict[str, Any]:
    """
    Strict validation for trending-worthy topics:
    - Policy compliance
    - Quality checks (length, substance, uniqueness)
    - Trending potential
    """
    # Normalize
    normalized = normalize_topic(topic, niche_hint)
    clean_topic = normalized["normalized"]
    
    # Policy compliance (must pass)
    policy_check = check_policy_compliance(clean_topic)
    if not policy_check["compliant"]:
        return {
            "valid": False,
            "reason": "Topic violates YouTube policies. Please choose a different topic.",
            "violations": policy_check["violations"],
            "normalized": normalized,
        }
    
    # Quality checks (stricter)
    quality_check = check_topic_quality(clean_topic)
    
    # Minimum quality score to pass (strict threshold)
    MIN_QUALITY_SCORE = 60
    
    if quality_check["quality_score"] < MIN_QUALITY_SCORE:
        issues_text = "; ".join(quality_check["issues"])
        return {
            "valid": False,
            "reason": f"Topic doesn't meet quality standards for trending content. {issues_text}",
            "quality_score": quality_check["quality_score"],
            "issues": quality_check["issues"],
            "normalized": normalized,
        }
    
    # If we get here, topic is valid and trending-worthy
    return {
        "valid": True,
        "normalized": normalized,
        "policy_check": policy_check,
        "quality_check": {
            "quality_score": quality_check["quality_score"],
            "has_trending_indicator": quality_check["has_trending_indicator"],
        },
        "message": "Topic is valid and has good potential for trending content!",
    }
