# generatestory.py
import os
from dotenv import load_dotenv
import google.generativeai as genai
from fastapi import HTTPException

# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

async def generate_story(topic: str) -> str:
    """
    Generate a detailed YouTube Shorts story prompt based on the given topic.
    """
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API key not configured")

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
        You are a creative YouTube Shorts script writer. 
        Generate a detailed story idea for a short video on the topic: "{topic}".

        The response should include:
        1. A catchy title
        2. A short engaging hook (2-3 lines)
        3. The main story flow (3-5 short bullet points)
        4. A closing line that leaves curiosity or encourages engagement.

        Keep it fun, engaging, and suitable for a viral YouTube Shorts style.
        """

        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini story generation error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate story")
