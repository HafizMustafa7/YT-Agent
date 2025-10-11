# fetchtrend.py
from fastapi import HTTPException
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

def get_youtube_service():
    if not YOUTUBE_API_KEY:
        raise HTTPException(status_code=500, detail="YouTube API key not configured")
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

def get_trending_shorts(niche: str, max_results: int = 20):
    """
    Fetch trending YouTube Shorts videos for a given niche.
    Returns list of dict with video details.
    """
    try:
        youtube = get_youtube_service()
        search_response = youtube.search().list(
            q=f"{niche} shorts trending",
            part="id,snippet",
            maxResults=max_results,
            order="viewCount",   # prioritize by views
            type="video",
            videoDuration="short",
            publishedAfter="2024-01-01T00:00:00Z",
        ).execute()

        videos = []
        for item in search_response.get("items", []):
            videos.append(
                {
                    "title": item["snippet"]["title"],
                    "description": item["snippet"]["description"],
                    "channel": item["snippet"]["channelTitle"],
                    "published": item["snippet"]["publishedAt"],
                }
            )
        return videos
    except HttpError as e:
        print(f"YouTube API error: {e}")
        return []
