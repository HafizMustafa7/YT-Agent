"""
YouTube API service for fetching trending shorts and AI-generated content.
Moved from fetchtrend.py to follow service layer architecture.
"""
import logging
from fastapi import HTTPException
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
import re
from typing import List, Dict

from app.core.config import settings
from app.core_yt.redis_cache import redis_cache

logger = logging.getLogger(__name__)

# Cached YouTube API service singleton (build() does HTTP discovery, so cache it)
_youtube_service = None


def get_youtube_service():
    """Get or create cached YouTube API service singleton."""
    global _youtube_service
    if not settings.YOUTUBE_API_KEY:
        raise HTTPException(status_code=500, detail="YouTube API key not configured")
    if _youtube_service is None:
        _youtube_service = build("youtube", "v3", developerKey=settings.YOUTUBE_API_KEY)
    return _youtube_service


def format_duration(seconds: int) -> str:
    """Format seconds to MM:SS."""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


def parse_iso_duration(duration: str) -> int:
    """Parse ISO 8601 duration to seconds including hours."""
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def extract_hashtags(description: str) -> List[str]:
    """Extract hashtags from description."""
    if not description:
        return []
    hashtags = re.findall(r'#\w+', description)
    return list(set([tag[1:].lower() for tag in hashtags]))


def calculate_ai_score(title: str, description: str, tags: List[str], channel_title: str) -> int:
    """
    Calculate an AI confidence score (0-100) based on multiple signals.
    Higher score = more likely to be AI-generated.
    """
    score = 0
    text_combined = f"{title} {description} {channel_title}".lower()
    
    # Strong AI indicators (20 points each)
    strong_indicators = [
        r'\bai\s+generated\b', r'\bai\s+created\b', r'\bai\s+made\b',
        r'\bchatgpt\b', r'\bmidjourney\b', r'\bdall-?e\b', r'\bstable\s+diffusion\b',
        r'\brunway\s+ml\b', r'\belevenlabs\b', r'\bsynthesia\b',
        r'\btext\s+to\s+speech\b', r'\btts\s+voice\b', r'\bai\s+voice\b',
        r'\bai\s+animation\b', r'\bai\s+art\b', r'\bai\s+video\b'
    ]
    for pattern in strong_indicators:
        if re.search(pattern, text_combined):
            score += 20
            break  # Don't double count
    
    # Medium AI indicators (15 points each)
    medium_indicators = [
        r'\bgenerated\b.*\bai\b', r'\bai\b.*\bgenerated\b',
        r'\bautomated\b', r'\bai\s+tool\b', r'\bai\s+software\b',
        r'\bpictory\b', r'\bfliki\b', r'\binvideo\b', r'\bdescript\b',
        r'\bmurf\s+ai\b', r'\bsynthesia\b', r'\bd-?id\b'
    ]
    for pattern in medium_indicators:
        if re.search(pattern, text_combined):
            score += 15
            break
    
    # AI-related keywords (10 points each, max 20)
    ai_keywords = ['ai', 'artificial intelligence', 'machine learning', 'neural', 'algorithm']
    keyword_matches = sum(1 for kw in ai_keywords if kw in text_combined)
    score += min(keyword_matches * 10, 20)
    
    # Check hashtags for AI indicators (15 points)
    ai_hashtags = ['ai', 'aiart', 'aianimation', 'aigenerated', 'aivoice', 'aitts', 
                   'artificialintelligence', 'chatgpt', 'midjourney', 'stablediffusion']
    if any(tag in ai_hashtags for tag in tags):
        score += 15
    
    # Channel name indicators (10 points)
    channel_ai_keywords = ['ai', 'artificial', 'automation', 'generated', 'bot']
    if any(kw in channel_title.lower() for kw in channel_ai_keywords):
        score += 10
    
    # Description structure indicators (5 points each)
    if description:
        # AI videos often have structured descriptions with tools mentioned
        if re.search(r'(tools?|software|created with|made with|using):', description, re.IGNORECASE):
            score += 5
        # Links to AI tools
        if re.search(r'(openai\.com|midjourney\.com|elevenlabs\.io|runway\.ml)', description, re.IGNORECASE):
            score += 10
    
    return min(score, 100)  # Cap at 100


def is_ai_generated(title: str, description: str, tags: List[str], channel_title: str, threshold: int = 30) -> bool:
    """
    Determine if content is AI-generated based on confidence score.
    
    Args:
        threshold: Minimum score (0-100) to consider as AI-generated. Default 30.
                   Lower = more results but less precise
                   Higher = fewer results but more precise
    """
    score = calculate_ai_score(title, description, tags, channel_title)
    return score >= threshold


def get_trending_shorts(niche: str, max_results: int = 20, ai_threshold: int = 30, search_pages: int = 3) -> List[Dict]:
    """
    Fetch trending YouTube Shorts videos for a given niche, focusing on AI-generated content.
    Now with Redis caching support.
    
    Args:
        niche: The content niche to search for (e.g., "facts", "motivation", "tech tips")
        max_results: Maximum number of AI-generated results to return
        ai_threshold: AI confidence threshold (0-100). Default 30. Higher = stricter filtering.
        search_pages: Number of search pages to fetch (max 50 results per page)
    
    Returns:
        List of dictionaries containing AI-generated video information, sorted by views
    """
    # Generate cache key
    # Scoped cache keys (M-8) — using "public" for now as there's no auth yet
    cache_key = f"public:trends_{niche}_{max_results}_{ai_threshold}"
    
    # Try to get from cache first
    cached_data = redis_cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # Cache miss - fetch from YouTube API
    try:
        youtube = get_youtube_service()
        fifteen_days_ago = (datetime.now() - timedelta(days=15)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        all_trends = []
        
        # Focused search strategies — 2 queries instead of 4 to save API quota
        # Each search.list costs 100 quota units; daily limit is 10,000
        search_queries = [
            f"{niche} AI generated shorts",
            f"{niche} AI shorts trending",
        ]
        
        for query in search_queries:
            if len(all_trends) >= max_results:
                break
                
            try:
                search_response = youtube.search().list(
                    q=query,
                    part="id,snippet",
                    maxResults=50,  # Max allowed by API
                    order="viewCount",
                    type="video",
                    videoDuration="short",
                    publishedAfter=fifteen_days_ago,
                    regionCode="US",  # Set region to United States
                    relevanceLanguage="en",  # Prioritize English content
                ).execute()

                items = search_response.get("items", [])
                if not items:
                    continue

                # Extract video IDs
                video_ids = [item["id"]["videoId"] for item in items]

                # Batch fetch detailed video information
                videos_response = youtube.videos().list(
                    part="snippet,statistics,contentDetails",
                    id=",".join(video_ids)
                ).execute()

                video_dict = {v["id"]: v for v in videos_response.get("items", [])}

                for item in items:
                    video_id = item["id"]["videoId"]
                    
                    # Skip duplicates
                    if any(t["id"] == video_id for t in all_trends):
                        continue
                    
                    if video_id not in video_dict:
                        continue

                    video = video_dict[video_id]
                    snippet = video["snippet"]
                    stats = video["statistics"]
                    content_details = video.get("contentDetails", {})

                    # Extract hashtags from description
                    tags = extract_hashtags(snippet.get("description", ""))

                    # Calculate AI score and filter
                    ai_score = calculate_ai_score(
                        snippet["title"],
                        snippet.get("description", ""),
                        tags,
                        snippet["channelTitle"]
                    )
                    
                    if ai_score < ai_threshold:
                        continue  # Skip non-AI content

                    # Parse and format duration
                    duration_iso = content_details.get("duration", "PT0S")
                    duration_secs = parse_iso_duration(duration_iso)
                    duration = format_duration(duration_secs)

                    # Build trend dictionary with AI score
                    trend = {
                        "id": video_id,
                        "title": snippet["title"],
                        "description": snippet.get("description", ""),
                        "tags": tags,
                        "views": int(stats.get("viewCount", 0)),
                        "likes": int(stats.get("likeCount", 0)) if "likeCount" in stats else 0,
                        "comments": int(stats.get("commentCount", 0)) if "commentCount" in stats else 0,
                        "thumbnail": snippet["thumbnails"]["medium"]["url"],
                        "duration": duration,
                        "channel": snippet["channelTitle"],
                        "ai_confidence": ai_score,  # Added for debugging/analysis
                        "url": f"https://youtube.com/shorts/{video_id}"  # Direct link
                    }
                    all_trends.append(trend)

                    if len(all_trends) >= max_results:
                        break

            except HttpError as e:
                logger.warning("Search query '%s' failed: %s", query, e)
                continue
        
        # Sort by views (highest first) and return
        all_trends.sort(key=lambda x: x["views"], reverse=True)
        result = all_trends[:max_results]
        
        # Store in cache
        if result:
            redis_cache.set(cache_key, result)
        
        return result

    except HttpError as e:
        logger.error("YouTube API error: %s", e)
        if e.resp.status == 403:
            raise HTTPException(status_code=403, detail="YouTube API quota exceeded or key invalid")
        raise HTTPException(status_code=502, detail="YouTube API error. Please try again later.")
    except Exception as e:
        logger.error("Unexpected error in get_trending_shorts: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch trends. Please try again.")
