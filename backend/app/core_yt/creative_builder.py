"""
Creative Brief Builder - Structures creative direction inputs.
"""
from typing import Dict, Any


# Allowed values aligned with CreativeFormScreen
ALLOWED_TONES = [
    "dynamic",
    "motivational",
    "inspirational",
    "educational",
    "shocking",
    "heartwarming",
    "powerful",
    "peaceful",
]
ALLOWED_STYLES = [
    "cinematic realism",
    "documentary realism",
    "naturalistic drama",
    "urban realism",
    "outdoor realism",
]
ALLOWED_MOVEMENTS = [
    "smooth tracking",
    "static tripod",
    "handheld documentary",
    "push-in zoom",
    "drone sweep",
]
ALLOWED_FORMATS = ["narrative", "educational", "did you know", "emotional story", "how-to guide"]
ALLOWED_COLOR_GRADING = [
    "natural cinematic color grading",
    "warm filmic",
    "cool desaturated",
    "high contrast documentary",
]


def normalize_duration_seconds(raw: Any, default: int = 60) -> int:
    """Normalize duration to 10..180 seconds in 10-second increments."""
    try:
        duration = int(raw)
    except (TypeError, ValueError):
        duration = default
    duration = max(10, min(180, duration))
    # Round to nearest 10 to enforce the configured step size.
    return int(round(duration / 10.0) * 10)


def build_creative_brief(preferences: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build structured and validated creative brief from user preferences.
    """
    tone = preferences.get("tone", "dynamic")
    if tone not in ALLOWED_TONES:
        tone = "dynamic"
        
    visual_style = preferences.get("visual_style", "cinematic realism")
    if visual_style not in ALLOWED_STYLES:
        visual_style = "cinematic realism"
        
    camera_movement = preferences.get("camera_movement", "smooth tracking")
    if camera_movement not in ALLOWED_MOVEMENTS:
        camera_movement = "smooth tracking"
        
    story_format = preferences.get("story_format", "narrative")
    if story_format not in ALLOWED_FORMATS:
        story_format = "narrative"

    effects = preferences.get("effects", "natural cinematic color grading")
    if effects not in ALLOWED_COLOR_GRADING:
        effects = "natural cinematic color grading"

    return {
        "tone": tone,
        "target_audience": preferences.get("target_audience", "General"),
        "visual_style": visual_style,
        "camera_movement": camera_movement,
        "effects": effects,
        "story_format": story_format,
        "duration_seconds": normalize_duration_seconds(preferences.get("duration_seconds", 60)),
        "constraints": preferences.get("constraints", []),
        "visual_mood": preferences.get("visual_mood", "engaging and vibrant"),
    }

