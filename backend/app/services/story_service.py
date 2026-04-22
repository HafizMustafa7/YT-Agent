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
from app.core_yt.prompts.loader import load_examples, load_system_prompt

logger = logging.getLogger(__name__)


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


def build_user_message(
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
    """Build the complete user message sent to Gemini."""
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

    # Separate provided vs missing params
    params = {
        "Style": style,
        "Camera Motion": camera_motion,
        "Composition": composition,
        "Focus & Lens": focus_and_lens,
        "Ambiance": ambiance,
    }
    provided_lines = []
    missing_keys = []
    for label, val in params.items():
        if _is_set(val):
            provided_lines.append(f"{label}: {_val(val)}")
        else:
            missing_keys.append(label)

    # Specifications block — only show params the user actually set
    if provided_lines:
        specs_block = "\n".join(provided_lines)
    else:
        specs_block = "(no creative parameters specified — infer all from topic)"

    # Inference instruction block — explicit directive for missing params
    if missing_keys:
        infer_list = "\n".join(f"  - {k}" for k in missing_keys)
        inference_block = f"""
=== LLM INFERENCE REQUIRED ===
The following parameters were NOT specified by the user.
You MUST autonomously determine the best value for each one based on the
topic, its natural mood, the content type, and the pacing you select.
Do NOT leave them implied — embed your chosen values explicitly inside
each frame prompt as if the user had specified them.

Parameters to infer:
{infer_list}

Guidance for inference:
  - Style: match the topic's natural register (e.g. cinematic for drama,
    hyperrealistic for product, sci-fi for tech, etc.)
  - Camera Motion: match pacing (tracking/steady for action, dolly/pull-back
    for calm, aerial for landscape, POV for immersive).
  - Composition: match subject type (wide for establishing, close-up for
    detail, low-angle for power, eye-level for intimacy).
  - Focus & Lens: match mood (shallow DoF for cinematic, wide-angle for
    environment, macro for detail).
  - Ambiance: match tone and time-of-day implied by the topic.
==============================="""
    else:
        inference_block = ""

    # Few-shot examples block — compact, pedagogical format
    examples_block = _format_examples(examples)

    return f"""Generate a frame-by-frame Veo video script using the specifications below.

=== VIDEO SPECIFICATIONS ===
Topic: {topic}
Total Duration: {actual_duration} seconds
{specs_block}
{inference_block}
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
    response = model.generate_content(user_message)

    if not response.text:
        raise ValueError("Gemini returned an empty response")

    return response.text.strip()


async def _call_gemini(system_prompt: str, user_message: str) -> str:
    """Async wrapper for the Gemini call."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _call_gemini_sync, system_prompt, user_message)


# ---------------------------------------------------------------------------
# JSON parse + validate
# ---------------------------------------------------------------------------

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

    # Step 1: Calculate frame structure
    frame_structure = calculate_frame_structure(duration)
    logger.info(
        "Frame structure for %ds: F=%d, ext=%d, total=%d",
        duration,
        frame_structure["first_frame_duration"],
        frame_structure["extension_count"],
        frame_structure["total_frames"],
    )

    # Step 2: Load system prompt + examples
    system_prompt = load_system_prompt()
    examples = load_examples()

    # Step 3: Build user message
    user_message = build_user_message(
        topic=topic,
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

    # Step 4: Call Gemini with one retry on parse failure
    last_error: Optional[Exception] = None
    for attempt in range(2):
        try:
            raw = await _call_gemini(system_prompt, user_message)
            story = _parse_and_validate(raw, expected_frames)
            return story
        except HTTPException:
            raise
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                logger.warning(
                    "Story parse failed on attempt 1: %s — retrying once...", exc
                )
            else:
                logger.error("Story generation failed after 2 attempts: %s", exc)

    raise HTTPException(
        status_code=422,
        detail=(
            f"Story generation failed after retrying. "
            f"Last error: {last_error}"
        ),
    )
