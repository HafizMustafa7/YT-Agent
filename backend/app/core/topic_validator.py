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

# Additional heuristics to detect low-quality/generic topics
STOPWORDS = set([
    'the', 'a', 'an', 'and', 'or', 'of', 'in', 'to', 'for', 'with', 'on', 'at', 'by', 'from',
    'about', 'as', 'is', 'it', 'this', 'that', 'these', 'those', 'be', 'are'
])

GENERIC_WORDS = set([
    'things', 'stuff', 'videos', 'content', 'ideas', 'random', 'anything'
])

COMMON_VERBS = set([
    'make', 'create', 'learn', 'build', 'find', 'discover', 'watch', 'see', 'get',
    'show', 'tell', 'explain', 'improve', 'grow', 'increase', 'reduce', 'save', 'fix', 'use',
    'do', 'how', 'why', 'what'
])

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
    
    # Prefer titles that are concise but descriptive (15-80 chars ideal)
    if len(topic) < 15:
        issues.append("Topic is too short. Aim for ~15-80 characters for better engagement.")
        score -= 25
    elif len(topic) > 120:
        issues.append("Topic is too long. Keep it concise (15-120 characters).")
        score -= 15

    # Tokenize and clean words
    raw_words = [w.strip(".,!?:;()[]\"'`).lower() for w in topic.split() if w.strip()]
    words = [w for w in raw_words if len(w) > 2]
    if len(words) < 2:
        issues.append("Topic needs at least 2 meaningful words")
        score -= 25

    # Penalize topics that are too generic (high stopword rate or generic words)
    if len(raw_words) > 0:
        stopword_ratio = sum(1 for w in raw_words if w in STOPWORDS) / len(raw_words)
        if stopword_ratio > 0.5:
            issues.append("Topic has too many filler words; make it more specific and action-oriented")
            score -= 20
        if any(w in GENERIC_WORDS for w in raw_words):
            issues.append("Avoid generic terms like 'things' or 'content' — be specific about the subject")
            score -= 15
    
    # Check for trending indicators (positive)
    has_trending_indicator = any(re.search(pattern, topic, re.IGNORECASE) for pattern in TRENDING_INDICATORS)
    if has_trending_indicator:
        score += 10  # Bonus for trending keywords
    
    # Check word diversity (avoid repetitive topics)
    unique_words = len(set([w.lower() for w in words]))
    if len(words) > 0 and unique_words / len(words) < 0.5:
        issues.append("Topic has too many repetitive words")
        score -= 15

    # Check for presence of an action verb or indicator of specific angle/hook
    def has_action_verb(words_list):
        for w in words_list:
            if w in COMMON_VERBS:
                return True
            # simple heuristic: words ending with 'ing' often indicate action
            if w.endswith('ing') and len(w) > 4:
                return True
        return False

    if not has_action_verb(raw_words):
        issues.append("Topic lacks an action or hook; include words like 'how', 'make', 'learn', or an active verb")
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
    
    # Minimum quality score to pass (stricter threshold)
    MIN_QUALITY_SCORE = 70

    if quality_check["quality_score"] < MIN_QUALITY_SCORE:
        issues_text = "; ".join(quality_check["issues"]) if quality_check["issues"] else "Please make the topic more specific and action-oriented."
        # Provide lightweight suggestions to help user improve the topic
        suggestions = []
        if any('short' in s.lower() for s in quality_check["issues"]):
            suggestions.append("Add a specific angle or time constraint (e.g., 'in 60 seconds', 'for beginners').")
        if any('generic' in s.lower() or 'things' in s.lower() for s in quality_check["issues"]):
            suggestions.append("Replace generic words with a specific subject (e.g., '10 quick morning stretches' instead of 'morning things').")
        if any('filler' in s.lower() or 'stopword' in s.lower() for s in quality_check["issues"]):
            suggestions.append("Use stronger nouns and verbs; reduce filler words.")
        if any('verb' in s.lower() for s in quality_check["issues"]):
            suggestions.append("Add an action or hook (e.g., 'How to', 'Watch this', 'Fix', 'Make').")

        # Generic rewrite examples
        base = normalized['normalized']
        example_rewrites = []
        if len(base) <= 60:
            example_rewrites.append(f"How to {base} in 60s")
            example_rewrites.append(f"Top 5 tips for {base}")
        else:
            example_rewrites.append(f"How to simplify {base}")

        return {
            "valid": False,
            "reason": f"Topic doesn't meet quality standards for trending content. {issues_text}",
            "quality_score": quality_check["quality_score"],
            "issues": quality_check["issues"],
            "normalized": normalized,
            "suggestions": suggestions,
            "example_rewrites": example_rewrites,
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
