# fetchtrend.py
from fastapi import HTTPException
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import re  # For duration parsing if needed
from typing import List, Dict

# Load environment variables
load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

def get_youtube_service():
    if not YOUTUBE_API_KEY:
        raise HTTPException(status_code=500, detail="YouTube API key not configured")
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

def format_duration(seconds: int) -> str:
    """Format ISO 8601 duration to MM:SS."""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"

def extract_hashtags(description: str) -> List[str]:
    """Extract hashtags from description."""
    if not description:
        return []
    hashtags = re.findall(r'#\w+', description.lower())
    return list(set([tag[1:] for tag in hashtags]))  # Unique, remove #

def get_trending_shorts(niche: str, max_results: int = 20) -> List[Dict]:
    """
    Fetch trending YouTube Shorts videos for a given niche.
    - Searches recent popular videos.
    - Fetches full details: stats, thumbnails, duration.
    - Extracts tags from description.
    Returns list of dicts matching VideoTrend model.
    """
    try:
        youtube = get_youtube_service()
        
        # Dynamic: Last 30 days for recency
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Search for niche + shorts + trending terms
        search_query = f"{niche} shorts trending viral"
        search_response = youtube.search().list(
            q=search_query,
            part="id,snippet",
            maxResults=max_results,
            order="date",  # Recent first; viewCount for popularity
            type="video",
            videoDuration="short",  # <4min, approximates Shorts
            publishedAfter=thirty_days_ago,
        ).execute()

        items = search_response.get("items", [])
        if not items:
            return []

        # Extract videoIds
        video_ids = [item["id"]["videoId"] for item in items]

        # Batch fetch details (stats, thumbnails, duration)
        videos_response = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(video_ids)
        ).execute()

        video_dict = {v["id"]: v for v in videos_response.get("items", [])}

        trends = []
        for item in items:
            video_id = item["id"]["videoId"]
            if video_id not in video_dict:
                continue

            video = video_dict[video_id]
            snippet = video["snippet"]
            stats = video["statistics"]
            content_details = video.get("contentDetails", {})

            # Parse duration (ISO 8601, e.g., PT45S → 45s)
            duration_iso = content_details.get("duration", "PT0S")
            duration_secs = sum(int(x) * 60 ** i for i, x in enumerate(reversed(r"PT(\d+)M(\d+)S".match(duration_iso).groups() or (0, 0))))
            duration = format_duration(duration_secs)

            # Extract tags
            tags = extract_hashtags(snippet.get("description", ""))

            trend = {
                "id": video_id,
                "title": snippet["title"],
                "description": snippet.get("description", f"Trending {niche} short."),
                "tags": tags or [niche.lower(), "shorts", "trending"],  # Fallback
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)) if "likeCount" in stats else 0,
                "comments": int(stats.get("commentCount", 0)) if "commentCount" in stats else 0,
                "thumbnail": snippet["thumbnails"]["medium"]["url"],  # 320x180
                "duration": duration,
                "channel": snippet["channelTitle"],
            }
            trends.append(trend)

        return trends[:max_results]  # Ensure limit
    except HttpError as e:
        print(f"YouTube API error: {e}")
        if e.resp.status == 403:
            raise HTTPException(status_code=403, detail="YouTube API quota exceeded or key invalid")
        return []
    except Exception as e:
        print(f"Unexpected error in get_trending_shorts: {e}")
        return []