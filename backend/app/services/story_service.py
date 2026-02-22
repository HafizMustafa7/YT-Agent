"""
Story generation service using MegaLLM API (OpenAI-compatible).
Uses the OpenAI SDK with MegaLLM's base URL for story and frame generation.
"""
import asyncio
import logging
from fastapi import HTTPException
from typing import List, Dict, Any, Optional
import json
import re
from itertools import product

from app.core.config import settings
from app.core_yt.llm_client import get_megallm_client

logger = logging.getLogger(__name__)


def extract_json_from_text(text: str) -> List[Dict]:
    """Extract JSON array from AI response text."""
    logger.debug("Attempting to extract JSON from text of length: %d", len(text))

    # First try to parse the entire text as JSON
    try:
        result = json.loads(text.strip())
        if isinstance(result, list):
            logger.debug("Successfully parsed entire text as JSON array")
            return result
    except json.JSONDecodeError as e:
        logger.debug("Could not parse entire text: %s", e)

    # Try to find JSON between code blocks first (common AI response format)
    try:
        code_block_match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', text, re.IGNORECASE)
        if code_block_match:
            json_str = code_block_match.group(1)
            logger.debug("Found JSON in code block, length: %d", len(json_str))
            result = json.loads(json_str)
            if isinstance(result, list):
                logger.debug("Successfully parsed code block JSON array, got %d items", len(result))
                return result
    except json.JSONDecodeError as e:
        logger.debug("Could not parse code block JSON: %s", e)

    # Try to extract the outermost JSON array by finding the first [ and last ]
    try:
        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end > start:
            json_str = text[start:end]
            logger.debug("Found JSON array from index %d to %d, length: %d", start, end, len(json_str))

            # Clean up common formatting issues
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)

            result = json.loads(json_str)
            if isinstance(result, list):
                logger.debug("Successfully parsed extracted JSON array, got %d items", len(result))
                return result
    except json.JSONDecodeError as e:
        logger.debug("Could not parse extracted JSON array: %s", e)

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
        """Convert parsed JSON to dict, handling array-of-scenes format."""
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list) and parsed:
            # Check if it's an array of scene objects with nested "frames"
            all_frames = []
            for item in parsed:
                if isinstance(item, dict):
                    if "frames" in item and isinstance(item["frames"], list):
                        # Add scene_number to each frame if present
                        scene_num = item.get("scene_number")
                        for frame in item["frames"]:
                            if isinstance(frame, dict):
                                if scene_num is not None and "scene_number" not in frame:
                                    frame["scene_number"] = scene_num
                                all_frames.append(frame)
                    else:
                        # Item itself might be a frame
                        all_frames.append(item)
            if all_frames:
                return {"frames": all_frames}
        return {}

    # First try to parse entire text as object
    try:
        result = json.loads(text.strip())
        normalized = _normalize_to_dict(result)
        if normalized:
            return normalized
    except json.JSONDecodeError as e:
        logger.debug("Could not parse entire text as object: %s", e)

    # Try code block (object or array)
    try:
        code_block_match = re.search(r'```(?:json)?\s*([\{\[][\s\S]*?[\}\]])\s*```', text, re.IGNORECASE)
        if code_block_match:
            result = json.loads(code_block_match.group(1))
            normalized = _normalize_to_dict(result)
            if normalized:
                return normalized
    except json.JSONDecodeError as e:
        logger.debug("Could not parse code block JSON: %s", e)

    # Try outermost object or array
    try:
        # Find first { or [ and matching last } or ]
        obj_start = text.find('{')
        arr_start = text.find('[')
        
        if obj_start != -1 and (arr_start == -1 or obj_start < arr_start):
            # Object comes first
            start = obj_start
            end = text.rfind('}') + 1
        elif arr_start != -1:
            # Array comes first
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
    except json.JSONDecodeError as e:
        logger.debug("Could not parse extracted JSON: %s", e)

    logger.warning("All JSON object extraction methods failed. First 500 chars: %s", text[:500])
    return {}


def _call_megallm_sync(prompt: str, json_mode: bool = False) -> str:
    """Synchronous MegaLLM call (internal; use call_megallm() instead)."""
    client = get_megallm_client()
    if not client:
        raise HTTPException(status_code=500, detail="MegaLLM API key not configured")

    messages = []

    if json_mode:
        messages.append({
            "role": "system",
            "content": "You are a helpful assistant that responds only in valid JSON format. Do not include any text before or after the JSON. Ensure all JSON is properly formatted with correct syntax."
        })

    messages.append({"role": "user", "content": prompt})

    logger.info("Calling MegaLLM with model: %s", settings.MEGALLM_MODEL)

    response = client.chat.completions.create(
        model=settings.MEGALLM_MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=8192
    )

    if not response.choices or not response.choices[0].message.content:
        logger.error("MegaLLM returned empty response. Response: %s", response)
        raise HTTPException(status_code=500, detail="MegaLLM API returned empty response")

    result = response.choices[0].message.content.strip()
    logger.debug("MegaLLM response length: %d chars", len(result))
    return result


async def call_megallm(prompt: str, json_mode: bool = False) -> str:
    """Call MegaLLM API without blocking the event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _call_megallm_sync, prompt, json_mode)


async def call_megallm_json_with_retry(
    step_name: str,
    prompt: str,
    retries: int = 2,
    retry_delay_seconds: float = 1.0,
) -> Dict[str, Any]:
    """
    Call MegaLLM in JSON mode with step-local retries.
    Retries only this failing step and returns parsed JSON object.
    """
    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            raw = await call_megallm(prompt, json_mode=True)
            parsed = extract_json_object_from_text(raw)
            if not parsed:
                raise ValueError(f"{step_name}: empty/invalid JSON object")
            return parsed
        except Exception as e:
            last_error = e
            if attempt < retries:
                logger.warning(
                    "%s failed on attempt %d/%d: %s. Retrying step...",
                    step_name,
                    attempt + 1,
                    retries + 1,
                    e,
                )
                await asyncio.sleep(retry_delay_seconds * (attempt + 1))
            else:
                logger.error("%s failed after %d attempts: %s", step_name, retries + 1, e)
    raise ValueError(f"{step_name} failed after retries: {last_error}")


def _normalize_duration_to_int(value: Any, default: int = 60) -> int:
    """Normalize duration input to int with sensible fallback."""
    try:
        d = int(value)
        return d if d > 0 else default
    except (TypeError, ValueError):
        return default


def video_to_dict(video) -> Dict:
    """Convert video object (Pydantic model or dict) to dictionary."""
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


def allocate_scene_durations(num_scenes: int, target_duration: int) -> List[int]:
    """Allocate per-scene durations using only Sora-valid values: 4, 8, 12."""
    allowed = [4, 8, 12]
    if num_scenes <= 0:
        return []

    best_combo = None
    best_diff = float("inf")

    for combo in product(allowed, repeat=num_scenes):
        total = sum(combo)
        diff = abs(total - target_duration)
        # tie-breaker: prefer 8-second pacing when equally close
        tie_score = sum(1 for x in combo if x == 8)
        if diff < best_diff:
            best_diff = diff
            best_combo = (combo, tie_score)
        elif diff == best_diff and best_combo is not None and tie_score > best_combo[1]:
            best_combo = (combo, tie_score)

    if best_combo is None:
        return [8] * num_scenes
    return list(best_combo[0])


def _validate_user_topic(topic: str) -> str:
    """Basic input validation and cleaning for story topic."""
    clean = " ".join((topic or "").split()).strip()
    if not clean:
        raise ValueError("Topic cannot be empty.")
    if len(clean) < 3:
        raise ValueError("Topic must be at least 3 characters.")
    unsafe_terms = ["hate speech", "terrorism", "sexual violence", "self-harm"]
    lower = clean.lower()
    if any(term in lower for term in unsafe_terms):
        raise ValueError("Topic contains unsafe content.")
    return clean


def _normalize_characters_locked(character_output: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Normalize character output to list[dict] for stable locking."""
    chars = character_output.get("characters", []) if isinstance(character_output, dict) else []
    if isinstance(chars, dict):
        chars = [chars]
    if not isinstance(chars, list):
        chars = []

    normalized: List[Dict[str, Any]] = []
    for idx, c in enumerate(chars):
        if not isinstance(c, dict):
            continue
        normalized.append({
            "name": str(c.get("name", f"Character {idx+1}")).strip(),
            "age": c.get("age", ""),
            "physical_description": str(c.get("physical_description", "")).strip(),
            "body_type": str(c.get("body_type", "")).strip(),
            "clothing": str(c.get("clothing", "")).strip(),
            "personality": str(c.get("personality", "")).strip(),
            "arc": str(c.get("arc", "")).strip(),
        })
    return normalized


def _character_lock_text(character_profile_locked: List[Dict[str, Any]]) -> str:
    """Create strict character lock text to inject into prompts."""
    if not character_profile_locked:
        return "No character lock."
    lines = []
    for c in character_profile_locked:
        lines.append(
            f"{c.get('name','Character')}: age {c.get('age','')}, "
            f"physical_description={c.get('physical_description','')}, "
            f"body_type={c.get('body_type','')}, "
            f"clothing={c.get('clothing','')}"
        )
    return "CHARACTER PROFILE LOCKED (MUST REUSE EXACTLY):\n" + "\n".join(lines)


def _scene_list_from_obj(obj: Any) -> List[Dict[str, Any]]:
    """Extract scene list from dict/list output."""
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        scenes = obj.get("scenes", [])
        if isinstance(scenes, list):
            return [x for x in scenes if isinstance(x, dict)]
    return []


async def generate_story_and_frames(
    selected_video,
    user_topic: str,
    max_frames: int = 10,
    creative_brief: Optional[Dict[str, Any]] = None,
    video_duration: Optional[int] = 60,
) -> Dict[str, Any]:
    """
    Generate story pipeline with 7 orchestration stages:
    1) Topic Expansion
    2) Story Blueprint
    3) Character Builder (lock)
    4) Scene Breakdown
    5) Full Narrative
    6) Frame Generator
    7) Visual Prompt Generator
    """
    if not settings.MEGALLM_API_KEY:
        raise HTTPException(status_code=500, detail="MegaLLM API key not configured")

    try:
        selected_video = video_to_dict(selected_video)
        clean_topic = _validate_user_topic(user_topic)

        tone = creative_brief.get("tone", "dynamic") if creative_brief else "dynamic"
        visual_style = creative_brief.get("visual_style", "cinematic realism") if creative_brief else "cinematic realism"
        camera_movement = creative_brief.get("camera_movement", "smooth tracking") if creative_brief else "smooth tracking"
        story_format = creative_brief.get("story_format", "narrative") if creative_brief else "narrative"
        target_audience = creative_brief.get("target_audience", "General") if creative_brief else "General"
        target_duration = _normalize_duration_to_int(
            creative_brief.get("duration_seconds", video_duration) if creative_brief else (video_duration or 60),
            default=60,
        )
        color_grading = (creative_brief.get("effects") if creative_brief else None) or "natural cinematic color grading"

        # Step 1: Topic Expansion (LLM Call #1)
        logger.info("STEP 1: Topic Expansion...")
        step1_prompt = f"""
You are a cinematic content strategist.
Input:
{{
  "topic": "{clean_topic}",
  "target_region": "US",
  "tone": "{tone}",
  "duration": {target_duration}
}}
Task:
- Expand minimal topic into richer narrative intent.
- Return JSON with keys:
  expanded_topic, core_conflict, theme, setting, emotional_arc
Return JSON only.
"""
        step1_output = await call_megallm_json_with_retry("STEP 1: Topic Expansion", step1_prompt)
        if not step1_output:
            raise ValueError("STEP 1 failed: invalid topic expansion output.")

        # Step 2: Story Blueprint (LLM Call #2)
        logger.info("STEP 2: Story Blueprint...")
        step2_prompt = f"""
You are a cinematic story architect.
Input:
{json.dumps(step1_output, ensure_ascii=True)}
Task:
- Build a strict 3-act blueprint.
- Return JSON with keys:
  act1, act2, act3, turning_point, climax, ending_tone
Return JSON only.
"""
        blueprint = await call_megallm_json_with_retry("STEP 2: Story Blueprint", step2_prompt)
        if not blueprint:
            raise ValueError("STEP 2 failed: invalid story blueprint output.")

        # Step 3: Character Builder (LLM Call #3) -> lock this output
        logger.info("STEP 3: Character Builder (lock)...")
        step3_prompt = f"""
You are a character designer for live-action cinematic stories.
Input:
- Blueprint: {json.dumps(blueprint, ensure_ascii=True)}
- Theme: {step1_output.get("theme", "")}
Task:
- Return JSON:
{{
  "characters": [
    {{
      "name": "...",
      "age": 30,
      "physical_description": "...",
      "body_type": "...",
      "clothing": "...",
      "personality": "...",
      "arc": "..."
    }}
  ]
}}
Rules:
- Physical description and clothing must be concrete and fixed.
- Live-action only.
Return JSON only.
"""
        character_output = await call_megallm_json_with_retry("STEP 3: Character Builder", step3_prompt)
        character_profile_locked = _normalize_characters_locked(character_output)
        if not character_profile_locked:
            raise ValueError("STEP 3 failed: no locked characters produced.")
        lock_text = _character_lock_text(character_profile_locked)

        # Step 4: Scene Breakdown (LLM Call #4)
        logger.info("STEP 4: Scene Breakdown...")
        step4_prompt = f"""
You are a cinematic scene planner.
Use this fixed locked character profile exactly:
{lock_text}

Input blueprint:
{json.dumps(blueprint, ensure_ascii=True)}

Task:
- Break into 6-10 scenes.
- Return JSON:
{{
  "scenes": [
    {{
      "scene_number": 1,
      "location": "...",
      "action": "...",
      "emotion": "...",
      "short_narration": "..."
    }}
  ]
}}
Rules:
- No outfit changes.
- No new physical attributes.
Return JSON only.
"""
        scene_obj = await call_megallm_json_with_retry("STEP 4: Scene Breakdown", step4_prompt)
        scene_breakdown = _scene_list_from_obj(scene_obj)
        if not scene_breakdown:
            raise ValueError("STEP 4 failed: no scenes generated.")

        # Step 5: Full Narrative (LLM Call #5)
        logger.info("STEP 5: Full Narrative...")
        step5_prompt = f"""
You are a cinematic screenplay writer.
Use this fixed locked character profile exactly:
{lock_text}

Input scenes:
{json.dumps(scene_breakdown, ensure_ascii=True)}

Task:
- Write complete emotional narrative for approximately {target_duration} seconds.
- Keep names, physical descriptions, and clothing fixed.
- Return JSON:
{{ "full_story_text": "..." }}
Return JSON only.
"""
        full_story_obj = await call_megallm_json_with_retry("STEP 5: Full Narrative", step5_prompt)
        full_story_text = str(full_story_obj.get("full_story_text", "")).strip()

        # Step 6: Frame Generator (LLM Call #6)
        logger.info("STEP 6: Frame Generator...")
        step6_prompt = f"""
You are a cinematography planner.
Use this fixed locked character profile exactly:
{lock_text}

Input scenes:
{json.dumps(scene_breakdown, ensure_ascii=True)}

Task:
- For each scene, generate shot structure JSON:
{{
  "frames": [
    {{
      "scene_number": 1,
      "shot_type": "...",
      "camera_angle": "...",
      "camera_movement": "{camera_movement}",
      "lighting_style": "...",
      "mood": "...",
      "environment_details": "..."
    }}
  ]
}}
Rules:
- No outfit changes.
- Live-action realism only.
Return JSON only.
"""
        frame_obj = await call_megallm_json_with_retry("STEP 6: Frame Generator", step6_prompt)
        frame_data = frame_obj.get("frames", []) if isinstance(frame_obj, dict) else []
        if not isinstance(frame_data, list) or not frame_data:
            raise ValueError("STEP 6 failed: no frame plan generated.")

        # Step 7: Visual Prompt Generator (LLM Call #7)
        logger.info("STEP 7: Visual Prompt Generator...")
        step7_prompt = f"""
You are a diffusion prompt engineer for live-action cinematic output.
Use this fixed locked character profile exactly:
{lock_text}

Creative configuration:
- Tone: {tone}
- Visual style: {visual_style}
- Camera movement: {camera_movement}
- Story format: {story_format}
- Target audience: {target_audience}
- Color grading: {color_grading}

Input frame_data:
{json.dumps(frame_data, ensure_ascii=True)}

Task:
- For each frame, generate diffusion-ready ultra-photorealistic visual prompt.
- Must include full locked character appearance and exact locked clothing.
- Must be live-action only, natural skin texture, depth of field.
- Lens must be 85mm or 50mm.
- Return JSON:
{{
  "scenes": [
    {{
      "scene_number": 1,
      "visual_prompt": "...",
      "audio_direction": {{
        "narration_style": "clear studio-quality",
        "voice_tone": "{tone}",
        "ambience": "minimal realistic",
        "clean_vocal_priority": true
      }}
    }}
  ]
}}
Return JSON only.
"""
        visual_obj = await call_megallm_json_with_retry("STEP 7: Visual Prompt Generator", step7_prompt)
        visual_scenes = _scene_list_from_obj(visual_obj)
        if not visual_scenes:
            raise ValueError("STEP 7 failed: no visual prompts generated.")

        # Final assembly with duration constraints and strict lock injection for every frame prompt.
        if len(visual_scenes) > max_frames:
            logger.info("Truncating generated scenes from %d to max_frames=%d", len(visual_scenes), max_frames)
            visual_scenes = visual_scenes[:max_frames]

        allowed_durations = [4, 8, 12]
        allocated = allocate_scene_durations(len(visual_scenes), target_duration)

        scene_map = {}
        for idx, s in enumerate(scene_breakdown):
            if not isinstance(s, dict):
                continue
            num = int(s.get("scene_number", idx + 1))
            scene_map[num] = s

        frame_plan_map = {}
        for idx, f in enumerate(frame_data):
            if not isinstance(f, dict):
                continue
            num = int(f.get("scene_number", idx + 1))
            frame_plan_map[num] = f

        frames: List[Dict[str, Any]] = []
        for idx, s in enumerate(visual_scenes):
            scene_num = int(s.get("scene_number", idx + 1))
            scene_src = scene_map.get(scene_num, {})
            frame_plan = frame_plan_map.get(scene_num, {})

            raw_duration = s.get("duration_seconds")
            if raw_duration not in allowed_durations:
                raw_duration = frame_plan.get("duration_seconds")
            duration = raw_duration if raw_duration in allowed_durations else allocated[idx]

            scene_description = " | ".join([
                str(scene_src.get("location", "")),
                str(scene_src.get("action", "")),
                f"Emotion: {scene_src.get('emotion', '')}",
            ]).strip(" |")
            if not scene_description:
                scene_description = f"Scene {scene_num}"

            base_prompt = str(s.get("visual_prompt", "")).strip()
            enforced_prompt = (
                f"{lock_text}\n"
                f"NON-NEGOTIABLE: Use exact same character physical traits and clothing above.\n"
                f"{base_prompt}"
            ).strip()
            # Keep prompt within downstream FrameInput schema max_length=5000.
            if len(enforced_prompt) > 5000:
                enforced_prompt = enforced_prompt[:5000]

            frames.append({
                "frame_num": scene_num,
                "duration_seconds": duration,
                "scene_description": scene_description,
                "ai_video_prompt": enforced_prompt,
                "narration_text": str(scene_src.get("short_narration", "")),
                "transition": "",
                "creative_modules": {
                    "tone": tone,
                    "visual_style": visual_style,
                    "camera_movement": camera_movement,
                    "effects": color_grading,
                    "target_audience": target_audience,
                },
                "frame_plan": frame_plan,
                "audio_direction": s.get("audio_direction", {}),
            })

        if not frames:
            raise ValueError("No frames generated after post-processing.")

        total_duration = sum(frame.get("duration_seconds", 8) for frame in frames)
        title_val = str(step1_output.get("expanded_topic", "")).strip() or selected_video.get("title") or clean_topic[:60]
        themes_val = step1_output.get("theme", [])
        if isinstance(themes_val, str):
            themes_val = [themes_val]
        if not isinstance(themes_val, list):
            themes_val = []
        hook_val = str(blueprint.get("act1", "")).strip()[:240]
        emotional_tone = str(blueprint.get("ending_tone", tone))
        characters_for_response = [
            f"{c.get('name')}, {c.get('physical_description')}, clothing: {c.get('clothing')}"
            for c in character_profile_locked
        ]

        return {
            "enhanced_topic": step1_output.get("expanded_topic", clean_topic),
            "title": title_val,
            "full_story": full_story_text,
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
                "target_duration": f"{target_duration} seconds",
                "character_based": len(character_profile_locked) > 0,
                "locked_character_profile": character_profile_locked,
                "source_video": {
                    "title": selected_video.get("title", ""),
                    "views": selected_video.get("views", 0),
                    "ai_confidence": selected_video.get("ai_confidence", 0)
                },
                "ai_model": settings.MEGALLM_MODEL
            }
        }

    except Exception as e:
        logger.error("MegaLLM generation error: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate story and frames: {str(e)}"
        )
