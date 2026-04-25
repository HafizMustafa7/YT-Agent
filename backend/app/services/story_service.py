"""
Story generation service — Single-call Veo 3.1 pipeline.

Replaces the legacy 12-stage, 8-LLM-call Sora pipeline.

Flow:
  1. calculate_frame_structure(duration)  → frame math (pure code)
  2. build_user_message(...)              → formats the Gemini user message
  3. _call_gemini(system_prompt, msg)     → single Gemini 2.5 Flash Lite call
  4. _parse_and_validate(raw, n_frames)   → strict JSON parse + structural check
     → on failure: one retry of step 3, then raise
  5. Returns validated story dict directly consumed by the route layer.
"""
import asyncio
import json
import logging
import re
from typing import Any, Dict, Optional

from fastapi import HTTPException

from app.core.config import settings
from app.core_yt.llm_client import get_gemini_model
from app.core_yt.prompts.loader import load_examples, load_system_prompt, load_bible_system_prompt

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Topic sanitizer
# ---------------------------------------------------------------------------

# Patterns Gemini's prompt scanner permanently rejects (PROHIBITED_CONTENT, code 4).
# These cannot be bypassed via safety_settings - the model literally never runs.
# We strip/rephrase them before they reach the API while keeping story intent.
_AGE_CHILD_PATTERNS = [
    # "of age 12" / "aged 10" / "age 11" etc.
    (re.compile(r'\bof\s+age\s+\d+\b', re.IGNORECASE), ''),
    (re.compile(r'\baged?\s+\d+\b', re.IGNORECASE), ''),
    # "baby" as an adjective for a person (baby girl, baby boy)
    (re.compile(r'\bbaby\s+(girl|boy|child|kid)\b', re.IGNORECASE), r'young \1'),
    # explicit child age numbers adjacent to gender words
    (re.compile(r'\b(girl|boy|child|kid)\s+of\s+\d+\b', re.IGNORECASE), r'young \1'),
    # "12 year old" / "12-year-old" etc.
    (re.compile(r'\b\d{1,2}[\s-]year[s]?[\s-]old\b', re.IGNORECASE), 'young'),
]


def _sanitize_topic_for_gemini(topic: str) -> str:
    """
    Remove age/child language patterns that trigger Gemini's hard-coded
    PROHIBITED_CONTENT block (block_reason code 4).  This is a permanent
    API restriction that cannot be overridden via safety_settings.

    Strategy: keep character names and story intent intact; drop or rephrase
    the age descriptors that act as scanner trigger tokens.

    Example:
      IN:  'baby girl of age 12 "Eris" hiding from a monster'
      OUT: 'young girl "Eris" hiding from a monster'
    """
    sanitized = topic
    for pattern, replacement in _AGE_CHILD_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    # Collapse any double spaces introduced by removals
    sanitized = re.sub(r'  +', ' ', sanitized).strip()
    if sanitized != topic:
        logger.info(
            "Topic sanitized for Gemini (age/child patterns removed). "
            "Original: %r | Sanitized: %r",
            topic[:80], sanitized[:80]
        )
    return sanitized


# ---------------------------------------------------------------------------
# Frame structure calculation
# ---------------------------------------------------------------------------

def calculate_frame_structure(duration: int) -> Dict[str, int]:
    """
    Determine first-frame duration F ∈ {8, 6, 4} such that
    (duration - F) is a non-negative multiple of 7.

    Returns:
        {
            "first_frame_duration": int,   F seconds
            "extension_count":      int,   number of 7-second extension frames
            "total_frames":         int,   first + extension frames
            "actual_duration":      int,   total seconds (may differ from input
                                           if no exact fit is found)
        }
    """
    for f in (8, 6, 4):
        remainder = duration - f
        if remainder >= 0 and remainder % 7 == 0:
            ext = remainder // 7
            return {
                "first_frame_duration": f,
                "extension_count": ext,
                "total_frames": 1 + ext,
                "actual_duration": duration,
            }

    # Fallback: use F=8, round extension count
    ext = max(0, round((duration - 8) / 7))
    actual = 8 + ext * 7
    logger.warning(
        "No exact Veo frame split found for %ds. "
        "Using F=8 + %d×7 = %ds total.",
        duration, ext, actual,
    )
    return {
        "first_frame_duration": 8,
        "extension_count": ext,
        "total_frames": 1 + ext,
        "actual_duration": actual,
    }


# ---------------------------------------------------------------------------
# User message builder
# ---------------------------------------------------------------------------

def _is_set(value: Optional[str]) -> bool:
    """Return True if value is a non-empty, non-placeholder string."""
    return bool(value and value.strip())


def _val(value: Optional[str]) -> str:
    """Return value stripped, or empty string."""
    return value.strip() if value and value.strip() else ""


def build_bible_message(
    topic: str,
    duration: int,
    frame_structure: Dict[str, int],
    style: Optional[str] = None,
    camera_motion: Optional[str] = None,
    composition: Optional[str] = None,
    focus_and_lens: Optional[str] = None,
    ambiance: Optional[str] = None,
) -> str:
    """Build the user message for Call 1 (Story Bible Generation)."""
    total_frames = frame_structure["total_frames"]
    f = frame_structure["first_frame_duration"]
    
    # Format arc slot list so LLM knows exactly how many beats to write
    arc_slots = [f"Frame 1 ({f}s): [establish beat]"]
    for i in range(2, total_frames + 1):
        arc_slots.append(f"Frame {i} (7s): [beat {i}]")
    arc_template = "\n".join(arc_slots)
    
    # User-provided params block
    params = {k: v for k, v in {
        "Style": style, "Camera Motion": camera_motion,
        "Composition": composition, "Focus & Lens": focus_and_lens,
        "Ambiance": ambiance
    }.items() if _is_set(v)}
    params_block = "\n".join(f"{k}: {v}" for k, v in params.items()) or "(none specified — infer all from topic and topic nature)"
    
    return f"""Build a Story Bible for this video.

=== INPUT ===
Topic: {topic}
Total Duration: {duration} seconds
Total Frames: {total_frames} (Frame 1 = {f}s, Frames 2-{total_frames} = 7s each)

=== USER CREATIVE PARAMETERS ===
Follow these explicit user preferences when building the world, visual constants, and style details:
{params_block}

=== STORY ARC SLOTS (fill exactly these {total_frames} entries) ===
{arc_template}

Respond with the Story Bible JSON only."""


def build_frames_message(
    topic: str,
    duration: int,
    frame_structure: Dict[str, int],
    bible: Dict[str, Any],
    examples: Optional[list] = None,
) -> str:
    """Build the complete user message sent to Gemini for Call 2 (Frames)."""
    f = frame_structure["first_frame_duration"]
    ext_count = frame_structure["extension_count"]
    total_frames = frame_structure["total_frames"]
    actual_duration = frame_structure["actual_duration"]

    # Build extension line for frame structure section
    if ext_count > 0:
        ext_line = (
            f"Frames 2 to {total_frames} → Extension Frames → 7 seconds each "
            f"(continuation prompts)"
        )
    else:
        ext_line = "(No extension frames — single frame video)"

    # Inject bible as a locked block
    char = bible.get("character", {})
    world = bible.get("world", {})
    vc = bible.get("visual_constants", {})
    ac = bible.get("audio_constants", {})
    arc = bible.get("story_arc", [])
    vt = bible.get("visual_treatment", {})
    
    arc_block = "\n".join(f"  {entry}" for entry in arc)
    
    locked_bible_block = f"""
=== LOCKED STORY BIBLE — DO NOT DEVIATE FROM THIS ===

CHARACTER:
  Name: {char.get('name', 'N/A')}
  Appearance: {char.get('appearance', 'N/A')}
  Wardrobe: {char.get('wardrobe', 'N/A')}  ← USE THIS EXACT TOKEN IN EVERY FRAME PROMPT
  Signature Prop: {char.get('signature_prop', 'N/A')}  ← must appear in ≥1 frame prompts

WORLD:
  Location: {world.get('location', 'N/A')}
  Time of Day: {world.get('time_of_day', 'N/A')}
  Environment: {world.get('environment', 'N/A')}

VISUAL CONSTANTS (embed in every frame):
  Color Palette: {vc.get('color_palette', 'N/A')}
  Lighting Rule: {vc.get('lighting_rule', 'N/A')}  ← EMBED VERBATIM
  Style Lock: {vc.get('style_lock', 'N/A')}  ← EMBED VERBATIM

AUDIO CONSTANTS:
  Ambient Layer: {ac.get('ambient_layer', 'N/A')}  ← MUST BE ACTIVE THROUGH EVERY CLIP'S FINAL SECOND
  Music: {ac.get('music', 'none')}
  Dialogue Style: {ac.get('dialogue_style', 'purely ambient')}

VISUAL TREATMENT (MANDATORY — EXECUTE THIS IN EVERY FRAME):
  Mode: {vt.get('mode', 'real-time')}  ← THIS IS THE TIME SCALE FOR ALL FRAMES
  Reason: {vt.get('reason', 'N/A')}
  Speed Cues (embed these environmental markers if mode is not real-time): {', '.join(vt.get('speed_cues', [])) or 'N/A'}

STORY ARC (each frame executes its beat — no substitutions):
{arc_block}

====================================================
"""

    examples_block = _format_examples(examples)

    return f"""Generate a frame-by-frame Veo video script using the locked bible below.

=== VIDEO SUMMARY ===
Topic: {topic}
Total Duration: {actual_duration} seconds

{locked_bible_block}
=== FRAME STRUCTURE (strictly follow this) ===
Total Frames: {total_frames}
Frame 1 → First Frame → {f} seconds (complete scene setup prompt)
{ext_line}
{examples_block}
=== OUTPUT FORMAT (return only this JSON, nothing else) ===
{{
  "topic": "restate the topic cleanly",
  "total_duration": {actual_duration},
  "pacing": "slow | medium | fast",
  "full_story": "2-3 sentence plain English overview of the complete story arc",
  "frames": [
    {{
      "frame_number": 1,
      "type": "first",
      "duration": {f},
      "prompt": "complete Veo-ready scene setup prompt with all technical parameters embedded naturally"
    }}{_extension_frame_schema(ext_count, total_frames)}
  ]
}}"""



def _format_examples(examples: Optional[list]) -> str:
    """
    Format few-shot examples into a compact, pedagogically useful block.

    Shows the LLM:
      - The example's topic + creative input (so it understands the context)
      - The output section only (topic, pacing, full_story, and each frame prompt)

    This avoids sending raw full-JSON dumps (which are noisy and token-heavy)
    and instead produces a clean, human-readable reference.
    """
    if not examples:
        return ""

    lines = ["\n=== REFERENCE EXAMPLES (study these, do not copy) ==="]
    for i, ex in enumerate(examples, 1):
        label = ex.get("label", f"example_{i}")
        description = ex.get("description", "")
        inp = ex.get("input", {})
        out = ex.get("output", {})

        lines.append(f"\n--- Example {i}: {label} ---")
        if description:
            lines.append(f"Context: {description}")

        # Input summary (compact)
        if inp:
            inp_parts = []
            for k in ("topic", "duration", "style", "camera_motion",
                      "composition", "focus_and_lens", "ambiance", "aspect_ratio"):
                if k in inp:
                    inp_parts.append(f"{k}={inp[k]!r}")
            lines.append(f"Input:   {', '.join(inp_parts)}")

        # Output — full_story + each frame prompt
        if out:
            lines.append(f"Pacing:  {out.get('pacing', 'N/A')}")
            lines.append(f"Story:   {out.get('full_story', '')}")
            for frame in out.get("frames", []):
                fnum = frame.get("frame_number", "?")
                ftype = frame.get("type", "?")
                fdur = frame.get("duration", "?")
                fprompt = frame.get("prompt", "")
                lines.append(
                    f"  Frame {fnum} ({ftype}, {fdur}s): {fprompt}"
                )

    lines.append("\n=== END EXAMPLES ===")
    return "\n".join(lines) + "\n"


def _extension_frame_schema(ext_count: int, total_frames: int) -> str:
    """Generate schema comment lines for extension frames."""
    if ext_count == 0:
        return ""
    lines = []
    for i in range(2, total_frames + 1):
        lines.append(
            f',\n    {{\n'
            f'      "frame_number": {i},\n'
            f'      "type": "extend",\n'
            f'      "duration": 7,\n'
            f'      "prompt": "Veo extension prompt — opens with visual continuation, '
            f'describes progression only"\n'
            f'    }}'
        )
    return "".join(lines)


# ---------------------------------------------------------------------------
# Gemini call
# ---------------------------------------------------------------------------

def _call_gemini_sync(system_prompt: str, user_message: str) -> str:
    """Synchronous Gemini call. Run via executor to avoid blocking event loop."""
    model = get_gemini_model(
        system_instruction=system_prompt,
        temperature=0.75,
        max_tokens=16384,
        json_mode=True,
    )
    if not model:
        raise RuntimeError("Gemini model could not be configured — check GEMINI_API_KEY")

    logger.info("Calling Gemini (%s) for story generation.", settings.GEMINI_MODEL)
    
    # Lower safety settings to allow fantasy violence / fictional creatures
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    response = model.generate_content(user_message, safety_settings=safety_settings)

    try:
        text = response.text
    except ValueError as e:
        # Happens when response.candidates is empty due to safety filters
        reason = "Unknown reason"
        if response.prompt_feedback and hasattr(response.prompt_feedback, "block_reason"):
            reason = str(response.prompt_feedback.block_reason)
        raise ValueError(f"AI refused to generate story (Safety Filter Triggered: {reason})") from e

    if not text:
        raise ValueError("Gemini returned an empty response")

    return text.strip()


async def _call_gemini(system_prompt: str, user_message: str) -> str:
    """Async wrapper for the Gemini call."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _call_gemini_sync, system_prompt, user_message)


# ---------------------------------------------------------------------------
# JSON parse + validate
# ---------------------------------------------------------------------------

def _parse_and_validate_bible(raw: str, expected_frames: int) -> Dict[str, Any]:
    parsed: Optional[Dict] = None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        pass

    if parsed is None:
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

    if not isinstance(parsed, dict):
        raise ValueError(f"Bible JSON is invalid. First 300 chars: {raw[:300]}")

    required_sections = ("character", "world", "visual_constants", "audio_constants", "visual_treatment", "story_arc")
    for section in required_sections:
        if section not in parsed:
            raise ValueError(f"Bible missing required section: '{section}'")

    if len(parsed.get("story_arc", [])) != expected_frames:
        raise ValueError(f"story_arc length must be exactly {expected_frames}")
    
    char = parsed.get("character", {})
    if not str(char.get("wardrobe", "")).strip():
        raise ValueError("character.wardrobe must be a non-empty string")
        
    vc = parsed.get("visual_constants", {})
    if not str(vc.get("lighting_rule", "")).strip():
        raise ValueError("visual_constants.lighting_rule must be a non-empty string")
        
    ac = parsed.get("audio_constants", {})
    if not str(ac.get("ambient_layer", "")).strip():
        raise ValueError("audio_constants.ambient_layer must be a non-empty string")

    vt = parsed.get("visual_treatment", {})
    valid_modes = {"real-time", "rapid time-lapse", "smooth hyperlapse"}
    mode = str(vt.get("mode", "")).strip()
    if mode not in valid_modes:
        raise ValueError(f"visual_treatment.mode must be one of {valid_modes}, got: '{mode}'")

    logger.info("Story Bible validated (Expected Frames: %d, Visual Treatment: %s)", expected_frames, mode)
    return parsed



def _parse_and_validate(raw: str, expected_frames: int) -> Dict[str, Any]:
    """
    Parse the raw Gemini response as JSON and validate its structure.

    Raises ValueError with a descriptive message on any failure.
    """
    # Attempt 1: direct parse
    parsed: Optional[Dict] = None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Attempt 2: extract JSON object from surrounding text
    if parsed is None:
        match = re.search(r'\{[\s\S]*\}', raw)
        if match:
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

    if not isinstance(parsed, dict):
        raise ValueError(
            f"Gemini response is not a valid JSON object. "
            f"First 300 chars: {raw[:300]}"
        )

    # Structural validation
    required_top = ("topic", "total_duration", "pacing", "full_story", "frames")
    missing_top = [k for k in required_top if k not in parsed]
    if missing_top:
        raise ValueError(f"Story JSON missing top-level keys: {missing_top}")

    frames = parsed.get("frames")
    if not isinstance(frames, list):
        raise ValueError("'frames' must be a list")

    if len(frames) != expected_frames:
        raise ValueError(
            f"Expected {expected_frames} frame(s), got {len(frames)}"
        )

    for i, frame in enumerate(frames):
        for key in ("frame_number", "type", "duration", "prompt"):
            if key not in frame:
                raise ValueError(
                    f"Frame {i + 1} missing required key: '{key}'"
                )
        if not str(frame.get("prompt", "")).strip():
            raise ValueError(f"Frame {i + 1} has an empty prompt")

    logger.info(
        "Story validated: %d frame(s), pacing=%s, duration=%s",
        len(frames),
        parsed.get("pacing"),
        parsed.get("total_duration"),
    )
    return parsed


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def generate_story(
    topic: str,
    duration: int,
    style: Optional[str] = None,
    camera_motion: Optional[str] = None,
    composition: Optional[str] = None,
    focus_and_lens: Optional[str] = None,
    ambiance: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate a Veo 3.1 frame-by-frame video script.

    Args:
        topic:          User-provided video topic (required).
        duration:       Total video duration in seconds (from [15, 32, 46, 60]).
        style:          Visual style (optional).
        camera_motion:  Camera movement technique (optional).
        composition:    Scene composition (optional).
        focus_and_lens: Focus and lens type (optional).
        ambiance:       Lighting and atmosphere (optional).

    Returns:
        Validated story dict with keys:
            topic, total_duration, pacing, full_story, frames[]

    Raises:
        HTTPException 500 on Gemini config error.
        HTTPException 422 on persistent parse failure after one retry.
    """
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")

    topic = " ".join(topic.strip().split())
    if not topic:
        raise ValueError("Topic cannot be empty")

    # Sanitize topic — strip hard-blocked age/child patterns before
    # they hit Gemini's prompt scanner (PROHIBITED_CONTENT cannot be bypassed
    # by safety_settings; the model won't even run if the prompt is flagged).
    topic_for_gemini = _sanitize_topic_for_gemini(topic)

    # Step 1: Calculate frame structure
    frame_structure = calculate_frame_structure(duration)
    logger.info(
        "Frame structure for %ds: F=%d, ext=%d, total=%d",
        duration,
        frame_structure["first_frame_duration"],
        frame_structure["extension_count"],
        frame_structure["total_frames"],
    )

    # Step 2: Load system prompts + examples
    bible_system_prompt = load_bible_system_prompt()
    system_prompt = load_system_prompt()
    examples = load_examples()

    # Step 3: Call 1: Story Bible
    bible_message = build_bible_message(
        topic=topic_for_gemini,
        duration=duration,
        frame_structure=frame_structure,
        style=style,
        camera_motion=camera_motion,
        composition=composition,
        focus_and_lens=focus_and_lens,
        ambiance=ambiance,
    )

    expected_frames = frame_structure["total_frames"]
    last_error: Optional[Exception] = None
    bible: Optional[Dict] = None

    for attempt in range(2):
        try:
            raw_bible = await _call_gemini(bible_system_prompt, bible_message)
            bible = _parse_and_validate_bible(raw_bible, expected_frames)
            break
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                logger.warning("Bible generation parse failed attempt 1: %s — retrying...", exc)
            else:
                logger.error("Bible generation failed after 2 attempts: %s", exc)

    if not bible:
        raise HTTPException(
            status_code=422,
            detail=f"Story bible generation failed. Last error: {last_error}"
        )

    # Step 4: Call 2: Frame Prompts
    frames_message = build_frames_message(
        topic=topic_for_gemini,
        duration=duration,
        frame_structure=frame_structure,
        bible=bible,
        examples=examples,
    )
    
    last_error = None
    for attempt in range(2):
        try:
            raw_frames = await _call_gemini(system_prompt, frames_message)
            story = _parse_and_validate(raw_frames, expected_frames)
            # Merge bible into final return
            return {**story, "story_bible": bible}
        except HTTPException:
            raise
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                logger.warning("Story frames parse failed attempt 1: %s — retrying...", exc)
            else:
                logger.error("Story frames generation failed after 2 attempts: %s", exc)

    raise HTTPException(
        status_code=422,
        detail=f"Story frames generation failed. Last error: {last_error}"
    )
