"""
Creative Brief Builder - Structures creative direction inputs.
"""
from typing import Dict, Any


def build_creative_brief(preferences: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build structured creative brief from user preferences.
    
    Expected preferences:
    - tone: str
    - target_audience: str
    - visual_style: str
    - camera_movement: str
    - effects: str
    - story_format: str
    - duration_seconds: int
    - constraints: List[str]
    """
    return {
        "tone": preferences.get("tone", "dynamic"),
        "target_audience": preferences.get("target_audience", "General"),
        "visual_style": preferences.get("visual_style", "cinematic realism"),
        "camera_movement": preferences.get("camera_movement", "smooth tracking"),
        "effects": preferences.get("effects", "subtle transitions"),
        "story_format": preferences.get("story_format", "narrative"),
        "duration_seconds": int(preferences.get("duration_seconds", 60)),
        "constraints": preferences.get("constraints", []),
        "visual_mood": preferences.get("visual_mood", "engaging and vibrant"),
    }

