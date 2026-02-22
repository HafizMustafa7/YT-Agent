import logging
import os
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

import httpx
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.core.config import supabase
from app.models.analytics import VideoAnalytics, ChannelInfo, AnalyticsResponse
from app.routes.auth import get_current_user
from app.core_yt.redis_cache import redis_cache

# Cache TTLs
_TTL_ANALYTICS = 3600  # 1 hour — expensive multi-page YouTube API call

from app.core_yt.google_service import get_google_http_client, refresh_youtube_token

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Helper: fetch all channel videos
# ---------------------------------------------------------------------------

async def get_channel_videos(access_token: str, channel_id: str) -> List[Dict]:
    """Fetch all videos from a YouTube channel with shared client and higher timeout."""
    logger.info("Fetching videos for channel: %s", channel_id)
    videos: List[Dict] = []
    next_page_token: Optional[str] = None
    page_count = 0
    max_pages = 10

    client = await get_google_http_client()
    while page_count < max_pages:
        params: Dict[str, Any] = {
            "part": "snippet",
            "channelId": channel_id,
            "maxResults": 50,
            "order": "date",
            "type": "video",
        }
        if next_page_token:
            params["pageToken"] = next_page_token

        logger.debug("Fetching video page %d", page_count + 1)

        # Higher timeout for search API (60s)
        response = await client.get(
            "https://www.googleapis.com/youtube/v3/search",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
            timeout=60.0
        )

        if response.status_code != 200:
            logger.warning("Search API failed on page %d: %s", page_count + 1, response.status_code)
            break

        data = response.json()
        video_ids = [
            item["id"]["videoId"]
            for item in data.get("items", [])
            if item.get("id", {}).get("kind") == "youtube#video"
        ]

        logger.debug("Found %d video IDs on page %d", len(video_ids), page_count + 1)

        if video_ids:
            details = await get_video_details(access_token, video_ids)
            videos.extend(details)

        next_page_token = data.get("nextPageToken")
        page_count += 1
        if not next_page_token:
            break

    logger.info("Total videos fetched for channel %s: %d", channel_id, len(videos))
    return videos


async def get_video_details(
    access_token: str,
    video_ids: List[str],
) -> List[Dict]:
    """Get detailed information for specific video IDs using shared client."""
    logger.debug("Fetching details for %d videos", len(video_ids))
    try:
        client = await get_google_http_client()
        response = await client.get(
            "https://www.googleapis.com/youtube/v3/videos",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"part": "snippet,statistics,contentDetails", "id": ",".join(video_ids)},
            timeout=60.0
        )
        if response.status_code == 200:
            result = response.json().get("items", [])
            logger.debug("Video details fetched for %d items", len(result))
            return result
        logger.warning("Video details API error: %d", response.status_code)
        return []
    except Exception as e:
        logger.error("Error fetching video details: %s", e)
        return []


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def calculate_engagement_rate(likes: int, comments: int, views: int) -> float:
    if views == 0:
        return 0.0
    return round(((likes + comments) / views) * 100, 2)


def parse_duration(duration: str) -> str:
    """Parse YouTube ISO 8601 duration (PT4M13S) to human-readable string."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
    if match:
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"
    return "0:00"


def categorize_video(title: str) -> str:
    t = title.lower()
    if any(w in t for w in ["tutorial", "how to", "guide"]):
        return "Tutorial"
    if any(w in t for w in ["review", "unboxing"]):
        return "Review"
    if any(w in t for w in ["vlog", "day in", "life"]):
        return "Vlog"
    return "Other"


# ---------------------------------------------------------------------------
# Debug endpoints (protected)
# ---------------------------------------------------------------------------

@router.get("/debug/token/{channel_id}")
async def debug_token_info(channel_id: str, current_user: dict = Depends(get_current_user)):
    """Debug token information for a specific channel."""
    try:
        result = (
            supabase.table("channels")
            .select("*")
            .eq("channel_id", channel_id)
            .eq("user_id", current_user["id"])
            .single()
            .execute()
        )
        if not result.data:
            return {"error": "Channel not found"}
        cd = result.data
        return {
            "channel_id": channel_id,
            "channel_name": cd.get("channel_name"),
            "has_access_token": bool(cd.get("access_token")),
            "has_refresh_token": bool(cd.get("refresh_token")),
            "token_expiry": cd.get("token_expiry"),
            "created_at": cd.get("created_at"),
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/debug/test-refresh/{channel_id}")
async def test_token_refresh(channel_id: str, current_user: dict = Depends(get_current_user)):
    """Test token refresh for debugging."""
    try:
        result = (
            supabase.table("channels")
            .select("*")
            .eq("channel_id", channel_id)
            .eq("user_id", current_user["id"])
            .single()
            .execute()
        )
        if not result.data:
            return {"error": "Channel not found"}

        refresh_token = result.data.get("refresh_token")
        if not refresh_token:
            return {"error": "No refresh token available"}

        client_id = os.getenv("GOOGLE_CLIENT_ID") or os.getenv("YOUTUBE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or os.getenv("YOUTUBE_CLIENT_SECRET")
        debug_info = {
            "has_client_id": bool(client_id),
            "has_client_secret": bool(client_secret),
            "client_id_preview": client_id[:20] + "..." if client_id else None,
        }

        if not client_id or not client_secret:
            return {"error": "Missing client credentials", "debug_info": debug_info}

        async with _make_client() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
        return {
            "status_code": response.status_code,
            "response_text": response.text,
            "debug_info": debug_info,
        }
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@router.get("/")
async def root():
    return {"message": "YouTube Analytics API", "status": "running"}


@router.get("/channels")
async def get_all_channels(current_user: dict = Depends(get_current_user)):
    """Get all channels for the current user."""
    try:
        logger.info("Fetching channels for user: %s", current_user["id"])
        result = supabase.table("channels").select("*").eq("user_id", current_user["id"]).execute()
        return {"channels": result.data, "count": len(result.data)}
    except Exception as e:
        logger.error("Database error fetching channels: %s", e)
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/channels/{user_id}")
async def get_user_channels(user_id: str, current_user: dict = Depends(get_current_user)):
    """Get channels for a specific user, with ownership check."""
    if user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to view these channels")
    try:
        logger.info("Fetching channels for user_id: %s", user_id)
        result = supabase.table("channels").select("*").eq("user_id", user_id).execute()
        return {"channels": result.data, "user_id": user_id, "count": len(result.data)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching channels for user %s: %s", user_id, e)
        raise HTTPException(status_code=500, detail=f"Database error: {e}")


@router.get("/analytics/{channel_id}")
async def get_channel_analytics(
    channel_id: str, current_user: dict = Depends(get_current_user)
) -> AnalyticsResponse:
    """Enhanced analytics endpoint with ownership check and automatic token refresh."""
    try:
        logger.info("Getting analytics for channel: %s", channel_id)

        # --- Cache check (serves from Redis if within TTL) ---
        cache_key = f"analytics:{channel_id}:{current_user['id']}"
        cached = redis_cache.get(cache_key)
        if cached:
            logger.info("[CACHE HIT] analytics for channel %s", channel_id)
            return AnalyticsResponse(**cached)

        result = (
            supabase.table("channels")
            .select("*")
            .eq("channel_id", channel_id)
            .eq("user_id", current_user["id"])
            .single()
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Channel not found in database")

        channel_data = result.data
        access_token = channel_data.get("access_token")
        refresh_tok = channel_data.get("refresh_token")

        logger.debug(
            "Channel %s — has_access_token: %s, has_refresh_token: %s",
            channel_data.get("channel_name"),
            bool(access_token),
            bool(refresh_tok),
        )

        if not access_token:
            raise HTTPException(status_code=401, detail="No access token found for channel")
        if not refresh_tok:
            raise HTTPException(status_code=401, detail="No refresh token found for channel")

        # Test current token health
        client = await get_google_http_client()
        test_response = await client.get(
            "https://www.googleapis.com/youtube/v3/channels",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"part": "snippet", "id": channel_id},
            timeout=15.0
        )

        if test_response.status_code == 401:
            logger.info("Access token expired for channel %s — refreshing via google_service", channel_id)
            success = await refresh_youtube_token(channel_data)
            if not success:
                 raise HTTPException(status_code=401, detail="Could not refresh YouTube token")
            
            # Refetch channel data for new token
            result = supabase.table("channels").select("*").eq("channel_id", channel_id).execute()
            channel_data = result.data[0]
            access_token = channel_data["access_token"]
            redis_cache.delete(cache_key)
        elif test_response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail=f"YouTube API connectivity issue: {test_response.status_code}",
            )

        # Get channel statistics
        client = await get_google_http_client()
        channel_response = await client.get(
            "https://www.googleapis.com/youtube/v3/channels",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"part": "statistics,snippet", "id": channel_id},
            timeout=30.0
        )

        channel_stats = {}
        if channel_response.status_code == 200:
            items = channel_response.json().get("items", [{}])
            channel_stats = items[0].get("statistics", {}) if items else {}
            logger.debug("Channel stats: %d metrics", len(channel_stats))
        else:
            logger.warning("Failed to get channel stats: %d", channel_response.status_code)

        # Fetch all videos
        videos_data = await get_channel_videos(access_token, channel_id)

        processed_videos = []
        total_views = 0

        for i, video in enumerate(videos_data):
            try:
                stats = video.get("statistics", {})
                snippet = video.get("snippet", {})
                content_details = video.get("contentDetails", {})
                views = int(stats.get("viewCount", 0))
                likes = int(stats.get("likeCount", 0))
                comments = int(stats.get("commentCount", 0))
                total_views += views
                processed_videos.append(
                    VideoAnalytics(
                        video_id=video["id"],
                        title=snippet.get("title", "Unknown Title"),
                        thumbnail=snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                        published_at=snippet.get("publishedAt", ""),
                        views=views,
                        likes=likes,
                        comments=comments,
                        duration=parse_duration(content_details.get("duration", "PT0S")),
                        engagement_rate=calculate_engagement_rate(likes, comments, views),
                    )
                )
                if (i + 1) % 10 == 0:
                    logger.debug("Processed %d/%d videos...", i + 1, len(videos_data))
            except Exception as e:
                logger.warning("Error processing video %s: %s", video.get("id", "?"), e)
                continue

        logger.info(
            "Analytics complete — %d videos processed, %d total views, %s subscribers",
            len(processed_videos),
            total_views,
            channel_stats.get("subscriberCount", "?"),
        )

        return AnalyticsResponse(
            videos=processed_videos,
            total_videos=len(processed_videos),
            total_views=total_views,
            total_subscribers=int(channel_stats.get("subscriberCount", 0)),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error in get_channel_analytics: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.get("/ai-insights/{channel_id}")
async def ai_insights(channel_id: str, current_user: dict = Depends(get_current_user)):
    """Generate AI-like performance insights for a channel."""
    analytics = await get_channel_analytics(channel_id, current_user)
    videos = analytics.videos
    if not videos:
        return {"error": "No videos available for analysis"}

    avg_views = sum(v.views for v in videos) / len(videos)
    avg_engagement = sum(v.engagement_rate for v in videos) / len(videos)

    insights = []
    for v in videos:
        score = (
            (v.views / (avg_views + 1e-6)) * 0.5
            + (v.engagement_rate / (avg_engagement + 1e-6)) * 0.3
            + min(v.likes / 50, 1) * 0.1
            + min(v.comments / 20, 1) * 0.1
        )
        if score > 1.5 and v.views > 1000:
            trend = "🔥 Trending"
        elif score > 0.9:
            trend = "✅ Normal"
        else:
            trend = "⚠️ Low Performance"
        insights.append({"video_id": v.video_id, "title": v.title, "score": round(score, 2), "trend": trend})

    return {"insights": insights}


@router.get("/content-summary/{channel_id}")
async def content_summary(channel_id: str, current_user: dict = Depends(get_current_user)):
    """Get content category summary."""
    analytics = await get_channel_analytics(channel_id, current_user)
    summary: Dict[str, int] = {}
    for v in analytics.videos:
        cat = categorize_video(v.title)
        summary[cat] = summary.get(cat, 0) + 1
    return {"summary": summary}


@router.get("/video/{video_id}")
async def get_video_analytics(
    video_id: str, channel_id: str, current_user: dict = Depends(get_current_user)
):
    """Get detailed analytics for a specific video with ownership check."""
    try:
        logger.info("Getting video analytics for: %s", video_id)

        result = (
            supabase.table("channels")
            .select("*")
            .eq("channel_id", channel_id)
            .eq("user_id", current_user["id"])
            .single()
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="Channel not found")

        access_token = result.data["access_token"]
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        client = await get_google_http_client()
        video_response = await client.get(
            "https://www.googleapis.com/youtube/v3/videos",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"part": "snippet,statistics,contentDetails", "id": video_id},
            timeout=30.0
        )
        analytics_response = await client.get(
            "https://youtubeanalytics.googleapis.com/v2/reports",
            headers={"Authorization": f"Bearer {access_token}"},
            params={
                "ids": f"channel=={channel_id}",
                "startDate": start_date,
                "endDate": end_date,
                "metrics": "views,likes,comments,shares,estimatedMinutesWatched,averageViewDuration",
                "filters": f"video=={video_id}",
                "dimensions": "day",
            },
            timeout=60.0
        )

        video_data = {}
        analytics_data = {}

        if video_response.status_code == 200:
            items = video_response.json().get("items", [])
            video_data = items[0] if items else {}
            logger.info("Video data retrieved: %s", video_data.get("snippet", {}).get("title", "?"))

        if analytics_response.status_code == 200:
            analytics_data = analytics_response.json()
        else:
            logger.warning("Analytics API response: %d", analytics_response.status_code)

        return {"video_data": video_data, "analytics_data": analytics_data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching video analytics: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching video analytics: {e}")


@router.get("/test-credentials")
async def test_credentials(current_user: dict = Depends(get_current_user)):
    """Test if environment variables are properly set."""
    google_client_id = os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    youtube_client_id = os.getenv("YOUTUBE_CLIENT_ID")
    youtube_client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")

    return {
        "google_client_id": google_client_id[:20] + "..." if google_client_id else None,
        "google_client_secret": "Set" if google_client_secret else None,
        "youtube_client_id": youtube_client_id[:20] + "..." if youtube_client_id else None,
        "youtube_client_secret": "Set" if youtube_client_secret else None,
        "environment_status": {
            "google_complete": bool(google_client_id and google_client_secret),
            "youtube_complete": bool(youtube_client_id and youtube_client_secret),
            "has_any_credentials": bool(
                (google_client_id or youtube_client_id)
                and (google_client_secret or youtube_client_secret)
            ),
        },
    }
