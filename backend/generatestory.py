import os
from dotenv import load_dotenv
import google.generativeai as genai
from fastapi import HTTPException
from typing import List, Dict, Any
import json
import re

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def extract_json_from_text(text: str) -> List[Dict]:
    """Extract JSON array from Gemini response text."""
    try:
        # First try to parse the entire text as JSON
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try to extract the outermost JSON array by finding the first [ and last ]
    try:
        start = text.find('[')
        end = text.rfind(']') + 1
        if start != -1 and end > start:
            json_str = text[start:end]
            # Clean up common formatting issues
            json_str = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas
            json_str = re.sub(r',\s*]', ']', json_str)
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # If still no luck, try to find JSON between code blocks or other markers
    try:
        # Look for ```json ... ``` blocks
        code_block_match = re.search(r'```(?:json)?\s*(\[[\s\S]*\])\s*```', text, re.IGNORECASE)
        if code_block_match:
            return json.loads(code_block_match.group(1))
    except json.JSONDecodeError:
        pass

    return []

def enhance_user_topic(selected_video: Dict, user_topic: str, model) -> str:
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
    
    response = model.generate_content(enhancement_prompt)
    return response.text.strip()

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
    max_frames: int = 5
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
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")

    try:
        # Convert selected_video to a dictionary to ensure it's subscriptable
        selected_video = video_to_dict(selected_video)
        
        model = genai.GenerativeModel("gemini-2.5-flash")  # Updated to the new model
        
        # Step 1: Enhance the user's topic
        print("Step 1: Enhancing user topic...")
        enhanced_topic = enhance_user_topic(selected_video, user_topic, model)
        
        # Step 2: Generate full story with character consistency
        print("Step 2: Generating full story...")
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
        
        Generate a COMPLETE SHORT-FORM story (30-60 seconds when narrated) with these requirements:
        
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
        
        story_response = model.generate_content(story_prompt)
        full_story_text = story_response.text.strip()
        
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
        print("Step 3: Generating video frames...")
        
        frames_prompt = f"""
        You are a professional AI video generation prompt engineer. Create a shot-by-shot storyboard for AI video tools (RunwayML, Pika, Sora, etc.).

        FULL STORY TO ADAPT:
        {story_data["story"]}

        {character_instruction}

        VISUAL STYLE: {story_data["visual_style"]}
        EMOTIONAL TONE: {story_data["emotional_tone"]}
        THEMES: {', '.join(story_data["themes"])}

        Remember: Output ONLY the exact JSON array as specified. Do not add any extra text.

        ANALYZE THE STORY and determine the OPTIMAL number of frames needed:
        - Simple stories: 4-5 frames
        - Complex stories with multiple scenes/characters: 6-8 frames
        - Very detailed stories: up to 10 frames maximum
        - Each frame should represent a distinct visual moment or scene change
        - Total duration should be 30-60 seconds when played

        FRAME REQUIREMENTS:
        1. Each frame: 5-8 seconds of video content
        2. Sequential storytelling: Frame 1 → Frame N covers complete narrative
        3. Character consistency: SAME characters throughout (if applicable)
        4. Optimal frame count based on story complexity and pacing

        PROMPT ENGINEERING RULES FOR EACH FRAME:
        - Start with: "A [duration] shot of..."
        - Include: Camera angle (close-up, wide shot, over-shoulder, aerial, etc.)
        - Include: Lighting (golden hour, dramatic shadows, bright studio, moody, etc.)
        - Include: Movement (camera pans left, zooms in, static shot, tracking shot, etc.)
        - Include: Character details (if applicable): exact clothing, hairstyle, facial expression, body language
        - Include: Environment: detailed setting description
        - Include: Action: what's happening in this exact moment
        - Include: Emotion: how it should feel (tense, joyful, mysterious, etc.)
        - Include: Style keywords: cinematic, 4K, photorealistic, animated, etc.
        - Length: 150-250 words per prompt (detailed enough for AI video gen)

        OUTPUT FORMAT (JSON):
        Return a valid JSON array with the optimal number of frames for this story:

        [
          {{
            "frame_num": 1,
            "duration_seconds": 8,
            "scene_description": "One-sentence summary of what happens in this frame",
            "ai_video_prompt": "Detailed 150-250 word prompt for AI video generation. Start with 'A 6-second shot of...' and include all visual details: camera angle, lighting, character appearance (if applicable), environment, action, emotion, style keywords, movement, colors, atmosphere. Be extremely specific and descriptive.",
            "narration_text": "Optional: What the narrator/character says during this frame (if applicable)",
            "transition": "How this frame transitions to next: cut, fade, zoom, etc."
          }},
          {{
            "frame_num": 2,
            ...
          }},
          ... (continue for optimal number of frames based on story)
        ]

        IMPORTANT:
        - Return ONLY valid JSON, no extra text
        - Choose the RIGHT number of frames for this specific story (4-10 frames)
        - Ensure character consistency if characters exist
        - Each prompt must be detailed enough for AI video generation
        - Cover the complete story arc from hook to ending

        Generate the frames now:
        """
        
        frames_response = model.generate_content(frames_prompt)
        frames_text = frames_response.text.strip()
        
        # Add debugging: Print the raw response
        print(f"Raw frames response: {frames_text[:500]}...")  
        
        frames = extract_json_from_text(frames_text)
        
        print(f"Extracted frames: {frames[:2]}...")  # Debug the extracted frames
        
        if not frames or len(frames) < 4:
            print(f"Debug: Frames response length is {len(frames)}. Full response: {frames_text}")
            raise ValueError(f"Generated only {len(frames)} frames, expected at least 4. Check the AI response for issues.")

        # No longer enforce max_frames - let AI determine optimal count
        # frames = frames[:max_frames]
        
        # Calculate estimated duration
        total_duration = sum(frame.get('duration_seconds', 6) for frame in frames)
        
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
            "metadata": {
                "total_frames": len(frames),
                "estimated_duration": total_duration,
                "target_duration": "30-60 seconds",
                "character_based": len(story_data["characters"]) > 0,
                "source_video": {
                    "title": selected_video['title'],
                    "views": selected_video['views'],
                    "ai_confidence": selected_video.get('ai_confidence', 0)
                }
            }
        }
        
    except Exception as e:
        print(f"Gemini generation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate story and frames: {str(e)}"
        )


