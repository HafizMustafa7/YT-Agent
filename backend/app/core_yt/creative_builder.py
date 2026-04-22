"""
Creative Brief Builder - Structures creative direction inputs.
"""
from typing import Dict, Any


# Allowed values aligned with CreativeFormScreen (Veo Specs)
ALLOWED_RESOLUTIONS = ["720p"]
ALLOWED_ASPECT_RATIOS = ["16:9", "9:16"]
ALLOWED_DURATIONS = [8, 15, 32, 46, 60]

ALLOWED_STYLES = [
    "cinematic", "film noir", "sci-fi", "horror film", "animated", 
    "3D cartoon", "surreal", "vintage", "futuristic", "hyperrealistic", "whimsical"
]

ALLOWED_CAMERA_MOTIONS = [
    "dolly shot", "tracking shot", "aerial view", "POV shot", "panning", 
    "slowly pulls back", "slowly flies"
]

ALLOWED_COMPOSITIONS = [
    "wide shot", "close-up", "medium shot", "eye-level", "low angle", 
    "top-down shot", "worm's eye"
]

ALLOWED_FOCUS_LENS = [
    "shallow depth of field", "deep focus", "macro lens", "wide-angle lens"
]

ALLOWED_AMBIANCE = [
    "cool blue tones", "warm tones", "natural light", "sunlight", "sunrise", 
    "sunset", "night", "torchlight flickering", "neon glow", "moonlit"
]


def build_creative_brief(preferences: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build structured and validated creative brief from user preferences (Veo format).
    """
    resolution = preferences.get("resolution", "720p")
    if resolution not in ALLOWED_RESOLUTIONS:
        resolution = "720p"

    aspect_ratio = preferences.get("aspect_ratio", "16:9")
    if aspect_ratio not in ALLOWED_ASPECT_RATIOS:
        aspect_ratio = "16:9"
        
    try:
        duration = int(preferences.get("duration", 15))
    except (ValueError, TypeError):
        duration = 15
        
    if duration not in ALLOWED_DURATIONS:
        duration = 15

    style = preferences.get("style", "cinematic")
    if style not in ALLOWED_STYLES:
        style = "cinematic"
        
    camera_motion = preferences.get("camera_motion", "dolly shot")
    if camera_motion not in ALLOWED_CAMERA_MOTIONS:
        camera_motion = "dolly shot"
        
    composition = preferences.get("composition", "wide shot")
    if composition not in ALLOWED_COMPOSITIONS:
        composition = "wide shot"

    focus_and_lens = preferences.get("focus_and_lens", "shallow depth of field")
    if focus_and_lens not in ALLOWED_FOCUS_LENS:
        focus_and_lens = "shallow depth of field"

    ambiance = preferences.get("ambiance", "cool blue tones")
    if ambiance not in ALLOWED_AMBIANCE:
        ambiance = "cool blue tones"

    return {
        "resolution": resolution,
        "aspect_ratio": aspect_ratio,
        "duration": duration,
        "style": style,
        "camera_motion": camera_motion,
        "composition": composition,
        "focus_and_lens": focus_and_lens,
        "ambiance": ambiance,
    }

