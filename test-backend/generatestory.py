# generatestory.py
import os
from dotenv import load_dotenv
import google.generativeai as genai
from fastapi import HTTPException
from typing import List, Tuple, Dict, Any

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

async def generate_story_and_frames(selected_video: Dict, user_topic: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Two-step generation:
    1. Generate full story with consistent characters, based on selected video + user topic.
    2. Split story into 6-9 frames, enforcing same characters, with detailed prompts for AI video gen.
    Returns (full_story: str, frames: List[{"frame_num": int, "prompt": str, "description": str}])
    """
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        # Step 1: Generate full story with consistent characters
        story_prompt = f"""
        You are a creative YouTube Shorts script writer specializing in engaging, viral content.
        Base the story on this trending video: Title: "{selected_video['title']}", Description: "{selected_video['description'][:200]}...", Hashtags: {selected_video['tags']}.
        User topic: "{user_topic}".

        Generate a COMPLETE, detailed story for a 30-60 second YouTube Short. Ensure:
        - CONSISTENT CHARACTERS: Introduce 2-4 main characters (e.g., a protagonist, sidekick) that appear throughout. Describe their appearances, personalities, and roles clearly at the start.
        - Engaging narrative: Start with a hook, build tension or fun, end with a twist or call-to-action.
        - Suitable for Shorts: Fast-paced, visual, emotional, and shareable.
        - Length: 200-400 words, narrative style.

        Output format:
        - Title: [Catchy title]
        - Characters: [List 2-4 characters with brief descriptions]
        - Story: [Full narrative in paragraphs]
        - Hook: [1-2 sentence opening]
        - Ending: [Closing line for engagement]
        """

        story_response = model.generate_content(story_prompt)
        full_story = story_response.text.strip()

        # Step 2: Split story into 6-9 frames, enforcing same characters
        frames_prompt = f"""
        You are an AI video storyboard expert. Take this full story and split it into EXACTLY 6-9 sequential frames for a YouTube Short video.

        Full Story:
        {full_story}

        Rules:
        - STRICTLY USE THE SAME CHARACTERS from the story (no new ones). Reference them consistently.
        - Each frame: 3-7 seconds, advancing the plot visually.
        - Frame prompts must be DETAILED for AI video generation (e.g., RunwayML, Sora): Include scene description, character actions/emotions, camera angles (e.g., close-up, wide shot), lighting (e.g., bright, dramatic), themes (e.g., motivational, humorous), scenarios (e.g., gym workout, kitchen mishap), colors, style (e.g., realistic, animated), and transitions.
        - Ensure continuity: Characters look/act the same across frames.
        - Total: 6-9 frames covering the entire story (hook to ending).
        - Keep viral Shorts vibe: Dynamic, eye-catching visuals.

        Output format (JSON-like for parsing):
        [
          {{
            "frame_num": 1,
            "description": "Brief 1-sentence summary of this frame's action.",
            "prompt": "Detailed AI video prompt: [Full visual description, 100-200 words]."
          }},
          ... (6-9 frames)
        ]
        """

        frames_response = model.generate_content(frames_prompt)
        frames_text = frames_response.text.strip()

        # Simple parsing: Assume Gemini outputs clean list; in production, use regex/JSON parser for robustness
        # For now, extract frames from the response (Gemini often follows format well)
        frames = []
        lines = frames_text.split('\n')
        current_frame = {}
        frame_num = 1
        for line in lines:
            line = line.strip()
            if line.startswith('"frame_num":'):
                if current_frame:
                    frames.append(current_frame)
                current_frame = {"frame_num": frame_num}
                frame_num += 1
            elif line.startswith('"description":'):
                current_frame["description"] = line.split(':', 1)[1].strip().strip('"')
            elif line.startswith('"prompt":'):
                current_frame["prompt"] = line.split(':', 1)[1].strip().strip('"')
        
        if current_frame:
            frames.append(current_frame)

        # Ensure 6-9 frames; if not, fallback or regenerate (simplified here)
        if len(frames) < 6:
            # Quick fallback: Pad or adjust, but for demo, just use as-is
            pass
        elif len(frames) > 9:
            frames = frames[:9]

        return full_story, frames

    except Exception as e:
        print(f"Gemini generation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate story and frames")