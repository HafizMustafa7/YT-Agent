# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import random
from datetime import datetime, timedelta
import re  # For hashtag extraction

# Local imports
from fetchtrend import get_trending_shorts
from generatestory import generate_story_and_frames

app = FastAPI(title="YouTube Trend Analyzer API")

# ------------------ CORS Middleware ------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ Pydantic Models ------------------
class VideoTrend(BaseModel):
    id: str
    title: str
    description: str = ""
    tags: List[str] = []
    views: int
    likes: int = 0
    comments: int = 0
    thumbnail: str
    duration: str
    channel: str
    ai_confidence: Optional[int] = 0
    url: Optional[str] = ""

class NicheRequest(BaseModel):
    niche: str

class TrendAnalysisResponse(BaseModel):
    niche: str
    trends: List[VideoTrend]
    averageViews: int
    averageLikes: Optional[int] = 0
    total_trends: int

# Old request model (still valid for backward compatibility)
class StoryGenerationRequest(BaseModel):
    selected_video: VideoTrend
    user_topic: str

class StoryAndFramesResponse(BaseModel):
    user_topic: str
    selected_video_title: str
    story: str
    frames: List[Dict[str, Any]]

# New request models
class GenerateStoryRequest(BaseModel):
    selected_video: Dict[str, Any]
    user_topic: str
    max_frames: Optional[int] = 7

class GenerateStoryRequestWithModel(BaseModel):
    selected_video: VideoTrend
    user_topic: str
    max_frames: Optional[int] = 7


# ------------------ Helpers ------------------
def generate_fallback_trends(niche: str, count: int = 8) -> List[VideoTrend]:
    """Generate fallback trends mimicking real structure if API fails."""
    base_tags = [niche.lower(), "trending", "viral", "shorts"]
    fallback_trends = []
    for i in range(count):
        title = random.choice([
            f"Top {niche} Tips for Beginners",
            f"Common {niche} Mistakes to Avoid",
            f"{niche} Trends You Need to Know",
            f"Quick {niche} Tutorial",
            f"Best {niche} Hacks",
        ])
        desc = f"Discover amazing {niche} content that's trending. Perfect for YouTube Shorts."
        tags = base_tags + [f"tip{i}", f"hack{i}"]
        views = random.randint(10000, 500000)
        likes = random.randint(1000, 50000)
        fallback_trends.append(VideoTrend(
            id=f"fallback_{i}",
            title=title,
            description=desc,
            tags=tags,
            views=views,
            likes=likes,
            comments=random.randint(100, 1000),
            thumbnail="https://via.placeholder.com/320x180?text=Fallback+Thumbnail",
            duration=f"{random.randint(15, 60)}s",
            channel=f"{niche.capitalize()} Channel"
        ))
    return fallback_trends


def extract_hashtags(description: str) -> List[str]:
    """Extract hashtags from description using regex."""
    if not description:
        return []
    hashtags = re.findall(r'#\w+', description.lower())
    return [tag[1:] for tag in hashtags]


# ------------------ API Endpoints ------------------

@app.get("/")
async def root():
    return {"message": "YouTube Trend Analyzer API is running!"}


@app.post("/analyze-trends", response_model=TrendAnalysisResponse)
async def analyze_trends(request: NicheRequest):
    try:
        niche = request.niche.strip().lower()
        if not niche:
            raise HTTPException(status_code=400, detail="Niche cannot be empty")

        trending_videos = get_trending_shorts(niche)

        if not trending_videos:
            trends = generate_fallback_trends(niche)
            avg_views = sum(t.views for t in trends) // len(trends)
            avg_likes = sum(t.likes for t in trends) // len(trends)
        else:
            trends = [VideoTrend(**video) for video in trending_videos]
            avg_views = sum(t.views for t in trends) // len(trends)
            avg_likes = sum(t.likes for t in trends) // len(trends) if any(t.likes for t in trends) else 0

        return TrendAnalysisResponse(
            niche=niche,
            trends=trends,
            averageViews=avg_views,
            averageLikes=avg_likes,
            total_trends=len(trends),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing trends: {str(e)}")


# ------------------ Story Generation (Legacy Endpoint) ------------------
@app.post("/generate-story-and-frames", response_model=StoryAndFramesResponse)
async def generate_story_endpoint(request: StoryGenerationRequest):
    """Legacy story generation endpoint (for backward compatibility)."""
    try:
        if not request.user_topic.strip():
            raise HTTPException(status_code=400, detail="User topic cannot be empty")

        result = await generate_story_and_frames(
            request.selected_video,
            request.user_topic.strip()
        )

        # Extract story and frames from the new result format
        story = result.get("full_story", "")
        frames = result.get("frames", [])

        return StoryAndFramesResponse(
            user_topic=request.user_topic,
            selected_video_title=request.selected_video.title,
            story=story,
            frames=frames
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating story and frames: {str(e)}")


# ------------------ New Story Generation Endpoints ------------------
@app.post("/generate-story-and-frames-v1")
async def generate_story_endpoint_v1(request: GenerateStoryRequest):
    """
    New version - Accepts a raw dict for selected_video and optional max_frames.
    """
    try:
        result = await generate_story_and_frames(
            selected_video=request.selected_video,
            user_topic=request.user_topic,
            max_frames=request.max_frames
        )
        return {"success": True, "data": result}

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error in generate_story_endpoint_v1: {e}")
        raise HTTPException(status_code=500, detail=f"Story generation failed: {str(e)}")


@app.post("/generate-story-and-frames-v2")
async def generate_story_endpoint_v2(request: GenerateStoryRequestWithModel):
    """
    Alternative version using a Pydantic model for selected_video.
    """
    try:
        video_dict = request.selected_video.dict()
        result = await generate_story_and_frames(
            selected_video=video_dict,
            user_topic=request.user_topic,
            max_frames=request.max_frames
        )
        return {"success": True, "data": result}

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error in generate_story_endpoint_v2: {e}")
        raise HTTPException(status_code=500, detail=f"Story generation failed: {str(e)}")





@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# ------------------ Run ------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
