"""
Story generation service — Unified Vertex AI pipeline.

Uses Gemini 2.5 Pro (thinking model) on Vertex AI. Single LLM call produces
both the Story Bible and all frame prompts in one coherent reasoning pass.

Consistency approach:
  - Story arc is planned in full before any frame is written (thinking model).
  - Each frame covers exactly the major beat assigned to it in the story arc;
    supporting sub-actions within a beat are allowed and encouraged.
  - No entry/exit state machine — Veo 3.1's extend feature handles visual
    continuity across clip boundaries automatically.
  - Anti-overlap: extension prompts describe ONLY what is new in their beat;
    they never re-describe actions that already appeared in a previous frame.
  - 6 narrative structures: conflict, transformation, journey, mystery, showcase, crescendo.
  - One auth path: same Vertex AI service account as Veo video generation.

Flow:
  1. calculate_frame_structure(duration)   → frame math (pure code, unchanged)
  2. build_unified_message(...)            → single user message
  3. _call_vertex_ai(system_prompt, msg)   → one Gemini 2.5 Pro call with thinking
  4. _parse_and_validate_unified(raw)      → strict JSON parse + structural check
  5. Returns validated story dict
"""
import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.core.config import settings

from app.core_yt.prompts.loader import load_system_prompt, load_examples

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Topic sanitizer (unchanged)
# ---------------------------------------------------------------------------

_AGE_CHILD_PATTERNS = [
    (re.compile(r'\bof\s+age\s+\d+\b', re.IGNORECASE), ''),
    (re.compile(r'\baged?\s+\d+\b', re.IGNORECASE), ''),
    (re.compile(r'\bbaby\s+(girl|boy|child|kid)\b', re.IGNORECASE), r'young \1'),
    (re.compile(r'\b(girl|boy|child|kid)\s+of\s+\d+\b', re.IGNORECASE), r'young \1'),
    (re.compile(r'\b\d{1,2}[\s-]year[s]?[\s-]old\b', re.IGNORECASE), 'young'),
]


def _sanitize_topic_for_gemini(topic: str) -> str:
    """Strip age/child patterns that trigger Gemini's hard-coded PROHIBITED_CONTENT block."""
    sanitized = topic
    for pattern, replacement in _AGE_CHILD_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    sanitized = re.sub(r'  +', ' ', sanitized).strip()
    if sanitized != topic:
        logger.info(
            "Topic sanitized. Original: %r | Sanitized: %r",
            topic[:80], sanitized[:80]
        )
    return sanitized


# ---------------------------------------------------------------------------
# Frame structure calculation (unchanged — durations: 15, 32, 46, 60)
# ---------------------------------------------------------------------------

def calculate_frame_structure(duration: int) -> Dict[str, int]:
    """
    Determine first-frame duration F ∈ {8, 6, 4} such that
    (duration - F) is a non-negative multiple of 7.
    Supports durations: 15, 32, 46, 60 (and any other valid combo).
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
        "No exact Veo frame split found for %ds. Using F=8 + %d×7 = %ds total.",
        duration, ext, actual,
    )
    return {
        "first_frame_duration": 8,
        "extension_count": ext,
        "total_frames": 1 + ext,
        "actual_duration": actual,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_set(value: Optional[str]) -> bool:
    return bool(value and value.strip())


def _val(value: Optional[str]) -> str:
    return value.strip() if value and value.strip() else ""


# ---------------------------------------------------------------------------
# Unified user message builder
# ---------------------------------------------------------------------------

def build_unified_message(
    topic: str,
    duration: int,
    frame_structure: Dict[str, int],
    style: Optional[str] = None,
    camera_motion: Optional[str] = None,
    composition: Optional[str] = None,
    focus_and_lens: Optional[str] = None,
    ambiance: Optional[str] = None,
    examples: Optional[list] = None,
) -> str:
    """
    Build the single user message sent to Gemini 2.5 Pro.
    The message contains everything the model needs to generate both
    the Story Bible AND all frame prompts in one thinking pass.
    """
    total_frames = frame_structure["total_frames"]
    f = frame_structure["first_frame_duration"]
    actual_duration = frame_structure["actual_duration"]

    # Arc slot template — tells the model exactly how many frames to write and their durations
    arc_slots = [f"Frame 1 ({f}s): [establish beat — causes Frame 2 to begin]"]
    for i in range(2, total_frames + 1):
        if i == total_frames:
            arc_slots.append(f"Frame {i} (7s): [resolution beat — ends the arc]")
        else:
            arc_slots.append(f"Frame {i} (7s): [progression beat — causes Frame {i+1} to begin]")
    arc_template = "\n".join(arc_slots)

    # User creative parameters
    params = {k: v for k, v in {
        "Style": style,
        "Camera Motion": camera_motion,
        "Composition": composition,
        "Focus & Lens": focus_and_lens,
        "Ambiance": ambiance,
    }.items() if _is_set(v)}
    params_block = (
        "\n".join(f"{k}: {v}" for k, v in params.items())
        or "(none specified — infer all from topic and its nature)"
    )

    # Few-shot examples block
    examples_block = _format_examples(examples)

    # Output schema for frames section
    frame_schema = _build_frame_schema(total_frames, f, actual_duration)

    return f"""Generate a unified Story Bible + frame-by-frame Veo video script.
Apply your thinking to plan the FULL causal narrative arc before writing any frame.

=== INPUT ===
Topic: {topic}
Total Duration: {actual_duration} seconds
Total Frames: {total_frames}
Frame 1 duration: {f} seconds
Extension frames (2-{total_frames}): 7 seconds each

=== USER CREATIVE PARAMETERS ===
{params_block}

=== STORY ARC SLOTS (plan these before writing frames) ===
Each beat must causally lead to the next — no abrupt scene changes.
{arc_template}

{examples_block}=== OUTPUT (return ONLY the JSON object below, no other text) ===
{frame_schema}"""


def _format_examples(examples: Optional[list]) -> str:
    """Format few-shot examples for the LLM."""
    if not examples:
        return ""

    lines = ["\n=== REFERENCE EXAMPLES (study story flow and anti-overlap technique — do not copy) ==="]
    for i, ex in enumerate(examples, 1):
        label = ex.get("label", f"example_{i}")
        description = ex.get("description", "")
        inp = ex.get("input", {})
        out = ex.get("output", {})

        lines.append(f"\n--- Example {i}: {label} ---")
        if description:
            lines.append(f"Context: {description}")

        if inp:
            inp_parts = []
            for k in ("topic", "duration", "style", "camera_motion", "composition",
                      "focus_and_lens", "ambiance", "aspect_ratio"):
                if k in inp:
                    inp_parts.append(f"{k}={inp[k]!r}")
            lines.append(f"Input:   {', '.join(inp_parts)}")

        if out:
            bible = out.get("story_bible", {})
            ns = bible.get("narrative_structure", "N/A")
            lines.append(f"Narrative Structure: {ns}")
            lines.append(f"Pacing:  {out.get('pacing', 'N/A')}")
            lines.append(f"Story:   {out.get('full_story', '')}")
            for frame in out.get("frames", []):
                fnum = frame.get("frame_number", "?")
                ftype = frame.get("type", "?")
                fdur = frame.get("duration", "?")
                fprompt = frame.get("prompt", "")
                lines.append(
                    f"  Frame {fnum} ({ftype}, {fdur}s):"
                    f"\n    prompt: {fprompt}"
                )

    lines.append("\n=== END EXAMPLES ===\n")
    return "\n".join(lines) + "\n"


def _build_frame_schema(total_frames: int, first_duration: int, total_duration: int) -> str:
    """Build the output JSON schema string to inject into the user message."""
    frames_list = []
    frames_list.append(f"""    {{
      "frame_number": 1,
      "type": "first",
      "duration": {first_duration},
      "prompt": "[complete Veo scene-setup prompt — 5-7 lines covering Frame 1's major beat with all bible tokens]"
    }}""")
    for i in range(2, total_frames + 1):
        frames_list.append(f"""    {{
      "frame_number": {i},
      "type": "extend",
      "duration": 7,
      "prompt": "[Veo extension prompt — 2-4 lines, opens with continuation phrase, covers ONLY Frame {i}'s new major beat]"
    }}""")

    frames_json = ",\n".join(frames_list)

    return f"""{{
  "story_bible": {{
    "character": {{
      "name": "...",
      "appearance": "...",
      "wardrobe": "...",
      "signature_prop": "..."
    }},
    "world": {{
      "location": "...",
      "environment": "...",
      "time_of_day": "..."
    }},
    "visual_constants": {{
      "color_palette": "...",
      "lighting_rule": "...",
      "style_lock": "..."
    }},
    "audio_constants": {{
      "ambient_layer": "...",
      "music": null,
      "dialogue_style": "purely ambient | spoken dialogue | internal voiceover"
    }},
    "narrative_structure": "conflict | transformation | journey | mystery | showcase | crescendo",
    "narrative_reason": "..."
  }},
  "topic": "...",
  "total_duration": {total_duration},
  "pacing": "slow | medium | fast",
  "full_story": "2-3 sentence overview showing the causal chain from start to end",
  "frames": [
{frames_json}
  ]
}}"""


# ---------------------------------------------------------------------------
# Vertex AI call (Gemini 2.5 Pro with thinking)
# ---------------------------------------------------------------------------

def _call_vertex_ai_sync(system_prompt: str, user_message: str) -> str:
    """
    Call Gemini 2.5 Pro via Vertex AI with thinking enabled.
    Synchronous — run via executor to avoid blocking the async event loop.
    """
    from app.core_yt.llm_client import get_vertex_ai_client
    from google.genai import types

    client = get_vertex_ai_client()

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=0.7,
        max_output_tokens=16384,
        response_mime_type="application/json",
        thinking_config=types.ThinkingConfig(include_thoughts=True),
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT",        threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH",       threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
        ],
    )

    logger.info("Calling Gemini 2.5 Pro (Vertex AI) for story generation.")
    response = client.models.generate_content(
        model=settings.STORY_MODEL,
        contents=user_message,
        config=config,
    )

    try:
        text = response.text
    except ValueError as e:
        reason = "Unknown"
        if hasattr(response, "prompt_feedback") and response.prompt_feedback:
            if hasattr(response.prompt_feedback, "block_reason"):
                reason = str(response.prompt_feedback.block_reason)
        raise ValueError(f"AI refused to generate story (Safety Filter: {reason})") from e

    if not text:
        raise ValueError("Gemini 2.5 Pro returned an empty response")

    return text.strip()


async def _call_vertex_ai(system_prompt: str, user_message: str) -> str:
    """Async wrapper for the Vertex AI call."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _call_vertex_ai_sync, system_prompt, user_message)


# ---------------------------------------------------------------------------
# JSON parse + validate
# ---------------------------------------------------------------------------

def _extract_json(raw: str) -> Optional[Dict]:
    """Try to parse JSON from raw string — direct parse then regex extraction."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    match = re.search(r'\{[\s\S]*\}', raw)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


def _parse_and_validate_unified(raw: str, expected_frames: int) -> Dict[str, Any]:
    """
    Parse and validate the unified JSON output (bible + frames together).
    Raises ValueError with a descriptive message on any failure.
    """
    parsed = _extract_json(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f"Response is not a valid JSON object. First 300 chars: {raw[:300]}")

    # --- Validate Story Bible ---
    bible = parsed.get("story_bible")
    if not isinstance(bible, dict):
        raise ValueError("Missing or invalid 'story_bible' section")

    for section in ("character", "world", "visual_constants", "audio_constants"):
        if section not in bible:
            raise ValueError(f"story_bible missing required section: '{section}'")

    char = bible.get("character", {})
    if not str(char.get("wardrobe", "")).strip():
        raise ValueError("story_bible.character.wardrobe must be a non-empty string")

    vc = bible.get("visual_constants", {})
    if not str(vc.get("lighting_rule", "")).strip():
        raise ValueError("story_bible.visual_constants.lighting_rule must be non-empty")
    if not str(vc.get("style_lock", "")).strip():
        raise ValueError("story_bible.visual_constants.style_lock must be non-empty")

    ac = bible.get("audio_constants", {})
    if not str(ac.get("ambient_layer", "")).strip():
        raise ValueError("story_bible.audio_constants.ambient_layer must be non-empty")

    valid_structures = {"conflict", "transformation", "journey", "mystery", "showcase", "crescendo"}
    ns = str(bible.get("narrative_structure", "")).strip()
    if ns not in valid_structures:
        raise ValueError(
            f"story_bible.narrative_structure must be one of {valid_structures}, got: '{ns}'"
        )

    # --- Validate top-level fields ---
    for key in ("topic", "total_duration", "pacing", "full_story", "frames"):
        if key not in parsed:
            raise ValueError(f"Story JSON missing top-level key: '{key}'")

    frames = parsed.get("frames")
    if not isinstance(frames, list):
        raise ValueError("'frames' must be a list")

    if len(frames) != expected_frames:
        raise ValueError(f"Expected {expected_frames} frames, got {len(frames)}")

    # --- Validate each frame ---
    for i, frame in enumerate(frames):
        for key in ("frame_number", "type", "duration", "prompt"):
            if key not in frame:
                raise ValueError(f"Frame {i + 1} missing required key: '{key}'")
        if not str(frame.get("prompt", "")).strip():
            raise ValueError(f"Frame {i + 1} has an empty prompt")

    logger.info(
        "Story validated: %d frames, pacing=%s, structure=%s, duration=%s",
        len(frames),
        parsed.get("pacing"),
        ns,
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
    Generate a Veo 3.1 frame-by-frame video script using Gemini 2.5 Pro on Vertex AI.

    Args:
        topic:          User-provided video topic (required).
        duration:       Total video duration in seconds ([15, 32, 46, 60]).
        style:          Visual style (optional).
        camera_motion:  Camera movement technique (optional).
        composition:    Scene composition (optional).
        focus_and_lens: Focus and lens type (optional).
        ambiance:       Lighting and atmosphere (optional).

    Returns:
        Validated story dict:
            story_bible, topic, total_duration, pacing, full_story, frames[]
            Each frame includes: frame_number, type, duration, prompt

    Raises:
        HTTPException 500 on Vertex AI config error.
        HTTPException 422 on persistent parse failure after one retry.
    """
    if not settings.VERTEX_AI_PROJECT_ID:
        raise HTTPException(status_code=500, detail="VERTEX_AI_PROJECT_ID is not configured")
    if not settings.GOOGLE_APPLICATION_CREDENTIALS:
        raise HTTPException(status_code=500, detail="GOOGLE_APPLICATION_CREDENTIALS is not configured")

    topic = " ".join(topic.strip().split())
    if not topic:
        raise ValueError("Topic cannot be empty")

    topic_for_llm = _sanitize_topic_for_gemini(topic)

    # Step 1: Calculate frame structure
    frame_structure = calculate_frame_structure(duration)
    logger.info(
        "Frame structure for %ds: F=%d, ext=%d, total=%d",
        duration,
        frame_structure["first_frame_duration"],
        frame_structure["extension_count"],
        frame_structure["total_frames"],
    )

    # Step 2: Load prompts + examples
    system_prompt = load_system_prompt()
    examples = load_examples()

    # Step 3: Build unified user message (bible + frames in one prompt)
    message = build_unified_message(
        topic=topic_for_llm,
        duration=duration,
        frame_structure=frame_structure,
        style=style,
        camera_motion=camera_motion,
        composition=composition,
        focus_and_lens=focus_and_lens,
        ambiance=ambiance,
        examples=examples,
    )

    expected_frames = frame_structure["total_frames"]
    logger.info(
        "Story generation request prepared: topic_len=%d sanitized_topic_len=%d expected_frames=%d "
        "style=%r camera_motion=%r composition=%r focus_and_lens=%r ambiance=%r",
        len(topic),
        len(topic_for_llm),
        expected_frames,
        style,
        camera_motion,
        composition,
        focus_and_lens,
        ambiance,
    )
    last_error: Optional[Exception] = None

    # Step 4: Single call with one retry
    for attempt in range(2):
        try:
            raw = await _call_vertex_ai(system_prompt, message)
            story = _parse_and_validate_unified(raw, expected_frames)

            for frame in story["frames"]:
                prompt_text = str(frame.get("prompt", ""))
                frame_number = frame.get("frame_number")
                logger.info(
                    "Generated story frame %s: type=%r duration=%r prompt_len=%d prompt_preview=%r",
                    frame_number,
                    frame.get("type"),
                    frame.get("duration"),
                    len(prompt_text),
                    prompt_text[:350],
                )

            logger.info(
                "Story generated successfully: %d frames, structure=%s, pacing=%s",
                len(story["frames"]),
                story.get("story_bible", {}).get("narrative_structure", "unknown"),
                story.get("pacing", "unknown"),
            )
            return story

        except HTTPException:
            raise
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                logger.warning(
                    "Story generation attempt 1 failed: %s — retrying...", exc
                )
            else:
                logger.error("Story generation failed after 2 attempts: %s", exc)

    raise HTTPException(
        status_code=422,
        detail=f"Story generation failed after 2 attempts. Last error: {last_error}",
    )

async def suggest_dynamic_creative_params(topic: str, context: Optional[str] = None) -> Dict[str, List[str]]:
    """
    Call Gemini 2.5 Pro to suggest dynamic creative parameters tailored to the topic.
    Returns lists of strings for style, camera_motion, composition, focus_and_lens, and ambiance.
    """
    from app.core_yt.creative_builder import (
        ALLOWED_STYLES, ALLOWED_CAMERA_MOTIONS, ALLOWED_COMPOSITIONS,
        ALLOWED_FOCUS_LENS, ALLOWED_AMBIANCE
    )

    system_prompt = (
        "You are an expert AI video director. Your task is to select highly tailored, creative, "
        "and visually striking suggestions for a video's creative parameters based on its topic. "
        "You MUST ONLY choose options from the provided allowed lists."
    )

    context_str = f"Context: {context}" if context else ""
    user_message = f"""Topic: {topic}
{context_str}

Please select 3-5 options for each of the following video creative parameters, choosing ONLY from the exact allowed lists provided:

Allowed Styles: {ALLOWED_STYLES}
Allowed Camera Motions: {ALLOWED_CAMERA_MOTIONS}
Allowed Compositions: {ALLOWED_COMPOSITIONS}
Allowed Focus Options: {ALLOWED_FOCUS_LENS}
Allowed Ambiances: {ALLOWED_AMBIANCE}

Return ONLY a JSON object with keys: "styles", "camera_motions", "compositions", "focus_options", "ambiances".
Each key must map to an array of strings containing your selections. Do NOT include markdown blocks or any other text."""

    for attempt in range(2):
        try:
            raw = await _call_vertex_ai(system_prompt, user_message)
            parsed = _extract_json(raw)
            if not isinstance(parsed, dict):
                raise ValueError("Response is not a valid JSON object.")

            # Ensure all keys exist, default to empty list if not
            return {
                "styles": parsed.get("styles", []),
                "camera_motions": parsed.get("camera_motions", []),
                "compositions": parsed.get("compositions", []),
                "focus_options": parsed.get("focus_options", []),
                "ambiances": parsed.get("ambiances", []),
            }
        except Exception as exc:
            if attempt == 0:
                logger.warning("Dynamic creative params attempt 1 failed: %s — retrying...", exc)
            else:
                logger.error("Dynamic creative params failed after 2 attempts: %s", exc)
                # Fallback to defaults
                return {
                    "styles": ALLOWED_STYLES[:5],
                    "camera_motions": ALLOWED_CAMERA_MOTIONS[:5],
                    "compositions": ALLOWED_COMPOSITIONS[:5],
                    "focus_options": ALLOWED_FOCUS_LENS[:4],
                    "ambiances": ALLOWED_AMBIANCE[:5],
                }
