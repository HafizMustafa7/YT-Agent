from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import os
from datetime import datetime, timedelta
from app.core.config import supabase
import re

router = APIRouter()

# Pydantic models (imported from models)
from app.models.analytics import VideoAnalytics, ChannelInfo, AnalyticsResponse

# Helper functions
async def refresh_access_token(refresh_token: str) -> str:
    """Enhanced refresh YouTube API access token with better debugging"""
    try:
        print(f"🔄 Starting token refresh process...")
        
        # Check environment variables more thoroughly
        google_client_id = os.getenv("GOOGLE_CLIENT_ID")
        google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        youtube_client_id = os.getenv("YOUTUBE_CLIENT_ID")
        youtube_client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
        
        print(f"📋 Environment check:")
        print(f"   GOOGLE_CLIENT_ID: {'✅' if google_client_id else '❌'}")
        print(f"   GOOGLE_CLIENT_SECRET: {'✅' if google_client_secret else '❌'}")
        print(f"   YOUTUBE_CLIENT_ID: {'✅' if youtube_client_id else '❌'}")
        print(f"   YOUTUBE_CLIENT_SECRET: {'✅' if youtube_client_secret else '❌'}")
        
        # Use Google credentials first, fallback to YouTube
        client_id = google_client_id or youtube_client_id
        client_secret = google_client_secret or youtube_client_secret
        
        if not client_id:
            raise HTTPException(
                status_code=500, 
                detail="No CLIENT_ID found. Please set GOOGLE_CLIENT_ID or YOUTUBE_CLIENT_ID environment variable"
            )
        
        if not client_secret:
            raise HTTPException(
                status_code=500, 
                detail="No CLIENT_SECRET found. Please set GOOGLE_CLIENT_SECRET or YOUTUBE_CLIENT_SECRET environment variable"
            )
        
        print(f"🔑 Using client_id: {client_id[:20]}...")
        print(f"🔐 Refresh token: {refresh_token[:20]}...")
        
        # Make the refresh request
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            payload = {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }
            
            print(f"📤 Making refresh request to Google OAuth...")
            
            response = await http_client.post(
                "https://oauth2.googleapis.com/token",
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            print(f"📥 Response status: {response.status_code}")
            print(f"📄 Response body: {response.text}")
            
            if response.status_code == 200:
                response_data = response.json()
                if "access_token" in response_data:
                    new_token = response_data["access_token"]
                    print(f"✅ Token refresh successful! New token: {new_token[:20]}...")
                    return new_token
                else:
                    print(f"❌ No access_token in response: {response_data}")
                    raise HTTPException(
                        status_code=401, 
                        detail=f"Token refresh returned no access_token: {response_data}"
                    )
            elif response.status_code == 400:
                try:
                    error_data = response.json()
                    error_description = error_data.get("error_description", "Unknown error")
                    error_type = error_data.get("error", "unknown_error")
                except:
                    error_description = response.text
                    error_type = "parse_error"
                
                print(f"❌ Bad request error: {error_description}")
                
                if "invalid_grant" in error_description.lower() or error_type == "invalid_grant":
                    raise HTTPException(
                        status_code=401, 
                        detail="Refresh token is invalid or expired. Please re-authenticate your YouTube channel."
                    )
                else:
                    raise HTTPException(
                        status_code=401, 
                        detail=f"Token refresh failed: {error_description}"
                    )
            else:
                print(f"❌ Unexpected status code: {response.status_code}")
                raise HTTPException(
                    status_code=401, 
                    detail=f"Token refresh failed with status {response.status_code}: {response.text}"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        print(f"💥 Token refresh exception: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Token refresh error: {str(e)}"
        )

async def get_channel_videos(access_token: str, channel_id: str) -> List[Dict]:
    """Get all videos from a YouTube channel with better error handling"""
    try:
        print(f"🎬 Fetching videos for channel: {channel_id}")
        videos = []
        next_page_token = None
        page_count = 0
        max_pages = 10  # Limit to prevent infinite loops
        
        while page_count < max_pages:
            async with httpx.AsyncClient(timeout=30.0) as client:
                params = {
                    "part": "snippet",
                    "channelId": channel_id,
                    "maxResults": 50,
                    "order": "date",
                    "type": "video"
                }
                if next_page_token:
                    params["pageToken"] = next_page_token
                    
                print(f"📄 Fetching page {page_count + 1} with params: {params}")
                
                response = await client.get(
                    "https://www.googleapis.com/youtube/v3/search",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params=params
                )
                
                print(f"📊 Search API response status: {response.status_code}")
                
                if response.status_code != 200:
                    print(f"❌ Search API failed: {response.text}")
                    break
                    
                data = response.json()
                
                # Get detailed video information
                video_ids = []
                for item in data.get("items", []):
                    if item.get("id", {}).get("kind") == "youtube#video":
                        video_ids.append(item["id"]["videoId"])
                
                print(f"🔍 Found {len(video_ids)} video IDs on page {page_count + 1}")
                
                if video_ids:
                    video_details = await get_video_details(access_token, video_ids)
                    videos.extend(video_details)
                    print(f"📈 Total videos collected: {len(videos)}")
                
                next_page_token = data.get("nextPageToken")
                page_count += 1
                
                if not next_page_token:
                    print("📄 No more pages to fetch")
                    break
                    
        print(f"🎉 Total videos fetched: {len(videos)}")
        return videos
        
    except Exception as e:
        print(f"💥 Error fetching videos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching videos: {str(e)}")

async def get_video_details(access_token: str, video_ids: List[str]) -> List[Dict]:
    """Get detailed information for specific videos"""
    try:
        print(f"📊 Fetching details for {len(video_ids)} videos...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://www.googleapis.com/youtube/v3/videos",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(video_ids)
                }
            )
            
            print(f"📋 Video details API response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json().get("items", [])
                print(f"✅ Video details fetched for {len(result)} videos")
                return result
            else:
                print(f"❌ Video details API error: {response.text}")
                return []
                
    except Exception as e:
        print(f"💥 Error fetching video details: {e}")
        return []

def calculate_engagement_rate(likes: int, comments: int, views: int) -> float:
    """Calculate engagement rate"""
    if views == 0:
        return 0.0
    return round(((likes + comments) / views) * 100, 2)

def parse_duration(duration: str) -> str:
    """Parse YouTube duration format (PT4M13S) to readable format"""
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration)
    
    if match:
        hours, minutes, seconds = match.groups()
        hours = int(hours) if hours else 0
        minutes = int(minutes) if minutes else 0
        seconds = int(seconds) if seconds else 0
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    return "0:00"

# Debug endpoints
@router.get("/debug/token/{youtube_channel_id}")
async def debug_token_info(youtube_channel_id: str):
    """Debug token information for a specific channel"""
    try:
        result = supabase.table("channels").select("*").eq("youtube_channel_id", youtube_channel_id).single().execute()

        if not result.data:
            return {"error": "Channel not found"}

        channel_data = result.data

        return {
            "channel_id": youtube_channel_id,
            "channel_name": channel_data.get("youtube_channel_name"),
            "has_access_token": bool(channel_data.get("access_token")),
            "has_refresh_token": bool(channel_data.get("refresh_token")),
            "access_token_preview": channel_data.get("access_token", "")[:20] + "..." if channel_data.get("access_token") else None,
            "refresh_token_preview": channel_data.get("refresh_token", "")[:20] + "..." if channel_data.get("refresh_token") else None,
            "token_expiry": channel_data.get("token_expiry"),
            "created_at": channel_data.get("created_at")
        }
    except Exception as e:
        return {"error": str(e)}

@router.post("/debug/test-refresh/{youtube_channel_id}")
async def test_token_refresh(youtube_channel_id: str):
    """Test token refresh for debugging"""
    try:
        result = supabase.table("channels").select("*").eq("youtube_channel_id", youtube_channel_id).single().execute()

        if not result.data:
            return {"error": "Channel not found"}

        refresh_token = result.data.get("refresh_token")
        if not refresh_token:
            return {"error": "No refresh token available"}

        # Test environment variables
        client_id = os.getenv("GOOGLE_CLIENT_ID") or os.getenv("YOUTUBE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or os.getenv("YOUTUBE_CLIENT_SECRET")

        debug_info = {
            "has_client_id": bool(client_id),
            "has_client_secret": bool(client_secret),
            "client_id_preview": client_id[:20] + "..." if client_id else None,
            "refresh_token_preview": refresh_token[:20] + "..." if refresh_token else None
        }

        if not client_id or not client_secret:
            return {
                "error": "Missing client credentials",
                "debug_info": debug_info
            }

        # Try to refresh token with detailed logging
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }

            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data=payload
            )

            return {
                "status_code": response.status_code,
                "response_text": response.text,
                "debug_info": debug_info,
                "payload_keys": list(payload.keys())
            }

    except Exception as e:
        return {"error": str(e)}

# API Routes
@router.get("/")
async def root():
    return {"message": "YouTube Analytics API", "status": "running"}

@router.get("/channels")
async def get_all_channels():
    """Get all channels from database"""
    try:
        print("📊 Fetching all channels from 'channels' table...")
        result = supabase.table('channels').select('*').execute()
        print(f"📋 Database result: {len(result.data)} channels found")
        return {"channels": result.data, "count": len(result.data)}
    except Exception as e:
        print(f"💥 Database error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/channels/{user_id}")
async def get_user_channels(user_id: str):
    """Get channels for a specific user"""
    try:
        print(f"👤 Fetching channels for user_id: {user_id}")

        # First try to get channels for the specific user_id
        result = supabase.table('channels').select('*').eq('user_id', user_id).execute()
        print(f"🎯 User-specific query result: {len(result.data)} channels")

        # If no channels found for specific user, return all channels
        if not result.data:
            print("📊 No channels found for specific user, fetching all channels...")
            result = supabase.table('channels').select('*').execute()
            print(f"📋 All channels result: {len(result.data)} channels")

        return {"channels": result.data, "user_id": user_id, "count": len(result.data)}

    except Exception as e:
        print(f"💥 Error in get_user_channels: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/analytics/{youtube_channel_id}")
async def get_channel_analytics(youtube_channel_id: str) -> AnalyticsResponse:
    """Enhanced analytics endpoint with better error handling"""
    try:
        print(f"🎯 Getting analytics for channel: {youtube_channel_id}")
        
        # Get channel info from Supabase
        result = supabase.table("channels").select("*").eq("youtube_channel_id", youtube_channel_id).single().execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Channel not found in database")
        
        channel_data = result.data
        access_token = channel_data.get("access_token")
        refresh_token = channel_data.get("refresh_token")
        
        print(f"📊 Channel: {channel_data.get('youtube_channel_name')}")
        print(f"🔑 Has access token: {'✅' if access_token else '❌'}")
        print(f"🔄 Has refresh token: {'✅' if refresh_token else '❌'}")
        
        if not access_token:
            raise HTTPException(status_code=401, detail="No access token found for channel")
        
        if not refresh_token:
            raise HTTPException(status_code=401, detail="No refresh token found for channel")
        
        # Test current token first
        token_valid = False
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("🧪 Testing current access token...")
            test_response = await client.get(
                f"https://www.googleapis.com/youtube/v3/channels",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"part": "snippet", "id": youtube_channel_id}
            )
            
            print(f"📊 Token test result: {test_response.status_code}")
            
            if test_response.status_code == 200:
                print("✅ Current token is valid")
                token_valid = True
            elif test_response.status_code == 401:
                print("❌ Current token is invalid/expired")
                try:
                    print("🔄 Attempting to refresh token...")
                    access_token = await refresh_access_token(refresh_token)
                    
                    # Update token in database
                    update_result = supabase.table("channels").update({
                        "access_token": access_token,
                        "token_expiry": (datetime.now() + timedelta(seconds=3600)).isoformat()
                    }).eq("youtube_channel_id", youtube_channel_id).execute()
                    
                    print("✅ Token refreshed and updated in database")
                    token_valid = True
                    
                except HTTPException as refresh_error:
                    print(f"💥 Token refresh failed: {refresh_error.detail}")
                    raise refresh_error
            else:
                print(f"🚫 Unexpected API response: {test_response.status_code} - {test_response.text}")
                raise HTTPException(
                    status_code=500, 
                    detail=f"YouTube API returned unexpected status: {test_response.status_code}"
                )
        
        if not token_valid:
            raise HTTPException(status_code=401, detail="Unable to obtain valid access token")
        
        # Get channel statistics
        async with httpx.AsyncClient(timeout=30.0) as client:
            print("📈 Fetching channel statistics...")
            channel_response = await client.get(
                f"https://www.googleapis.com/youtube/v3/channels",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "part": "statistics,snippet",
                    "id": youtube_channel_id
                }
            )
        
        channel_stats = {}
        if channel_response.status_code == 200:
            channel_info = channel_response.json().get("items", [{}])[0]
            channel_stats = channel_info.get("statistics", {})
            print(f"📊 Channel stats retrieved: {len(channel_stats)} metrics")
        else:
            print(f"⚠️ Failed to get channel stats: {channel_response.status_code}")
        
        # Get videos
        print("🎬 Fetching channel videos...")
        videos_data = await get_channel_videos(access_token, youtube_channel_id)
        
        # Process videos for analytics
        processed_videos = []
        total_views = 0
        
        print(f"⚙️ Processing {len(videos_data)} videos...")
        for i, video in enumerate(videos_data):
            try:
                stats = video.get("statistics", {})
                snippet = video.get("snippet", {})
                content_details = video.get("contentDetails", {})
                
                views = int(stats.get("viewCount", 0))
                likes = int(stats.get("likeCount", 0))
                comments = int(stats.get("commentCount", 0))
                
                total_views += views
                
                video_analytics = VideoAnalytics(
                    video_id=video["id"],
                    title=snippet.get("title", "Unknown Title"),
                    thumbnail=snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                    published_at=snippet.get("publishedAt", ""),
                    views=views,
                    likes=likes,
                    comments=comments,
                    duration=parse_duration(content_details.get("duration", "PT0S")),
                    engagement_rate=calculate_engagement_rate(likes, comments, views)
                )
                processed_videos.append(video_analytics)
                
                if (i + 1) % 10 == 0:
                    print(f"   ✅ Processed {i + 1}/{len(videos_data)} videos...")
                    
            except Exception as e:
                print(f"⚠️ Error processing video {video.get('id', 'unknown')}: {e}")
                continue
        
        print(f"🎉 Successfully processed {len(processed_videos)} videos")
        print(f"👥 Total subscribers: {channel_stats.get('subscriberCount', 0)}")
        print(f"👀 Total views: {total_views:,}")
        
        response = AnalyticsResponse(
            videos=processed_videos,
            total_videos=len(processed_videos),
            total_views=total_views,
            total_subscribers=int(channel_stats.get("subscriberCount", 0))
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"💥 Unexpected error in get_channel_analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get("/ai-insights/{youtube_channel_id}")
async def ai_insights(youtube_channel_id: str):
    """Generate AI-like performance insights for a channel"""
    analytics = await get_channel_analytics(youtube_channel_id)
    videos = analytics.videos

    if not videos:
        return {"error": "No videos available for analysis"}

    # Calculate averages
    avg_views = sum(v.views for v in videos) / len(videos)
    avg_engagement = sum(v.engagement_rate for v in videos) / len(videos)

    insights = []
    for v in videos:
        score = (
            (v.views / (avg_views + 1e-6)) * 0.5 +
            (v.engagement_rate / (avg_engagement + 1e-6)) * 0.3 +
            min(v.likes / 50, 1) * 0.1 +
            min(v.comments / 20, 1) * 0.1
        )

        if score > 1.5 and v.views > 1000:
            trend = "🔥 Trending"
        elif score > 0.9:
            trend = "✅ Normal"
        else:
            trend = "⚠️ Low Performance"

        insights.append({
            "video_id": v.video_id,
            "title": v.title,
            "score": round(score, 2),
            "trend": trend
        })

    return {"insights": insights}

def categorize_video(title: str) -> str:
    title = title.lower()
    if any(w in title for w in ["tutorial", "how to", "guide"]):
        return "Tutorial"
    elif any(w in title for w in ["review", "unboxing"]):
        return "Review"
    elif any(w in title for w in ["vlog", "day in", "life"]):
        return "Vlog"
    else:
        return "Other"

@router.get("/content-summary/{youtube_channel_id}")
async def content_summary(youtube_channel_id: str):
    analytics = await get_channel_analytics(youtube_channel_id)
    videos = analytics.videos

    summary = {}
    for v in videos:
        cat = categorize_video(v.title)
        summary[cat] = summary.get(cat, 0) + 1

    return {"summary": summary}

@router.get("/video/{video_id}")
async def get_video_analytics(video_id: str, youtube_channel_id: str):
    """Get detailed analytics for a specific video"""
    try:
        print(f"🎬 Getting video analytics for: {video_id}")
        
        # Get channel info from Supabase
        result = supabase.table("channels").select("*").eq("youtube_channel_id", youtube_channel_id).single().execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Channel not found")
        
        access_token = result.data["access_token"]
        
        # Get video analytics from YouTube API
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get basic video data
            video_response = await client.get(
                f"https://www.googleapis.com/youtube/v3/videos",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "part": "snippet,statistics,contentDetails",
                    "id": video_id
                }
            )
            
            # Get analytics data (last 30 days)
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            analytics_response = await client.get(
                "https://youtubeanalytics.googleapis.com/v2/reports",
                headers={"Authorization": f"Bearer {access_token}"},
                params={
                    "ids": f"channel=={youtube_channel_id}",
                    "startDate": start_date,
                    "endDate": end_date,
                    "metrics": "views,likes,comments,shares,estimatedMinutesWatched,averageViewDuration",
                    "filters": f"video=={video_id}",
                    "dimensions": "day"
                }
            )
        
        video_data = {}
        analytics_data = {}
        
        if video_response.status_code == 200:
            video_items = video_response.json().get("items", [])
            if video_items:
                video_data = video_items[0]
                print(f"✅ Video data retrieved for: {video_data.get('snippet', {}).get('title', 'Unknown')}")
        
        if analytics_response.status_code == 200:
            analytics_data = analytics_response.json()
            print(f"📊 Analytics data retrieved")
        else:
            print(f"⚠️ Analytics API response: {analytics_response.status_code}")
        
        return {
            "video_data": video_data,
            "analytics_data": analytics_data
        }
        
    except Exception as e:
        print(f"💥 Error fetching video analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching video analytics: {str(e)}")

@router.get("/test-credentials")
async def test_credentials():
    """Test if environment variables are properly set"""
    
    google_client_id = os.getenv("GOOGLE_CLIENT_ID")
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    youtube_client_id = os.getenv("YOUTUBE_CLIENT_ID")
    youtube_client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
    
    return {
        "google_client_id": google_client_id[:20] + "..." if google_client_id else None,
        "google_client_secret": "Set" if google_client_secret else None,
        "youtube_client_id": youtube_client_id[:20] + "..." if youtube_client_id else None,
        "youtube_client_secret": "Set" if youtube_client_secret else None,
        "using_credentials": {
            "client_id": google_client_id or youtube_client_id,
            "client_secret": "Set" if (google_client_secret or youtube_client_secret) else None
        },
        "environment_status": {
            "google_complete": bool(google_client_id and google_client_secret),
            "youtube_complete": bool(youtube_client_id and youtube_client_secret),
            "has_any_credentials": bool((google_client_id or youtube_client_id) and (google_client_secret or youtube_client_secret))
        }
    }
