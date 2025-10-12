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
    allow_origins=["*"],  # Update to your frontend URL in production, e.g., ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ Pydantic Models ------------------
# Updated to match frontend: id (videoId), title, description, tags (hashtags), views (int), etc.
class VideoTrend(BaseModel):  # Renamed from VideoTopic for clarity; removed unused fields
    id: str  # YouTube videoId
    title: str
    description: str
    tags: List[str]  # Extracted hashtags
    views: int  # Real view count
    likes: Optional[int] = 0  # Optional if not available
    comments: Optional[int] = 0
    thumbnail: str  # Default thumbnail URL
    duration: str  # Formatted duration (e.g., "0:45")
    channel: str

class NicheRequest(BaseModel):
    niche: str

class StoryGenerationRequest(BaseModel):
    selected_video: VideoTrend  # Pass full selected video details for context
    user_topic: str  # User's custom topic input

class TrendAnalysisResponse(BaseModel):
    niche: str
    trends: List[VideoTrend]  # Matches frontend data.trends
    averageViews: int  # Real average
    averageLikes: Optional[int] = 0
    total_trends: int

class StoryAndFramesResponse(BaseModel):
    user_topic: str
    selected_video_title: str
    story: str  # Full generated story
    frames: List[Dict[str, Any]]  # List of 6-9 frames: [{"frame_num": 1, "prompt": "...", "description": "..."}]

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
        tags = base_tags + [f"tip{i}", f"hack{i}"]  # Mock hashtags
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
            thumbnail="https://via.placeholder.com/320x180?text=Fallback+Thumbnail",  # Mock
            duration=f"{random.randint(15, 60)}s",
            channel=f"{niche.capitalize()} Channel"
        ))
    return fallback_trends

def extract_hashtags(description: str) -> List[str]:
    """Extract hashtags from description using regex."""
    if not description:
        return []
    hashtags = re.findall(r'#\w+', description.lower())
    return [tag[1:] for tag in hashtags]  # Remove #

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
            # Use fallback
            trends = generate_fallback_trends(niche)
            avg_views = sum(t.views for t in trends) // len(trends)
            avg_likes = sum(t.likes for t in trends) // len(trends) if trends else 0
        else:
            trends = [VideoTrend(**video) for video in trending_videos]  # Already structured
            avg_views = sum(t.views for t in trends) // len(trends)
            avg_likes = sum(t.likes for t in trends) // len(trends) if any(t.likes for t in trends) else 0

        summary = f"Found {len(trends)} trending YouTube Shorts for '{niche}'."

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

@app.post("/generate-story-and-frames", response_model=StoryAndFramesResponse)  # Renamed/Updated endpoint
async def generate_story_endpoint(request: StoryGenerationRequest):
    try:
        if not request.user_topic.strip():
            raise HTTPException(status_code=400, detail="User topic cannot be empty")
        
        # Call updated function that generates story + frames
        story, frames = await generate_story_and_frames(
            request.selected_video, 
            request.user_topic.strip()
        )
        
        return StoryAndFramesResponse(
            user_topic=request.user_topic,
            selected_video_title=request.selected_video.title,
            story=story,
            frames=frames  # List of dicts: [{"frame_num": 1, "prompt": "Detailed AI video prompt...", "description": "Brief scene desc"}]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating story and frames: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# ------------------ Run ------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)