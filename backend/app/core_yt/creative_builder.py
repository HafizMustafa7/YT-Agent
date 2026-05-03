"""
Creative Brief Builder - Structures creative direction inputs.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


# Allowed values aligned with CreativeFormScreen (Veo Specs)
ALLOWED_RESOLUTIONS = ["720p"]
ALLOWED_ASPECT_RATIOS = ["16:9", "9:16"]
ALLOWED_DURATIONS = [15, 32, 46, 60]

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
    logger.info(
        "Building creative brief from preferences: duration=%r resolution=%r aspect_ratio=%r "
        "style=%r camera_motion=%r composition=%r focus_and_lens=%r ambiance=%r",
        preferences.get("duration"),
        preferences.get("resolution"),
        preferences.get("aspect_ratio"),
        preferences.get("style"),
        preferences.get("camera_motion"),
        preferences.get("composition"),
        preferences.get("focus_and_lens"),
        preferences.get("ambiance"),
    )

    resolution = preferences.get("resolution", "720p")
    if resolution not in ALLOWED_RESOLUTIONS:
        logger.warning("Invalid resolution %r; defaulting to 720p", resolution)
        resolution = "720p"

    aspect_ratio = preferences.get("aspect_ratio", "16:9")
    if aspect_ratio not in ALLOWED_ASPECT_RATIOS:
        logger.warning("Invalid aspect_ratio %r; defaulting to 16:9", aspect_ratio)
        aspect_ratio = "16:9"
        
    try:
        duration = int(preferences.get("duration", 15))
    except (ValueError, TypeError):
        logger.warning("Invalid duration %r; defaulting to 15", preferences.get("duration"))
        duration = 15
        
    if duration not in ALLOWED_DURATIONS:
        logger.warning("Unsupported duration %r; defaulting to 15", duration)
        duration = 15

    style = preferences.get("style", "cinematic")
    if style not in ALLOWED_STYLES:
        logger.warning("Invalid style %r; defaulting to cinematic", style)
        style = "cinematic"
        
    camera_motion = preferences.get("camera_motion", "dolly shot")
    if camera_motion not in ALLOWED_CAMERA_MOTIONS:
        logger.warning("Invalid camera_motion %r; defaulting to dolly shot", camera_motion)
        camera_motion = "dolly shot"
        
    composition = preferences.get("composition", "wide shot")
    if composition not in ALLOWED_COMPOSITIONS:
        logger.warning("Invalid composition %r; defaulting to wide shot", composition)
        composition = "wide shot"

    focus_and_lens = preferences.get("focus_and_lens", "shallow depth of field")
    if focus_and_lens not in ALLOWED_FOCUS_LENS:
        logger.warning("Invalid focus_and_lens %r; defaulting to shallow depth of field", focus_and_lens)
        focus_and_lens = "shallow depth of field"

    ambiance = preferences.get("ambiance", "cool blue tones")
    if ambiance not in ALLOWED_AMBIANCE:
        logger.warning("Invalid ambiance %r; defaulting to cool blue tones", ambiance)
        ambiance = "cool blue tones"

    brief = {
        "resolution": resolution,
        "aspect_ratio": aspect_ratio,
        "duration": duration,
        "style": style,
        "camera_motion": camera_motion,
        "composition": composition,
        "focus_and_lens": focus_and_lens,
        "ambiance": ambiance,
    }
    logger.info("Creative brief resolved: %s", brief)
    return brief

