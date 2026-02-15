"""
Creative Brief Builder - Structures creative direction inputs.
"""
from typing import Dict, Any


# Allowed values from CreativeFormScreen.js
ALLOWED_TONES = ["dynamic", "calm", "motivational", "funny", "shocking", "heartwarming", "educational"]
ALLOWED_STYLES = ["cinematic realism", "3D animation", "hand-drawn sketch", "minimalist motion", "documentary-style"]
ALLOWED_MOVEMENTS = ["smooth tracking", "dynamic zoom", "static / tripod", "first-person view", "drone sweep"]
ALLOWED_FORMATS = ["narrative", "top 5 / list", "did you know", "emotional story", "how-to guide"]


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

    return {
        "tone": tone,
        "target_audience": preferences.get("target_audience", "General"),
        "visual_style": visual_style,
        "camera_movement": camera_movement,
        "effects": preferences.get("effects", "subtle transitions"),
        "story_format": story_format,
        "duration_seconds": int(preferences.get("duration_seconds", 60)),
        "constraints": preferences.get("constraints", []),
        "visual_mood": preferences.get("visual_mood", "engaging and vibrant"),
    }

