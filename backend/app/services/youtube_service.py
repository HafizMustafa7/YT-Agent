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

from app.config.settings import settings
from app.core.redis_cache import redis_cache

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


def calculate_growth_score(video_data: Dict) -> float:
    """
    Calculate growth/virality score based on engagement metrics and velocity.
    
    Formula: (views * 0.4) + (likes * 0.3) + (comments * 0.2) + (velocity * 0.1)
    
    Args:
        video_data: Dictionary containing video metrics and published_at timestamp
    
    Returns:
        Growth score (higher = more viral)
    """
    views = video_data.get("views", 0)
    likes = video_data.get("likes", 0)
    comments = video_data.get("comments", 0)
    
    # Calculate velocity (views per hour since publication)
    published_at = video_data.get("published_at")
    velocity = 0
    if published_at:
        try:
            # Parse ISO 8601 timestamp
            pub_time = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            hours_since_pub = (datetime.now(pub_time.tzinfo) - pub_time).total_seconds() / 3600
            if hours_since_pub > 0:
                velocity = views / hours_since_pub
        except Exception as e:
            logger.warning("Could not calculate velocity: %s", e)
    
    # Apply formula
    score = (views * 0.4) + (likes * 0.3) + (comments * 0.2) + (velocity * 0.1)
    return score


def get_us_trending_videos(
    mode: str,
    niche: str = None,
    max_results: int = 20,
    ai_threshold: int = 30,
    category_id: str = None,
    days_back: int = 3
) -> Dict[str, List[Dict]]:
    """
    Fetch trending YouTube videos from the US, divided into Shorts and Long Videos.
    
    Args:
        mode: "search_trends" (general) or "analyze_niche" (specific topic)
        niche: The content niche to search for (required for analyze_niche mode)
        max_results: Maximum number of AI-generated results to return per category
        ai_threshold: AI confidence threshold (0-100). Default 30.
        category_id: Optional YouTube category ID for filtering
        days_back: Number of days to look back for trends (default 3)
    
    Returns:
        Dictionary with "shorts" and "long_videos" keys containing sorted video lists
    """
    # Generate cache key
    cache_key = f"public:trends_v4_{mode}_{niche or 'general'}_{max_results}_{ai_threshold}_{category_id or 'all'}_{days_back}"
    
    # Try to get from cache first
    cached_data = redis_cache.get(cache_key)
    if cached_data:
        logger.info("Cache HIT for trends: %s", cache_key)
        return cached_data
    
    logger.info("Cache MISS - fetching from YouTube API (mode=%s, niche=%s, days=%d)", mode, niche, days_back)
    
    # Cache miss - fetch from YouTube API
    try:
        youtube = get_youtube_service()
        # Use UTC to avoid timezone issues with YouTube API
        now_utc = datetime.utcnow()
        time_window = (now_utc - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Clean up category_id
        if category_id and not category_id.strip():
            category_id = None
        
        all_candidates = []
        
        # Dual-path strategy
        if mode == "search_trends":
            # Path 1: General trending videos using chart API
            logger.info("Using chart API for general US trends (time window: %s)", time_window)
            try:
                # To get enough videos for both categories, we fetch more
                chart_params = {
                    "part": "snippet,statistics,contentDetails",
                    "chart": "mostPopular",
                    "regionCode": "US",
                    "maxResults": 50,
                }
                if category_id:
                    chart_params["videoCategoryId"] = category_id.strip()
                
                chart_response = youtube.videos().list(**chart_params).execute()
                items = chart_response.get("items", [])
                logger.info("Chart API returned %d items", len(items))
                
                pass_72h = 0
                pass_ai = 0
                
                for video in items:
                    video_id = video["id"]
                    snippet = video["snippet"]
                    stats = video["statistics"]
                    content_details = video.get("contentDetails", {})
                    
                    # Check if published within window
                    published_at = snippet.get("publishedAt", "")
                    if published_at < time_window:
                        continue
                    
                    pass_72h += 1
                    
                    # AI-first filtering
                    tags = extract_hashtags(snippet.get("description", ""))
                    ai_score = calculate_ai_score(
                        snippet["title"],
                        snippet.get("description", ""),
                        tags,
                        snippet["channelTitle"]
                    )
                    
                    if ai_score < ai_threshold:
                        continue
                    
                    pass_ai += 1
                    
                    # Parse duration
                    duration_iso = content_details.get("duration", "PT0S")
                    duration_secs = parse_iso_duration(duration_iso)
                    duration = format_duration(duration_secs)
                    
                    # Build candidate object
                    candidate = {
                        "id": video_id,
                        "title": snippet["title"],
                        "description": snippet.get("description", ""),
                        "tags": tags,
                        "views": int(stats.get("viewCount", 0)),
                        "likes": int(stats.get("likeCount", 0)) if "likeCount" in stats else 0,
                        "comments": int(stats.get("commentCount", 0)) if "commentCount" in stats else 0,
                        "thumbnail": snippet["thumbnails"]["medium"]["url"],
                        "duration": duration,
                        "duration_seconds": duration_secs,
                        "channel": snippet["channelTitle"],
                        "ai_confidence": ai_score,
                        "published_at": published_at,
                        "url": f"https://youtube.com/watch?v={video_id}"
                    }
                    all_candidates.append(candidate)
                    
                logger.info("Path summary (search_trends): 50 candidates -> %d pass time window -> %d pass AI filter", pass_72h, pass_ai)
                    
            except HttpError as e:
                logger.error("Chart API failed: %s", e)
        
        elif mode == "analyze_niche":
            # Path 2: Niche-specific search
            if not niche:
                raise HTTPException(status_code=400, detail="Niche is required for analyze_niche mode")
            
            logger.info("Using search API for niche: %s", niche)
            
            # Focused search queries for AI content
            search_queries = [
                f"{niche} AI generated",
                f"{niche} AI trending",
            ]
            
            for query in search_queries:
                try:
                    search_params = {
                        "q": query,
                        "part": "id,snippet",
                        "maxResults": 50,
                        "order": "viewCount",
                        "type": "video",
                        "publishedAfter": time_window,
                        "regionCode": "US",
                        "relevanceLanguage": "en",
                    }
                    if category_id:
                        search_params["videoCategoryId"] = category_id
                    
                    search_response = youtube.search().list(**search_params).execute()
                    items = search_response.get("items", [])
                    logger.info("Search API returned %d items for query: %s", len(items), query)
                    
                    if not items:
                        continue
                    
                    # Extract video IDs
                    video_ids = [item["id"]["videoId"] for item in items]
                    
                    # Batch fetch detailed info
                    videos_response = youtube.videos().list(
                        part="snippet,statistics,contentDetails",
                        id=",".join(video_ids)
                    ).execute()
                    
                    video_dict = {v["id"]: v for v in videos_response.get("items", [])}
                    
                    for item in items:
                        video_id = item["id"]["videoId"]
                        if any(t["id"] == video_id for t in all_candidates):
                            continue
                        
                        if video_id not in video_dict:
                            continue
                        
                        video = video_dict[video_id]
                        snippet = video["snippet"]
                        stats = video["statistics"]
                        content_details = video.get("contentDetails", {})
                        
                        tags = extract_hashtags(snippet.get("description", ""))
                        ai_score = calculate_ai_score(
                            snippet["title"],
                            snippet.get("description", ""),
                            tags,
                            snippet["channelTitle"]
                        )
                        
                        if ai_score < ai_threshold:
                            continue
                        
                        duration_iso = content_details.get("duration", "PT0S")
                        duration_secs = parse_iso_duration(duration_iso)
                        duration = format_duration(duration_secs)
                        
                        candidate = {
                            "id": video_id,
                            "title": snippet["title"],
                            "description": snippet.get("description", ""),
                            "tags": tags,
                            "views": int(stats.get("viewCount", 0)),
                            "likes": int(stats.get("likeCount", 0)) if "likeCount" in stats else 0,
                            "comments": int(stats.get("commentCount", 0)) if "commentCount" in stats else 0,
                            "thumbnail": snippet["thumbnails"]["medium"]["url"],
                            "duration": duration,
                            "duration_seconds": duration_secs,
                            "channel": snippet["channelTitle"],
                            "ai_confidence": ai_score,
                            "published_at": snippet.get("publishedAt", ""),
                            "url": f"https://youtube.com/watch?v={video_id}"
                        }
                        all_candidates.append(candidate)
                        
                except HttpError as e:
                    logger.warning("Search query '%s' failed: %s", query, e)
                    continue
        else:
            raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}")
        
        # Categorize results
        shorts = []
        long_videos = []
        
        for candidate in all_candidates:
            candidate["growth_score"] = calculate_growth_score(candidate)
            if candidate["duration_seconds"] <= 60:
                shorts.append(candidate)
            else:
                long_videos.append(candidate)
        
        # FALLBACK MECHANISM
        if not shorts and not long_videos and days_back < 15:
            new_days = 7 if days_back < 7 else 15
            logger.info("No results found in last %d days. Retrying with %d days window...", days_back, new_days)
            return get_us_trending_videos(
                mode=mode,
                niche=niche,
                max_results=max_results,
                ai_threshold=max(10, ai_threshold - 10),
                category_id=category_id,
                days_back=new_days
            )
        
        # Sort and limit
        shorts.sort(key=lambda x: x["growth_score"], reverse=True)
        long_videos.sort(key=lambda x: x["growth_score"], reverse=True)
        
        result = {
            "shorts": shorts[:max_results],
            "long_videos": long_videos[:max_results]
        }
        
        logger.info("Found %d shorts and %d long videos", len(result["shorts"]), len(result["long_videos"]))
        
        # Store in cache
        if result["shorts"] or result["long_videos"]:
            redis_cache.set(cache_key, result)
        
        return result
    
    except HttpError as e:
        logger.error("YouTube API error: %s", e)
        if e.resp.status == 403:
            raise HTTPException(status_code=403, detail="YouTube API quota exceeded or key invalid")
        raise HTTPException(status_code=502, detail="YouTube API error. Please try again later.")
    except Exception as e:
        logger.error("Unexpected error in get_us_trending_videos: %s", e)
        raise HTTPException(status_code=500, detail="Failed to fetch trends. Please try again.")


# Backward compatibility alias
get_trending_shorts = get_us_trending_videos
