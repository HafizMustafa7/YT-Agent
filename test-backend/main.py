# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import random

# local imports
from fetchtrend import get_trending_shorts
from generatestory import generate_story

app = FastAPI(title="YouTube Trend Analyzer API")

# ------------------ CORS Middleware ------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ Pydantic Models ------------------
class NicheRequest(BaseModel):
    niche: str

class VideoTopic(BaseModel):
    id: int
    title: str
    description: str
    tags: List[str]
    estimated_views: str
    difficulty: str
    trend_score: int

class CustomTopicRequest(BaseModel):
    custom_topic: str

class TrendAnalysisResponse(BaseModel):
    niche: str
    trending_topics: List[VideoTopic]
    total_topics: int
    analysis_summary: str

class StoryRequest(BaseModel):
    topic: str

# ------------------ Helpers ------------------
def generate_fallback_topics(niche: str):
    topics_list = [
        f"Top {niche} Tips for Beginners",
        f"Common {niche} Mistakes to Avoid",
        f"{niche} Trends You Need to Know",
        f"Quick {niche} Tutorial for Busy People",
        f"Best {niche} Tools Under $50",
        f"{niche} Before and After Results",
        f"Why Everyone is Talking About {niche}",
        f"{niche} Hacks That Actually Work",
    ]

    video_topics = []
    for i, title in enumerate(topics_list):
        topic = VideoTopic(
            id=i + 1,
            title=title,
            description=f"Discover amazing {niche} content that's trending right now. Perfect for YouTube Shorts.",
            tags=[niche, "trending", "viral", "shorts", "tutorial"],
            estimated_views=random.choice(
                ["10K-50K", "50K-100K", "100K-500K", "500K-1M"]
            ),
            difficulty=random.choice(["Easy", "Medium", "Hard"]),
            trend_score=random.randint(6, 10),
        )
        video_topics.append(topic)
    return video_topics

# ------------------ API Endpoints ------------------
@app.get("/")
async def root():
    return {"message": "YouTube Trend Analyzer API is running!"}

@app.post("/analyze-trends", response_model=TrendAnalysisResponse)
async def analyze_trends(request: NicheRequest):
    try:
        niche = request.niche.strip()
        if not niche:
            raise HTTPException(status_code=400, detail="Niche cannot be empty")

        trending_videos = get_trending_shorts(niche)

        # Agar koi trending shorts nahi milte toh fallback use karo
        if not trending_videos:
            video_topics = generate_fallback_topics(niche)
        else:
            video_topics = []
            for i, video in enumerate(trending_videos):
                topic = VideoTopic(
                    id=i + 1,
                    title=video["title"],
                    description=video["description"] or f"Trending {niche} Shorts idea.",
                    tags=[niche, "shorts", "viral", "trending"],
                    estimated_views=random.choice(
                        ["50K-200K", "200K-500K", "500K-1M"]
                    ),
                    difficulty=random.choice(["Easy", "Medium", "Hard"]),
                    trend_score=random.randint(7, 10),
                )
                video_topics.append(topic)

        summary = f"Found {len(video_topics)} trending YouTube Shorts topics for '{niche}'."

        return TrendAnalysisResponse(
            niche=niche,
            trending_topics=video_topics,
            total_topics=len(video_topics),
            analysis_summary=summary,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/generate-custom-topic", response_model=VideoTopic)
async def generate_custom_topic(request: CustomTopicRequest):
    custom_topic = request.custom_topic.strip()
    if not custom_topic:
        raise HTTPException(status_code=400, detail="Custom topic cannot be empty")
    topic = VideoTopic(
        id=999,
        title=f"{custom_topic} - Trending Now",
        description=f"Custom video idea: {custom_topic}.",
        tags=[custom_topic.lower(), "custom", "shorts"],
        estimated_views=random.choice(["25K-75K", "75K-150K", "150K-300K"]),
        difficulty=random.choice(["Easy", "Medium"]),
        trend_score=random.randint(7, 9),
    )
    return topic

@app.post("/generate-story")
async def generate_story_endpoint(request: StoryRequest):
    story = await generate_story(request.topic.strip())
    return {"topic": request.topic, "story": story}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# ------------------ Run ------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
