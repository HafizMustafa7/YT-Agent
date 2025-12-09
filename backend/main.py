"""
Main FastAPI Application - Clean structure with component-based architecture
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Literal

# Component imports
from app.core.trend_fetcher import fetch_trends
from app.core.topic_validator import validate_topic, normalize_topic
from app.core.creative_builder import build_creative_brief
from generatestory import generate_story_and_frames

app = FastAPI(title="YouTube Trend Analyzer API")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Pydantic Models ====================

class TrendRequest(BaseModel):
    mode: Literal["search_trends", "analyze_niche"]
    niche: Optional[str] = None

class TopicValidationRequest(BaseModel):
    topic: str
    niche_hint: Optional[str] = None

class CreativePreferencesRequest(BaseModel):
    tone: str
    target_audience: str
    visual_style: str
    camera_movement: str
    effects: str
    story_format: str
    duration_seconds: int
    constraints: List[str] = []

class GenerateStoryRequest(BaseModel):
    topic: str
    selected_video: Dict[str, Any]
    creative_preferences: CreativePreferencesRequest

# ==================== API Endpoints ====================

@app.get("/")
async def root():
    return {"message": "YouTube Trend Analyzer API is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/api/fetch-trends")
async def api_fetch_trends(request: TrendRequest):
    """Fetch trending videos based on mode (search_trends or analyze_niche)"""
    try:
        result = fetch_trends(
            mode=request.mode,
            niche=request.niche,
            limit=20
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching trends: {str(e)}")

@app.post("/api/validate-topic")
async def api_validate_topic(request: TopicValidationRequest):
    """Validate a topic - checks policy compliance and basic quality"""
    try:
        result = validate_topic(request.topic, request.niche_hint)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validating topic: {str(e)}")

@app.post("/api/generate-story")
async def api_generate_story(request: GenerateStoryRequest):
    """Generate story and frames with creative brief"""
    try:
        # Build creative brief
        creative_brief = build_creative_brief(request.creative_preferences.model_dump())
        
        # Generate story with creative brief
        story_result = await generate_story_and_frames(
            selected_video=request.selected_video,
            user_topic=request.topic,
            creative_brief=creative_brief,
            video_duration=creative_brief.get("duration_seconds", 60),
        )
        
        return {
            "success": True,
            "story": story_result,
            "creative_brief": creative_brief,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating story: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
