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

from app.core.config import settings
from app.core_yt.llm_client import get_megallm_client

logger = logging.getLogger(__name__)


def extract_json_from_text(text: str) -> List[Dict]:
    """Extract JSON array from AI response text."""
    logger.debug("Attempting to extract JSON from text of length: %d", len(text))
    
    # First try to parse the entire text as JSON
    try:
        result = json.loads(text.strip())
        logger.debug("Successfully parsed entire text as JSON")
        return result
    except json.JSONDecodeError as e:
        logger.debug("Could not parse entire text: %s", e)
    
    # Try to find JSON between code blocks first (common AI response format)
    try:
        # Look for ```json ... ``` blocks
        code_block_match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', text, re.IGNORECASE)
        if code_block_match:
            json_str = code_block_match.group(1)
            logger.debug("Found JSON in code block, length: %d", len(json_str))
            result = json.loads(json_str)
            logger.debug("Successfully parsed code block JSON, got %d items", len(result))
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
            json_str = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas before }
            json_str = re.sub(r',\s*]', ']', json_str)  # Remove trailing commas before ]
            json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)  # Remove control characters
            
            result = json.loads(json_str)
            logger.debug("Successfully parsed extracted JSON, got %d items", len(result))
            return result
    except json.JSONDecodeError as e:
        logger.debug("Could not parse extracted JSON array: %s", e)
        # Log the problematic part
        if start != -1 and end > start:
            problem_area = text[max(0, e.pos - 50):e.pos + 50] if hasattr(e, 'pos') else "N/A"
            logger.debug("Problem area: ...%s...", problem_area)
    
    logger.warning("All JSON extraction methods failed. First 500 chars: %s", text[:500])
    return []


def _call_megallm_sync(prompt: str, json_mode: bool = False) -> str:
    """Synchronous MegaLLM call (internal — use call_megallm() instead)."""
    client = get_megallm_client()
    if not client:
        raise HTTPException(status_code=500, detail="MegaLLM API key not configured")
    
    messages = []
    
    # Add system message for JSON mode
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
        max_tokens=8192  # Increased for longer JSON responses
    )
    
    # Check if the response has content
    if not response.choices or not response.choices[0].message.content:
        logger.error("MegaLLM returned empty response. Response: %s", response)
        raise HTTPException(status_code=500, detail="MegaLLM API returned empty response")
    
    result = response.choices[0].message.content.strip()
    logger.debug("MegaLLM response length: %d chars", len(result))
    return result


async def call_megallm(prompt: str, json_mode: bool = False) -> str:
    """Call MegaLLM API without blocking the event loop.
    Runs the synchronous OpenAI SDK call in a thread executor.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _call_megallm_sync, prompt, json_mode)


async def enhance_user_topic(selected_video: Dict, user_topic: str) -> str:
    """
    Enhance user's topic by analyzing trending video patterns and adding viral elements.
    """
    enhancement_prompt = f"""
    You are a YouTube Shorts content strategist. Analyze this trending video and enhance the user's topic idea.
    
    TRENDING VIDEO ANALYSIS:
    - Title: "{selected_video['title']}"
    - Views: {selected_video['views']}
    - Likes: {selected_video['likes']}
    - Description: "{selected_video.get('description', '')[:300]}"
    - Hashtags: {', '.join(selected_video.get('tags', [])[:5])}
    - AI Confidence: {selected_video.get('ai_confidence', 'N/A')}%
    
    USER'S TOPIC: "{user_topic}"
    
    Task: Enhance this topic by:
    1. Identifying what made the trending video viral (hook, emotion, visual style)
    2. Incorporating those viral elements into the user's topic
    3. Adding specific themes, emotions, and visual directions
    4. Making it SHORT-FORM optimized (30-60 seconds max)
    
    Output a comprehensive enhanced topic description (100-150 words) that includes:
    - Main theme/story angle
    - Emotional tone (motivational, funny, shocking, heartwarming, etc.)
    - Visual style (cinematic, animated, documentary-style, fast-paced, etc.)
    - Key hook/twist
    - Target audience appeal
    
    Enhanced Topic:
    """
    
    return await call_megallm(enhancement_prompt)


def video_to_dict(video) -> Dict:
    """Convert video object (Pydantic model or dict) to dictionary."""
    if isinstance(video, dict):
        return video
    # Handle Pydantic model or object with attributes
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


async def generate_story_and_frames(
    selected_video,
    user_topic: str,
    max_frames: int = 5,
    creative_brief: Optional[Dict[str, Any]] = None,
    video_duration: Optional[int] = 60,
) -> Dict[str, Any]:
    """
    Generate a complete YouTube Shorts story with consistent characters and detailed frame prompts.
    
    Args:
        selected_video: The selected trending video data
        user_topic: User's input topic
        max_frames: Maximum number of frames (default 7 for optimal 30-60s video)
    
    Returns:
        Dictionary containing:
        - enhanced_topic: The enhanced version of user's topic
        - full_story: Complete narrative
        - characters: List of character descriptions (if applicable)
        - frames: List of frame objects with detailed prompts
        - metadata: Additional info (duration estimate, style, etc.)
    """
    if not settings.MEGALLM_API_KEY:
        raise HTTPException(status_code=500, detail="MegaLLM API key not configured")

    try:
        # Convert selected_video to a dictionary to ensure it's subscriptable
        selected_video = video_to_dict(selected_video)
        
        # Step 1: Enhance the user's topic
        logger.info("Step 1: Enhancing user topic...")
        enhanced_topic = await enhance_user_topic(selected_video, user_topic)
        
        # Step 2: Generate story with creative brief integration
        logger.info("Step 2: Generating story with creative modules...")
        # Extract creative modules
        tone = creative_brief.get("tone", "dynamic") if creative_brief else "dynamic"
        visual_style = creative_brief.get("visual_style", "cinematic") if creative_brief else "cinematic"
        target_audience = creative_brief.get("target_audience", "General") if creative_brief else "General"
        story_format = creative_brief.get("story_format", "narrative") if creative_brief else "narrative"
        target_duration = creative_brief.get("duration_seconds", video_duration) if creative_brief else (video_duration or 60)

        story_prompt = f"""
        You are an expert YouTube Shorts scriptwriter specializing in VIRAL, AI-GENERATED video content.
        
        CONTEXT FROM TRENDING VIDEO:
        - Title: "{selected_video['title']}"
        - Description: "{selected_video.get('description', '')[:200]}"
        - What's working: {selected_video['views']} views, {selected_video['likes']} likes
        - Tags: {', '.join(selected_video.get('tags', [])[:5])}
        
        ENHANCED TOPIC TO CREATE:
        {enhanced_topic}
        
        ORIGINAL USER TOPIC: "{user_topic}"

        CREATIVE MODULES:
        - Tone: {tone}
        - Visual Style: {visual_style}
        - Target Audience: {target_audience}
        - Story Format: {story_format}
        - Duration: {target_duration} seconds
        
        Generate a COMPLETE SHORT-FORM story (target {target_duration} seconds when narrated) with these requirements:
        
        1. CHARACTER CONSISTENCY (CRITICAL):
           - If story needs characters, introduce 1-3 main characters MAX
           - Provide DETAILED physical descriptions: age, gender, clothing, hair, distinctive features
           - Keep characters SIMPLE and RECOGNIZABLE for AI video generation
           - Characters must be CONSISTENT across entire story
           - If no characters needed (e.g., nature documentary), focus on visual continuity
        
        2. STORY STRUCTURE:
           - Hook (0-3s): Grab attention immediately
           - Build-up (3-20s): Develop tension/interest
           - Climax (20-40s): Peak moment
           - Resolution (40-50s): Payoff/twist
           - CTA (50-60s): Call to action or memorable ending
        
        3. VISUAL-FIRST WRITING:
           - Every sentence should be visually descriptive
           - Focus on actions, not just dialogue
           - Include emotions through facial expressions and body language
        
        4. SHORT-FORM OPTIMIZATION:
           - Fast-paced, no filler
           - Maximum 200-250 words
           - Every second counts
        
        5. VIRAL ELEMENTS:
           - Emotional impact (surprise, joy, inspiration, shock)
           - Relatable or aspirational content
           - Shareable moment or quotable line
        
        OUTPUT FORMAT (use exact headers):
        
        ### TITLE
        [Catchy, clickable title under 60 characters]
        
        ### CHARACTERS
        [If applicable, list 1-3 characters with detailed descriptions. If no characters, write "No specific characters - focus on [subject/theme]"]
        
        Character 1: [Name], [age range], [gender], [physical appearance: hair, clothing, build], [key trait]
        Character 2: [Name], [age range], [gender], [physical appearance], [key trait]
        
        ### STORY
        [Write the complete narrative in 200-250 words. Use present tense. Be visually descriptive.]
        
        ### HOOK
        [The exact opening line/visual that grabs attention in first 3 seconds]
        
        ### THEMES
        [List 3-4 themes: e.g., motivation, humor, transformation, discovery]
        
        ### VISUAL STYLE
        [Describe the overall aesthetic: e.g., cinematic realism, animated cartoon, documentary style, surreal, dramatic lighting, bright and colorful, etc.]
        
        ### EMOTIONAL TONE
        [Primary emotion: motivational, humorous, heartwarming, shocking, inspirational, mysterious, etc.]
        
        Generate the story now:
        """
        
        full_story_text = await call_megallm(story_prompt)
        
        # Parse story components
        story_data = {
            "title": "",
            "characters": [],
            "story": "",
            "hook": "",
            "themes": [],
            "visual_style": "",
            "emotional_tone": ""
        }
        
        # Extract sections using regex
        title_match = re.search(r'###\s*TITLE\s*\n(.*?)(?=\n###|\Z)', full_story_text, re.DOTALL | re.IGNORECASE)
        if title_match:
            story_data["title"] = title_match.group(1).strip()
        
        characters_match = re.search(r'###\s*CHARACTERS\s*\n(.*?)(?=\n###|\Z)', full_story_text, re.DOTALL | re.IGNORECASE)
        if characters_match:
            char_text = characters_match.group(1).strip()
            if "no specific characters" not in char_text.lower():
                char_lines = [line.strip() for line in char_text.split('\n') if line.strip() and not line.strip().startswith('#')]
                story_data["characters"] = char_lines
        
        story_match = re.search(r'###\s*STORY\s*\n(.*?)(?=\n###|\Z)', full_story_text, re.DOTALL | re.IGNORECASE)
        if story_match:
            story_data["story"] = story_match.group(1).strip()
        
        hook_match = re.search(r'###\s*HOOK\s*\n(.*?)(?=\n###|\Z)', full_story_text, re.DOTALL | re.IGNORECASE)
        if hook_match:
            story_data["hook"] = hook_match.group(1).strip()
        
        themes_match = re.search(r'###\s*THEMES\s*\n(.*?)(?=\n###|\Z)', full_story_text, re.DOTALL | re.IGNORECASE)
        if themes_match:
            story_data["themes"] = [t.strip() for t in themes_match.group(1).strip().split(',')]
        
        visual_match = re.search(r'###\s*VISUAL\s*STYLE\s*\n(.*?)(?=\n###|\Z)', full_story_text, re.DOTALL | re.IGNORECASE)
        if visual_match:
            story_data["visual_style"] = visual_match.group(1).strip()
        
        tone_match = re.search(r'###\s*EMOTIONAL\s*TONE\s*\n(.*?)(?=\n###|\Z)', full_story_text, re.DOTALL | re.IGNORECASE)
        if tone_match:
            story_data["emotional_tone"] = tone_match.group(1).strip()
        
        # Build character consistency instruction
        character_instruction = ""
        if story_data["characters"]:
            character_instruction = f"""
            CRITICAL CHARACTER CONSISTENCY:
            These are the ONLY characters in this story. They MUST appear exactly as described in ALL relevant frames:
            {chr(10).join(story_data["characters"])}
            
            - DO NOT change their appearance, clothing, or features
            - DO NOT introduce new characters
            - Reference them by name and maintain visual consistency
            - If a character isn't in a frame, explicitly state "Character not in this frame"
            """
        else:
            character_instruction = "No specific characters. Focus on visual subject consistency (e.g., same location, object, animal)."
        
        # Step 3: Generate frames with strict character consistency
        logger.info("Step 3: Generating video frames...")
        
        # Prepare creative modules for prompt
        tone_val = creative_brief.get("tone") if creative_brief else story_data.get("emotional_tone", "dynamic")
        visual_style_val = creative_brief.get("visual_style") if creative_brief else story_data.get("visual_style", "cinematic realism")
        camera_movement_val = creative_brief.get("camera_movement") if creative_brief else "dynamic tracking"
        effects_val = creative_brief.get("effects") if creative_brief else "subtle transitions"
        target_audience_val = creative_brief.get("target_audience") if creative_brief else "General"
        
        frames_prompt = f"""
        You are a professional AI video generation prompt engineer. Create a shot-by-shot storyboard for AI video tools (RunwayML, Pika, Sora, etc.).

        FULL STORY TO ADAPT:
        {story_data["story"]}

        {character_instruction}

        CREATIVE MODULES (MUST be included in EVERY frame's ai_video_prompt):
        - TONE: {tone_val}
        - VISUAL STYLE: {visual_style_val}
        - CAMERA MOVEMENT: {camera_movement_val}
        - EFFECTS: {effects_val}
        - TARGET AUDIENCE: {target_audience_val}
        - THEMES: {', '.join(story_data.get("themes", []))}
        - TARGET DURATION: {creative_brief.get("duration_seconds") if creative_brief else target_duration} seconds

        Remember: Output ONLY the exact JSON array as specified. Do not add any extra text.

        ANALYZE THE STORY and determine the OPTIMAL number of frames needed based on TARGET DURATION:
        - Simple stories (20-40s): 3-5 frames
        - Medium stories (40-80s): 5-8 frames
        - Complex stories (80-120s): 8-12 frames
        - Each frame should represent a distinct visual moment or scene change
        - Total duration MUST match TARGET DURATION exactly ({creative_brief.get("duration_seconds") if creative_brief else target_duration} seconds)

        CRITICAL FRAME DURATION LIMIT (SORA 2 API CONSTRAINT):
        - duration_seconds MUST be EXACTLY one of: 4, 8, or 12 (NO other values allowed!)
        - These are the ONLY values the Sora 2 API accepts: 4, 8, 12
        - Use 4s for quick shots, 8s for standard scenes, 12s for key moments
        - For a 60s video: e.g. 5 frames × 12s, or 4 frames × 12s + 1 frame × 8s + 1 frame × 4s
        - For a 120s video: e.g. 10 frames × 12s, or mix of 8s and 12s frames
        
        FRAME REQUIREMENTS:
        1. Each frame: EXACTLY 4, 8, or 12 seconds (these are the ONLY allowed values!)
        2. Sequential storytelling: Frame 1 → Frame N covers complete narrative
        3. Character consistency: SAME characters throughout (if applicable)
        4. Optimal frame count based on story complexity and pacing

        PROMPT ENGINEERING RULES FOR EACH FRAME (CRITICAL FOR CONSISTENCY & CREATIVITY):
        
        CONSISTENCY REQUIREMENTS:
        - Maintain EXACT visual continuity between frames (same characters, same settings, same style)
        - Use consistent color palette and lighting mood throughout
        - Ensure smooth visual flow from frame to frame
        - Reference previous frames to maintain continuity
        
        CREATIVITY REQUIREMENTS:
        - Create visually stunning, eye-catching scenes that captivate viewers
        - Use dynamic compositions with strong visual hierarchy
        - Incorporate interesting perspectives and unique camera angles
        - Add visual interest through contrast, depth, and movement
        
        PERFECT SCENE REQUIREMENTS:
        - Start with: "A [duration]-second [shot type] of..."
        - Specify EXACT camera angle (close-up, medium shot, wide shot, over-shoulder, aerial, dutch angle, etc.)
        - Define PRECISE lighting (golden hour, dramatic shadows, bright studio, moody, high-key, low-key, rim lighting, etc.)
        - Describe camera movement (smooth tracking, handheld, push-in, pull-out, pan, tilt, dolly, crane, etc.)
        - Detail character appearance EXACTLY (if applicable): clothing, hairstyle, facial expression, body language, posture
        - Describe environment COMPLETELY: location, time of day, weather, props, background details
        - Specify action CLEARLY: what's happening, movement, gestures, interactions
        - Convey emotion EFFECTIVELY: mood, atmosphere, feeling (tense, joyful, mysterious, inspiring, etc.)
        - Include style keywords: cinematic, 4K UHD, photorealistic, professional cinematography, color graded, etc.
        - Add creative elements: depth of field, bokeh, lens flares, color grading, visual effects
        
        TECHNICAL SPECIFICATIONS:
        - Frame rate: 24fps or 30fps
        - Aspect ratio: 9:16 (vertical for Shorts)
        - Resolution: 1080p minimum
        - Length: 200-300 words per prompt (extremely detailed for perfect AI video generation)
        - Must be production-ready for professional video generation tools

        OUTPUT FORMAT (JSON):
        Return a valid JSON array with the optimal number of frames for this story.
        Each frame MUST be a complete JSON object with ALL required fields in JSON format:

        [
          {{
            "frame_num": 1,
            "duration_seconds": 8,  // MUST be exactly 4, 8, or 12
            "scene_description": "One-sentence summary of what happens in this frame",
            "ai_video_prompt": "Highly detailed 200-300 word production-ready prompt for professional AI video generation. Start with 'A [duration]-second [shot type] of...' and MUST seamlessly integrate ALL creative modules: camera movement ({camera_movement_val}), visual style ({visual_style_val}), effects ({effects_val}), tone ({tone_val}). Create a visually stunning, consistent scene with: EXACT camera angle and movement, PRECISE lighting setup, DETAILED character appearance (if applicable) maintaining consistency, COMPLETE environment description, CLEAR action and movement, STRONG emotional impact, PROFESSIONAL cinematography style, CREATIVE visual elements. Ensure perfect scene composition, visual continuity, and maximum creative appeal. Be extremely specific about every visual element to ensure consistency and perfection.",
            "narration_text": "Optional: What the narrator/character says during this frame (if applicable)",
            "transition": "How this frame transitions to next: cut, fade, zoom, etc.",
            "creative_modules": {{
              "tone": "{tone_val}",
              "visual_style": "{visual_style_val}",
              "camera_movement": "{camera_movement_val}",
              "effects": "{effects_val}",
              "target_audience": "{target_audience_val}"
            }}
          }},
          {{
            "frame_num": 2,
            ...
          }},
          ... (continue for optimal number of frames based on story - DO NOT hardcode frame count)
        ]

        IMPORTANT:
        - Return ONLY valid JSON array, no extra text before or after
        - DYNAMICALLY determine the optimal number of frames based on story complexity (NOT hardcoded)
        - CRITICAL: duration_seconds MUST be EXACTLY 4, 8, or 12 (NO other values are valid!)
        - Each frame MUST include creative_modules as a JSON object within the frame JSON
        - Each ai_video_prompt MUST incorporate ALL creative modules (tone, visual_style, camera_movement, effects)
        - Ensure character consistency if characters exist
        - Each prompt must be detailed enough for AI video generation
        - Cover the complete story arc from hook to ending
        - Frame numbers should be sequential (1, 2, 3, ...) based on actual story division

        Generate the frames now as a valid JSON array:
        """
        
        frames_text = await call_megallm(frames_prompt, json_mode=True)
        
        # Add debugging: Log the raw response
        logger.debug("Raw frames response: %s...", frames_text[:500])
        
        frames = extract_json_from_text(frames_text)
        
        logger.debug("Extracted frames: %s...", frames[:2] if frames else 'None')
        
        if not frames or len(frames) < 1:
            logger.error("Frames response length is %d. Full response: %s", len(frames) if frames else 0, frames_text)
            raise ValueError(f"Generated {len(frames) if frames else 0} frames, expected at least 1. Check the AI response for issues.")

        # Truncate to max_frames if necessary (M-7)
        if len(frames) > max_frames:
            logger.info("Truncating frames from %d to max_frames=%d", len(frames), max_frames)
            frames = frames[:max_frames]

        # Post-process: Snap duration to Sora 2 allowed values (4, 8, 12)
        ALLOWED_DURATIONS = [4, 8, 12]
        for frame in frames:
            duration = frame.get('duration_seconds', 8)
            if duration not in ALLOWED_DURATIONS:
                # Snap to nearest allowed value
                snapped = min(ALLOWED_DURATIONS, key=lambda x: abs(x - duration))
                logger.warning("Frame %s had duration %ds, snapped to %ds (Sora allows only 4, 8, 12)", frame.get('frame_num'), duration, snapped)
                frame['duration_seconds'] = snapped

        # Calculate estimated duration
        total_duration = sum(frame.get('duration_seconds', 10) for frame in frames)
        
        # Return complete package
        return {
            "enhanced_topic": enhanced_topic,
            "title": story_data["title"],
            "full_story": story_data["story"],
            "hook": story_data["hook"],
            "characters": story_data["characters"],
            "themes": story_data["themes"],
            "visual_style": story_data["visual_style"],
            "emotional_tone": story_data["emotional_tone"],
            "frames": frames,
            "creative_brief": creative_brief,
            "metadata": {
                "total_frames": len(frames),
                "estimated_duration": total_duration,
                "target_duration": f"{target_duration or 60} seconds",
                "character_based": len(story_data["characters"]) > 0,
                "source_video": {
                    "title": selected_video['title'],
                    "views": selected_video['views'],
                    "ai_confidence": selected_video.get('ai_confidence', 0)
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
