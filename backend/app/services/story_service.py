"""
Story generation service — 12-Stage Pipeline (8 LLM calls).

Stages (LLM calls marked with *):
  1* Topic Enrichment
  2* Story Definition (4-act arc)
  3* Character Identification  → CHARACTER LOCK
  4* Object & Environment Registry → OBJECT/ENV LOCK
  5* Scene Segmentation        (locks injected)
  6* Scene Importance Scoring  (1-5 per scene)
     Duration Allocation       (pure math — no LLM)
  7* Shot Planning             (locks injected; state-machine continuity)
  8* Visual Prompt Generation  (locks injected; Sora-official format)
     Final Assembly            (pure code)

Consistency strategy: Option A (prevention).
Character lock + object/env lock are injected verbatim into every
downstream prompt (Stages 5, 7, 8). No post-hoc review stage.
"""
import asyncio
import logging
from collections import defaultdict
from fastapi import HTTPException
from typing import List, Dict, Any, Optional
import json
import re

from app.core.config import settings
from app.core_yt.llm_client import get_gemini_model

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sora-valid clip durations (seconds). 4s re-enabled for non-crux scenes.
# ---------------------------------------------------------------------------
ALLOWED_FRAME_DURATIONS: List[int] = [8, 15, 32, 46, 60]


# ===========================================================================
# JSON extraction helpers (unchanged from previous implementation)
# ===========================================================================

def extract_json_from_text(text: str) -> List[Dict]:
    """Extract JSON array from AI response text."""
    logger.debug("Attempting to extract JSON from text of length: %d", len(text))

    try:
        result = json.loads(text.strip())
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    try:
        code_block_match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', text, re.IGNORECASE)
        if code_block_match:
            result = json.loads(code_block_match.group(1))
            if isinstance(result, list):
                return result
    except json.JSONDecodeError:
        pass

    try:
        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end > start:
            json_str = text[start:end]
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
            result = json.loads(json_str)
            if isinstance(result, list):
                return result
    except json.JSONDecodeError:
        pass

    logger.warning("All JSON array extraction methods failed. First 500 chars: %s", text[:500])
    return []


def extract_json_object_from_text(text: str) -> Dict[str, Any]:
    """Extract a JSON object from AI response text.

    If LLM returns an array of scene objects (e.g. [{"scene_number": 1, "frames": [...]}]),
    this function will flatten them into {"frames": [all frames merged]} so downstream
    code expecting {"frames": [...]} still works.
    """
    logger.debug("Attempting to extract JSON object from text of length: %d", len(text))

    def _normalize_to_dict(parsed: Any) -> Dict[str, Any]:
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list) and parsed:
            all_frames = []
            for item in parsed:
                if isinstance(item, dict):
                    if "frames" in item and isinstance(item["frames"], list):
                        scene_num = item.get("scene_number")
                        for frame in item["frames"]:
                            if isinstance(frame, dict):
                                if scene_num is not None and "scene_number" not in frame:
                                    frame["scene_number"] = scene_num
                                all_frames.append(frame)
                    else:
                        all_frames.append(item)
            if all_frames:
                return {"frames": all_frames}
        return {}

    try:
        result = json.loads(text.strip())
        normalized = _normalize_to_dict(result)
        if normalized:
            return normalized
    except json.JSONDecodeError:
        pass

    try:
        code_block_match = re.search(r'```(?:json)?\s*([\{\[][\s\S]*?[\}\]])\s*```', text, re.IGNORECASE)
        if code_block_match:
            result = json.loads(code_block_match.group(1))
            normalized = _normalize_to_dict(result)
            if normalized:
                return normalized
    except json.JSONDecodeError:
        pass

    try:
        obj_start = text.find('{')
        arr_start = text.find('[')

        if obj_start != -1 and (arr_start == -1 or obj_start < arr_start):
            start = obj_start
            end = text.rfind('}') + 1
        elif arr_start != -1:
            start = arr_start
            end = text.rfind(']') + 1
        else:
            start, end = -1, 0

        if start != -1 and end > start:
            json_str = text[start:end]
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
            result = json.loads(json_str)
            normalized = _normalize_to_dict(result)
            if normalized:
                return normalized
    except json.JSONDecodeError:
        pass

    logger.warning("All JSON object extraction methods failed. First 500 chars: %s", text[:500])
    return {}


# ===========================================================================
# Gemini call helpers
# ===========================================================================

def _call_gemini_sync(prompt: str, json_mode: bool = False) -> str:
    """Synchronous Gemini call (internal; use call_gemini() instead)."""
    system_instruction = None
    if json_mode:
        system_instruction = (
            "You are a helpful assistant that responds only in valid JSON format. "
            "Do not include any text before or after the JSON. "
            "Ensure all JSON is properly formatted with correct syntax."
        )

    model = get_gemini_model(
        system_instruction=system_instruction,
        temperature=0.7,
        max_tokens=8192,
        json_mode=json_mode
    )

    if not model:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")

    logger.info("Calling Gemini with model: %s", settings.GEMINI_MODEL)
    response = model.generate_content(prompt)

    if not response.text:
        logger.error("Gemini returned empty response. Response: %s", response)
        raise HTTPException(status_code=500, detail="Gemini API returned empty response")

    result = response.text.strip()
    logger.debug("Gemini response length: %d chars", len(result))
    return result


async def call_gemini(prompt: str, json_mode: bool = False) -> str:
    """Call Gemini API without blocking the event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _call_gemini_sync, prompt, json_mode)


async def call_gemini_json_with_retry(
    step_name: str,
    prompt: str,
    retries: int = 2,
    retry_delay_seconds: float = 1.0,
) -> Dict[str, Any]:
    """Call Gemini in JSON mode with step-local retries."""
    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            raw = await call_gemini(prompt, json_mode=True)
            parsed = extract_json_object_from_text(raw)
            if not parsed:
                raise ValueError(f"{step_name}: empty/invalid JSON object")
            return parsed
        except Exception as e:
            last_error = e
            if attempt < retries:
                logger.warning(
                    "%s failed on attempt %d/%d: %s. Retrying step...",
                    step_name, attempt + 1, retries + 1, e,
                )
                await asyncio.sleep(retry_delay_seconds * (attempt + 1))
            else:
                logger.error("%s failed after %d attempts: %s", step_name, retries + 1, e)
    raise ValueError(f"{step_name} failed after retries: {last_error}")



# ===========================================================================
# Misc helpers
# ===========================================================================

def _normalize_duration_to_int(value: Any, default: int = 44) -> int:
    try:
        d = int(value)
        return d if d > 0 else default
    except (TypeError, ValueError):
        return default


def video_to_dict(video) -> Dict:
    if isinstance(video, dict):
        return video
    return {
        'id': getattr(video, 'id', ''),
        'title': getattr(video, 'title', ''),
        'description': getattr(video, 'description', ''),
        'tags': getattr(video, 'tags', []),
        'views': getattr(video, 'views', 0),
        'likes': getattr(video, 'likes', 0),
        'comments': getattr(video, 'comments', 0),
        'thumbnail': getattr(video, 'thumbnail', ''),
        'duration': getattr(video, 'duration', ''),
        'channel': getattr(video, 'channel', ''),
        'ai_confidence': getattr(video, 'ai_confidence', 0),
        'url': getattr(video, 'url', '')
    }


def _validate_user_topic(topic: str) -> str:
    clean = " ".join((topic or "").split()).strip()
    if not clean:
        raise ValueError("Topic cannot be empty.")
    if len(clean) < 3:
        raise ValueError("Topic must be at least 3 characters.")
    unsafe_terms = ["hate speech", "terrorism", "sexual violence", "self-harm"]
    if any(term in clean.lower() for term in unsafe_terms):
        raise ValueError("Topic contains unsafe content.")
    return clean


def _snap_to_sora(seconds: float) -> int:
    """Snap a duration to the nearest valid Sora clip length (4, 8, or 12)."""
    allowed = sorted(ALLOWED_FRAME_DURATIONS)
    best = allowed[0]
    best_dist = abs(seconds - best)
    for d in allowed[1:]:
        dist = abs(seconds - d)
        if dist < best_dist:
            best, best_dist = d, dist
    return best


# ===========================================================================
# Lock preamble builder (Prevention-based consistency — Option A)
# ===========================================================================

def _build_lock_preamble(
    characters: List[Dict[str, Any]],
    objects_registry: List[Dict[str, Any]],
    environment: Dict[str, Any],
) -> str:
    """Build the unified CHARACTER LOCK + OBJECT/ENV LOCK block.

    This block is injected verbatim at the top of Stage 5, 7, and 8
    prompts. By including it in every downstream prompt the LLM is
    forced to reuse the exact same traits — no post-hoc consistency
    check is required (Option A strategy).
    """
    lines = ["=== CHARACTER LOCK — copy exactly into every visual prompt ==="]
    for c in characters:
        lines.append(
            f"{c.get('name', 'Character')} (id={c.get('character_id', '?')}): "
            f"age {c.get('age', '?')} | "
            f"{c.get('appearance_description', '')} | "
            f"clothing: {c.get('clothing', '')} | "
            f"distinct: {c.get('distinct_visual_features', '')}"
        )

    lines.append("")
    lines.append("=== OBJECT & ENVIRONMENT LOCK — maintain in every frame ===")
    for obj in objects_registry:
        lines.append(
            f"{obj.get('object_id', 'obj')}: "
            f"{obj.get('description', '')} — "
            f"visual: {obj.get('visual_characteristics', '')}"
        )

    lines.append("")
    lines.append("=== GLOBAL ENVIRONMENT ===")
    lines.append(f"Setting: {environment.get('setting', '')}")
    lines.append(f"Time of day: {environment.get('time_of_day', '')}")
    lines.append(f"Weather: {environment.get('weather', '')}")
    lines.append(f"Lighting baseline: {environment.get('lighting_baseline', '')}")
    lines.append(f"Visual tone: {environment.get('visual_tone', '')}")

    return "\n".join(lines)


# ===========================================================================
# Main pipeline
# ===========================================================================

async def generate_story_and_frames(
    selected_video,
    user_topic: str,
    max_frames: int = 10,
    creative_brief: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate story pipeline with 12 conceptual stages (8 LLM calls).

    LLM Calls:
      1) Topic Enrichment
      2) Story Definition  (4-act arc)
      3) Character Identification  → lock
      4) Object & Environment Registry → lock
      5) Scene Segmentation        (lock injected)
      6) Scene Importance Scoring
         Duration Allocation       (pure math)
      7) Shot Planning             (lock injected; state-machine)
      8) Visual Prompt Generation  (lock injected; Sora format)
         Final Assembly            (pure code)
    """
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")

    try:
        selected_video = video_to_dict(selected_video)
        clean_topic = _validate_user_topic(user_topic)

        # Extract creative brief settings with sensible defaults
        target_total_duration = creative_brief.get("duration", 15) if creative_brief else 15
        style = creative_brief.get("style", "cinematic") if creative_brief else "cinematic"
        camera_motion = creative_brief.get("camera_motion", "dolly shot") if creative_brief else "dolly shot"
        composition = creative_brief.get("composition", "wide shot") if creative_brief else "wide shot"
        focus_and_lens = creative_brief.get("focus_and_lens", "shallow depth of field") if creative_brief else "shallow depth of field"
        ambiance = creative_brief.get("ambiance", "cool blue tones") if creative_brief else "cool blue tones"
        resolution = creative_brief.get("resolution", "720p") if creative_brief else "720p"
        aspect_ratio = creative_brief.get("aspect_ratio", "16:9") if creative_brief else "16:9"

        # ===================================================================
        # STAGE 1 — Topic Enrichment (LLM Call #1)
        # ===================================================================
        logger.info("STAGE 1: Topic Enrichment...")
        stage1_prompt = f"""You are a cinematic content strategist specializing in visual storytelling.

User topic: "{clean_topic}"
Visual Style: {style}
Target Scene Composition: {composition}
Ambiance: {ambiance}

Task:
Expand this topic into a rich visual scenario optimized for a short-form video exactly {target_total_duration} seconds long.
Infer and define all environmental details that a cinematographer would need.

Return JSON only:
{{
  "expanded_topic": "rich one-sentence hook describing the scenario",
  "environment": {{
    "setting": "detailed physical setting description",
    "time_of_day": "e.g. early morning, dusk, midday",
    "weather": "e.g. overcast, sunny, light rain",
    "lighting_baseline": "natural lighting description matching time+weather",
    "visual_tone": "{visual_style}"
  }},
  "key_actions": ["action 1", "action 2", "action 3"],
  "important_objects": ["object 1", "object 2", "object 3"],
  "possible_characters": ["character description 1", "character description 2"],
  "core_conflict": "central dramatic tension of the video",
  "theme": "emotional or thematic underpinning",
  "emotional_arc": "how the viewer's emotion should move from start to end"
}}
Return JSON only."""

        stage1 = await call_gemini_json_with_retry("STAGE 1: Topic Enrichment", stage1_prompt)
        if not stage1:
            raise ValueError("STAGE 1 failed: invalid topic enrichment output.")

        environment_base = stage1.get("environment", {
            "setting": clean_topic,
            "time_of_day": "daytime",
            "weather": "clear",
            "lighting_baseline": "natural daylight",
            "visual_tone": visual_style
        })

        # ===================================================================
        # STAGE 2 — Story Definition (LLM Call #2)
        # ===================================================================
        logger.info("STAGE 2: Story Definition...")
        stage2_prompt = f"""You are a cinematic story architect specializing in short-form visual narratives.

Topic enrichment:
{json.dumps(stage1, ensure_ascii=True)}

Story format: {story_format}

Task:
Create a tight 4-act story arc. The story should naturally unfold over 16 to 44 seconds.
The story should be VISUALLY driven — no dialogue-heavy scenes.
The CRUX (main event) must be the most visually powerful, longest, and highest-action segment.

Rules:
- Setup and Resolution should be brief visual beats.
- Rising action escalates toward the crux.
- The crux is the undeniable visual climax of the video.
- Every act must be understandable without any dialogue.

Return JSON only:
{{
  "setup": "brief description of opening visual state — what the viewer sees first",
  "rising_action": "how tension or anticipation builds visually",
  "crux": "the exact main event — this is the climax, the most important scene",
  "resolution": "brief visual closing — how the scene settles after the crux",
  "narrative_through_line": "one sentence describing the emotional journey",
  "opening_hook": "compelling first visual that grabs attention immediately"
}}
Return JSON only."""

        stage2 = await call_gemini_json_with_retry("STAGE 2: Story Definition", stage2_prompt)
        if not stage2:
            raise ValueError("STAGE 2 failed: invalid story definition output.")

        # ===================================================================
        # STAGE 3 — Character Identification → LOCK (LLM Call #3)
        # ===================================================================
        logger.info("STAGE 3: Character Identification (lock)...")
        stage3_prompt = f"""You are a live-action character designer for cinematic short films.

Story context:
{json.dumps(stage2, ensure_ascii=True)}

Environment:
{json.dumps(environment_base, ensure_ascii=True)}

Possible character hints from topic analysis:
{json.dumps(stage1.get("possible_characters", []), ensure_ascii=True)}

Task:
Identify and fully define all characters who appear in this video.
Character descriptions must be CONCRETE and FIXED — they will be copy-pasted
into every frame prompt to enforce visual consistency.

Rules:
- Live-action photorealistic characters only. No animated or stylized characters.
- Clothing must be specific: e.g. "orange high-visibility vest, white hard hat, dark cargo trousers, steel-toe boots" — NOT "work clothes".
- Appearance must include exact details: hair color, length, skin tone, build.
- Keep character count minimal (1–3 max for short-form videos).

Return JSON only:
{{
  "characters": [
    {{
      "character_id": "char_1",
      "role_in_story": "e.g. lead worker, site supervisor",
      "name": "descriptive name or role label",
      "age": 35,
      "appearance_description": "hair color+style, skin tone, build, height",
      "clothing": "complete, specific clothing description",
      "personality_traits": ["trait1", "trait2"],
      "distinct_visual_features": "one or two instantly recognizable features"
    }}
  ]
}}
Return JSON only."""

        stage3 = await call_gemini_json_with_retry("STAGE 3: Character Identification", stage3_prompt)
        characters_locked: List[Dict[str, Any]] = stage3.get("characters", [])
        if not isinstance(characters_locked, list):
            characters_locked = []
        if not characters_locked:
            raise ValueError("STAGE 3 failed: no characters produced.")

        # ===================================================================
        # STAGE 4 — Object & Environment Registry → LOCK (LLM Call #4)
        # ===================================================================
        logger.info("STAGE 4: Object & Environment Registry (lock)...")
        stage4_prompt = f"""You are a film art director and set designer.

Story:
{json.dumps(stage2, ensure_ascii=True)}

Environment:
{json.dumps(environment_base, ensure_ascii=True)}

Key objects from topic analysis:
{json.dumps(stage1.get("important_objects", []), ensure_ascii=True)}

Task:
Build the complete registry of every OBJECT and ENVIRONMENTAL ELEMENT that will
appear in this video. This registry will be injected into every frame prompt to
prevent objects from appearing or disappearing unexpectedly.

Rules:
- Be specific about visual characteristics (colour, texture, condition, size).
- Include ALL major props, vehicles, structures, and environmental elements.
- The registry is the single source of truth — if an object is not listed here, it cannot appear in any frame.

Return JSON only:
{{
  "objects": [
    {{
      "object_id": "obj_1",
      "description": "concrete noun description, e.g. yellow tower crane",
      "visual_characteristics": "specific details: color, texture, condition, size/scale"
    }}
  ],
  "environment_confirmed": {{
    "setting": "finalized full setting description",
    "time_of_day": "{environment_base.get('time_of_day', 'daytime')}",
    "weather": "{environment_base.get('weather', 'clear')}",
    "lighting_baseline": "{environment_base.get('lighting_baseline', 'natural daylight')}",
    "visual_tone": "{visual_style}",
    "palette_anchors": ["color 1", "color 2", "color 3", "color 4"]
  }}
}}
Return JSON only."""

        stage4 = await call_gemini_json_with_retry("STAGE 4: Object & Environment Registry", stage4_prompt)
        objects_locked: List[Dict[str, Any]] = stage4.get("objects", [])
        if not isinstance(objects_locked, list):
            objects_locked = []
        environment_confirmed: Dict[str, Any] = stage4.get("environment_confirmed", environment_base)

        # Build the lock preamble injected into all downstream prompts
        lock_preamble = _build_lock_preamble(characters_locked, objects_locked, environment_confirmed)

        # ===================================================================
        # STAGE 5 — Scene Segmentation (LLM Call #5) — locks injected
        # ===================================================================
        logger.info("STAGE 5: Scene Segmentation...")
        stage5_prompt = f"""You are a cinematic scene planner.

{lock_preamble}

Story arc:
{json.dumps(stage2, ensure_ascii=True)}

Narrative constraints:
- Total video duration: exactly {target_total_duration} seconds.
- Visual Style: {style}
- The crux scene is: "{stage2.get('crux', '')}"

Task:
Divide the story into scenes that cover ALL four acts (setup, rising_action, crux, resolution).
Each scene maps to exactly ONE act. The crux must be its own scene.

IMPORTANT: Give minimal scenes to setup and resolution (they are brief).
The crux scene and rising action carry the weight of the video.

Return JSON only:
{{
  "scenes": [
    {{
      "scene_id": "scene_1",
      "act": "setup | rising_action | crux | resolution",
      "narrative_role": "what this scene achieves in the story",
      "description": "detailed visual description of what happens",
      "key_action": "single most important action that occurs (max 15 words)",
      "characters_present": ["char_1"],
      "objects_featured": ["obj_1", "obj_2"],
      "location_within_environment": "specific area within the global setting"
    }}
  ]
}}
Rules:
- Minimum 3 scenes, maximum 6 scenes.
- EVERY scene must reuse characters and objects from the lock above — no new elements.
- Setup and resolution scenes are short beats; crux is the most expanded scene.
Return JSON only."""

        stage5 = await call_gemini_json_with_retry("STAGE 5: Scene Segmentation", stage5_prompt)
        scenes: List[Dict[str, Any]] = stage5.get("scenes", [])
        if not isinstance(scenes, list) or not scenes:
            raise ValueError("STAGE 5 failed: no scenes generated.")

        # ===================================================================
        # STAGE 6 — Scene Importance Scoring (LLM Call #6)
        # ===================================================================
        logger.info("STAGE 6: Scene Importance Scoring (%d scenes)...", len(scenes))
        stage6_prompt = f"""You are a film editor evaluating scene importance for time allocation.

Scenes to evaluate:
{json.dumps(scenes, ensure_ascii=True)}

Crux scene is: the scene with act="crux"

Task:
Score each scene on three dimensions (scale 1–5 each):
  - narrative_significance: how critical is this scene to the overall story?
  - emotional_intensity: how emotionally engaging is this scene?
  - visual_complexity: how many visual elements, movements, and details does this scene require?

total_importance = narrative_significance + emotional_intensity + visual_complexity (max 15)

Rules:
- The crux scene MUST have the highest total_importance score.
- Setup and resolution should have LOW scores (minimal screen time).
- Be honest and differentiated — not every scene should score 5.

Return JSON only:
{{
  "scene_scores": [
    {{
      "scene_id": "scene_1",
      "narrative_significance": 3,
      "emotional_intensity": 2,
      "visual_complexity": 2,
      "total_importance": 7,
      "reasoning": "brief justification"
    }}
  ]
}}
Return JSON only."""

        stage6 = await call_gemini_json_with_retry("STAGE 6: Scene Importance Scoring", stage6_prompt)
        scene_scores_raw: List[Dict[str, Any]] = stage6.get("scene_scores", [])

        # Build importance map: scene_id -> total_importance
        importance_map: Dict[str, int] = {}
        for ss in scene_scores_raw:
            sid = ss.get("scene_id", "")
            total = ss.get("total_importance", 5)
            try:
                importance_map[sid] = max(1, int(total))
            except (TypeError, ValueError):
                importance_map[sid] = 5

        # Ensure every scene has a score (fallback to 5)
        for sc in scenes:
            sid = sc.get("scene_id", "")
            if sid not in importance_map:
                importance_map[sid] = 5

        # ===================================================================
        # STAGE 7 — Shot Planning (LLM Call #7) — locks injected, state machine, dynamic duration
        # ===================================================================
        logger.info("STAGE 7: Shot Planning (Dynamic Duration)...")

        # Build a scene summary with importance scores for the LLM
        scenes_with_importance = []
        for sc in scenes:
            sid = sc.get("scene_id", "")
            scenes_with_importance.append({
                **sc,
                "importance_score": importance_map.get(sid, 5),
            })

        stage7_prompt = f"""You are a master cinematographer planning shots for a live-action short film.

{lock_preamble}

Scenes with Importance Scores (higher score = longer screen time, more shots):
{json.dumps(scenes_with_importance, ensure_ascii=True)}

Creative config:
  style={style} | camera_preference={camera_motion} | focus={focus_and_lens} | grade={ambiance}

Task:
For EACH scene, plan its shots. Each shot is one continuous camera clip.
The total sum of ALL shots' duration across ALL scenes must be exactly {target_total_duration} seconds.

Duration & Pacing Rules (CRITICAL):
  - Shot durations must ONLY be from these valid intervals: {', '.join(map(str, ALLOWED_FRAME_DURATIONS))}.
  - Prioritize standard length shots to keep the pacing dynamic.
  - The Crux scene MUST have the longest total duration.
  - Setup and Resolution scenes MUST be brief.
  - Maintain consistent camera angles and visual continuity between shots within the same scene.

State-machine rule:
  - Every shot has a start_state and end_state describing the EXACT physical world state.
  - The start_state of shot N MUST be identical to the end_state of shot N-1.
  - The very first shot's start_state describes the opening frame of the video.
  - The very last shot's end_state is the closing freeze-frame.

Shot types available: wide establishing shot | medium shot | close-up | tracking shot | overhead shot | slow motion shot | handheld ENG

Return JSON only:
{{
  "shot_plan": [
    {{
      "scene_id": "scene_1",
      "shot_id": "shot_1",
      "shot_type": "wide establishing shot",
      "camera_angle": "eye level | low angle | high angle | overhead",
      "camera_movement": "static | slow push-in | tracking left | handheld | slow dolly back",
      "lens": "50mm | 85mm | 35mm | 24mm",
      "subject": "who or what is the main subject",
      "action": "specific action described in beats, e.g. worker takes three steps left and looks up",
      "environment_context": "which part of the environment is visible",
      "lighting_setup": "specific lighting description using palette anchors",
      "depth_of_field": "shallow | deep",
      "duration_seconds": 8,
      "start_state": "exact physical world state at the START of this shot",
      "end_state": "exact physical world state at the END of this shot"
    }}
  ]
}}
Rules:
- Each scene may have 1–3 shots depending on its importance.
- Shot duration must be 4, 8, or 12 only (favoring 4 and 8).
- The sum of ALL shot durations must be between 16 and 44 seconds.
- All characters must wear EXACTLY the clothing from the CHARACTER LOCK above.
- Only use objects from the OBJECT & ENVIRONMENT LOCK above.
- Live-action photorealistic only. No animation.
Return JSON only."""

        stage7 = await call_gemini_json_with_retry("STAGE 7: Shot Planning", stage7_prompt)
        shot_plan: List[Dict[str, Any]] = stage7.get("shot_plan", [])
        if not isinstance(shot_plan, list) or not shot_plan:
            raise ValueError("STAGE 7 failed: no shot plan generated.")

        # ===================================================================
        # POST-STAGE 7 — Dynamic Duration Safeguard
        # We asked the LLM to stay within exact {target_total_duration}s. If it fails, we enforce it here.
        # ===================================================================
        logger.info(f"Enforcing exact duration ({target_total_duration}s) on shot plan...")
        
        # Ensure all durations are valid Sora lengths
        for shot in shot_plan:
            raw_dur = shot.get("duration_seconds", 8)
            shot["duration_seconds"] = min(ALLOWED_FRAME_DURATIONS, key=lambda x: abs(x - raw_dur))

        # Helper to calculate total
        def get_total_duration():
            return sum(s["duration_seconds"] for s in shot_plan)

        # Trimmer loop
        while get_total_duration() > target_total_duration and len(shot_plan) > 1:
            # Find the shot in the LEAST important scene that is currently the SHORTEST.
            # We sort by: Importance (Ascending), Duration (Ascending)
            shot_plan.sort(key=lambda s: (
                importance_map.get(s.get("scene_id", ""), 5), 
                s["duration_seconds"]
            ))
            # Remove the first one
            dropped = shot_plan.pop(0)
            logger.debug(f"Overshot > {target_total_duration}s: dropped shot {dropped.get('shot_id')} (dur {dropped['duration_seconds']}s) from scene {dropped.get('scene_id')}")

        # Padding loop
        while get_total_duration() < target_total_duration:
            # Find the shot in the MOST important scene that we can extend
            # Sort by: Importance (Descending)
            shot_plan.sort(key=lambda s: importance_map.get(s.get("scene_id", ""), 5), reverse=True)
            
            extended = False
            for shot in shot_plan:
                current_dur = shot["duration_seconds"]
                
                # Check if we can increment to the next allowed duration
                current_idx = ALLOWED_FRAME_DURATIONS.index(current_dur) if current_dur in ALLOWED_FRAME_DURATIONS else 0
                if current_idx < len(ALLOWED_FRAME_DURATIONS) - 1:
                    next_dur = ALLOWED_FRAME_DURATIONS[current_idx + 1]
                    logger.debug(f"Undershot < {target_total_duration}s: extended shot {shot.get('shot_id')} from {current_dur}s to {next_dur}s")
                    shot["duration_seconds"] = next_dur
                    extended = True
                    break
            
            if not extended:
                # If all shots are maxed out, duplicate one.
                logger.debug("Edge case fallback: duplicating a shot to hit minimum.")
                dup = dict(shot_plan[0])
                dup["shot_id"] = f"{dup['shot_id']}_dup"
                dup["duration_seconds"] = ALLOWED_FRAME_DURATIONS[0]
                shot_plan.append(dup)

        # Restore strict original temporal order (which might be lost by sorting)
        # We rely on shot_id/scene_id or just general position. Best way is to re-extract from stage7 original order.
        original_order = {s.get("shot_id"): i for i, s in enumerate(stage7.get("shot_plan", []))}
        shot_plan.sort(key=lambda s: original_order.get(s.get("shot_id", ""), 999))

        enforced_total = get_total_duration()
        logger.info(
            "Post-Stage-7 enforcement: enforced_total=%ds shots=%d",
            enforced_total, len(shot_plan),
        )

        # ===================================================================
        # STAGE 8 — Visual Prompt Generation (LLM Call #8) — Sora format
        # ===================================================================
        logger.info("STAGE 8: Visual Prompt Generation (Sora format, %d shots)...", len(shot_plan))

        stage8_prompt = f"""You are a Hollywood director writing video generation prompts for OpenAI Sora.

{lock_preamble}

Creative config (flavor the prose, do NOT label these):
  style={style} | ambiance={ambiance} | focus={focus_and_lens} | camera={camera_motion}

Shot plan:
{json.dumps(shot_plan, ensure_ascii=True)}

Task:
Write a Sora-compliant visual prompt for EACH shot in the shot plan.

=== OFFICIAL SORA PROMPT FORMAT (follow exactly) ===

[Prose scene description — 2-4 sentences. Describe: characters by name + ONE specific clothing 
 detail each, 2-3 key objects from the registry woven naturally into the scene, 
 environment from the lock, weather, lighting feel. DO NOT use headers or labels in prose. 
 Write naturally as a cinematographer briefing their crew.]

Cinematography:
Camera shot: [exact shot type and angle from shot plan]
Lens: [lens from shot plan]
Lighting + palette: [key source, fill, rim description + 3-5 palette anchor colors]
Depth of field: [shallow/deep as planned]
Mood: [single evocative tone word matching the style ({style})]

Actions:
- [Beat 1: specific, timed action e.g. "takes four steps toward the crane, stops"]
- [Beat 2: second visual beat]
- [Beat 3: final beat that brings the shot to its end_state]

Background Sound:
[Diegetic ambient sound only — realistic location sounds, no music score]

=== RULES (critical — violations break video generation) ===
1. Prose section: NO headers, NO labels, NO JSON keys, NO bullet points.
2. Each character must appear with EXACTLY ONE physical appearance detail (e.g. hair color or skin tone)
   AND ONE clothing detail from the CHARACTER LOCK. Format on first appearance:
   "Name (one appearance detail, e.g. dark-haired, tan skin) wearing [one clothing item]"
   Keep this on first mention per shot only. Do not repeat on subsequent mentions.
3. From the object registry, pick the 2-3 MOST VISUALLY IMPORTANT objects for this shot only.
   Weave them into the prose naturally — do NOT list them.
4. ONE single camera movement per shot. ONE primary subject action.
   For multi-shot scenes: maintain visual continuity — do NOT jump to confusing angles between shots in the same scene.
5. The Actions section must describe beats that START at start_state and END at end_state.
6. Live-action photorealistic only. Absolutely no animation or illustrated style.
7. Keep total prompt per shot under 800 characters. Be precise, not verbose.
8. Maintain IDENTICAL character appearance and clothing across ALL shots — no substitutions.

Return JSON only:
{{
  "visual_prompts": [
    {{
      "shot_id": "shot_1",
      "scene_id": "scene_1",
      "visual_prompt": "<full Sora-format prompt as described above>",
      "start_state": "<copied from shot plan>",
      "end_state": "<copied from shot plan>",
      "duration_seconds": 8,
      "audio_direction": {{
        "ambience": "location-appropriate ambient sound",
        "voice_tone": "{tone}",
        "clean_vocal_priority": true
      }}
    }}
  ]
}}
Return JSON only."""

        stage8 = await call_gemini_json_with_retry("STAGE 8: Visual Prompt Generation", stage8_prompt)
        visual_prompts: List[Dict[str, Any]] = stage8.get("visual_prompts", [])
        if not isinstance(visual_prompts, list) or not visual_prompts:
            raise ValueError("STAGE 8 failed: no visual prompts generated.")

        # ===================================================================
        # FINAL ASSEMBLY — pure code, no LLM
        # ===================================================================
        logger.info("Final Assembly (%d shots)...", len(visual_prompts))

        # Build lookup maps
        shot_plan_map: Dict[str, Dict[str, Any]] = {s.get("shot_id", ""): s for s in shot_plan}
        scene_map: Dict[str, Dict[str, Any]] = {sc.get("scene_id", ""): sc for sc in scenes}
        scene_scores_map: Dict[str, Dict[str, Any]] = {
            ss.get("scene_id", ""): ss for ss in scene_scores_raw
        }

        frames: List[Dict[str, Any]] = []
        for idx, vp in enumerate(visual_prompts):
            shot_id = vp.get("shot_id", f"shot_{idx+1}")
            scene_id = vp.get("scene_id", "")
            shot_meta = shot_plan_map.get(shot_id, {})
            scene_meta = scene_map.get(scene_id, {})
            score_meta = scene_scores_map.get(scene_id, {})

            # Duration: prefer shot plan (LLM-specified), fallback to minimum valid Sora duration
            raw_duration = vp.get("duration_seconds") or shot_meta.get("duration_seconds")
            if raw_duration in ALLOWED_FRAME_DURATIONS:
                duration = raw_duration
            else:
                duration = ALLOWED_FRAME_DURATIONS[0]  # Default to 4s (minimum Sora clip)

            # Build a human-readable scene description
            scene_description = " | ".join(filter(None, [
                scene_meta.get("location_within_environment", ""),
                scene_meta.get("key_action", ""),
                f"Act: {scene_meta.get('act', '')}",
            ]))

            sora_prompt = str(vp.get("visual_prompt", "")).strip()
            # Hard cap: 1500 chars gives the full Sora template (prose + Cinematography
            # + Actions + Background Sound) without mid-word truncation.
            # Official guide: longer prompts restrict model creativity, so keep concise.
            if len(sora_prompt) > 1500:
                sora_prompt = sora_prompt[:1500]

            start_state = str(vp.get("start_state", shot_meta.get("start_state", ""))).strip()
            end_state = str(vp.get("end_state", shot_meta.get("end_state", ""))).strip()

            frames.append({
                "frame_num": idx + 1,
                "shot_id": shot_id,
                "scene_id": scene_id,
                "act": scene_meta.get("act", ""),
                "duration_seconds": duration,
                "scene_description": scene_description,
                "ai_video_prompt": sora_prompt,     # Clean Sora-ready prompt
                "narration_text": scene_meta.get("description", ""),
                "transition": "",
                "creative_modules": {
                    "tone": tone,
                    "visual_style": visual_style,
                    "camera_movement": camera_movement,
                    "effects": color_grading,
                    "target_audience": target_audience,
                },
                # frame_plan: all context metadata — NOT sent to video model
                "frame_plan": {
                    "shot_type": shot_meta.get("shot_type", ""),
                    "camera_angle": shot_meta.get("camera_angle", ""),
                    "camera_movement": shot_meta.get("camera_movement", camera_movement),
                    "lens": shot_meta.get("lens", ""),
                    "lighting_setup": shot_meta.get("lighting_setup", ""),
                    "depth_of_field": shot_meta.get("depth_of_field", ""),
                    "start_state": start_state,
                    "end_state": end_state,
                    "subject": shot_meta.get("subject", ""),
                    "characters_present": scene_meta.get("characters_present", []),
                    "objects_featured": scene_meta.get("objects_featured", []),
                    "importance_score": score_meta.get("total_importance", 5),
                    "character_lock": lock_preamble,
                },
                "audio_direction": vp.get("audio_direction", {}),
            })

        if not frames:
            raise ValueError("Final assembly produced no frames.")

        total_duration = sum(f.get("duration_seconds", 8) for f in frames)
        title_val = (
            str(stage1.get("expanded_topic", "")).strip()
            or selected_video.get("title", "")
            or clean_topic[:60]
        )
        themes_val = stage1.get("theme", [])
        if isinstance(themes_val, str):
            themes_val = [themes_val]
        if not isinstance(themes_val, list):
            themes_val = []

        hook_val = str(stage2.get("opening_hook", stage2.get("setup", ""))).strip()[:240]
        emotional_tone = str(stage2.get("narrative_through_line", tone)).strip()

        characters_for_response = [
            f"{c.get('name', 'Character')} — {c.get('appearance_description', '')}; clothing: {c.get('clothing', '')}"
            for c in characters_locked
        ]

        return {
            "enhanced_topic": stage1.get("expanded_topic", clean_topic),
            "title": title_val,
            "full_story": str(stage2.get("narrative_through_line", "")),
            "hook": hook_val,
            "characters": characters_for_response,
            "themes": themes_val,
            "visual_style": visual_style,
            "emotional_tone": emotional_tone,
            "frames": frames,
            "creative_brief": creative_brief,
            "metadata": {
                "total_frames": len(frames),
                "estimated_duration": total_duration,
                "actual_duration": f"{total_duration} seconds (dynamically generated by LLM)",
                "character_based": len(characters_locked) > 0,
                "locked_character_profile": characters_locked,
                "locked_object_registry": objects_locked,
                "environment": environment_confirmed,
                "pipeline_stages": 8,
                "consistency_strategy": "prevention/lock-injection (Option A)",
                "source_video": {
                    "title": selected_video.get("title", ""),
                    "views": selected_video.get("views", 0),
                    "ai_confidence": selected_video.get("ai_confidence", 0),
                },
                "ai_model": settings.GEMINI_MODEL,
            },
        }

    except Exception as e:
        logger.error("Story generation error: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate story and frames: {str(e)}"
        )
