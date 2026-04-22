"""
API route handlers with versioning.
All endpoints are prefixed with /api/v1
"""
import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from app.routes.auth import get_current_user

logger = logging.getLogger(__name__)

from app.schemas.models import (
    TrendRequest,
    TopicValidationRequest,
    GenerateStoryRequest,
    TopicSuggestionRequest,
)
from app.services.youtube_service import get_trending_shorts
from app.core_yt.topic_validator import validate_topic
from app.services.story_service import generate_story
from app.core_yt.engagement_filter import filter_by_engagement, rank_by_engagement
from app.core_yt.trend_summary_builder import build_trend_summary
from app.core_yt.topic_suggestion_engine import generate_topic_suggestions
from app.core_yt.redis_cache import redis_cache
from app.core.config import settings


# Create API router with v1 prefix
router = APIRouter()


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "service": settings.APP_NAME
    }


@router.post("/trends/fetch")
async def fetch_trends(request: TrendRequest, current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Fetch trending videos based on mode (search_trends or analyze_niche).
    
    Args:
        request: TrendRequest with mode and optional niche
        
    Returns:
        Dictionary with trends data
    """
    try:
        # Determine query based on mode
        if request.mode == "analyze_niche":
            if not request.niche or not request.niche.strip():
                raise HTTPException(
                    status_code=400, 
                    detail="Niche is required for analyze mode."
                )
            query = request.niche.strip()
        elif request.mode == "search_trends":
            query = "trending ai shorts"
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid mode: {request.mode}"
            )
        
        # Fetch from YouTube API
        trends = get_trending_shorts(
            query, 
            max_results=settings.YOUTUBE_MAX_RESULTS,
            ai_threshold=settings.YOUTUBE_AI_THRESHOLD,
            search_pages=settings.YOUTUBE_SEARCH_PAGES
        )
        
        if not trends:
            raise HTTPException(
                status_code=502,
                detail="Unable to fetch trends. Please check your YouTube API key and try again."
            )
        
        # Format response
        return {
            "success": True,
            "mode": request.mode,
            "query_used": query,
            "total_results": len(trends),
            "trends": trends,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching trends: %s", e)
        raise HTTPException(
            status_code=500, 
            detail="An error occurred while fetching trends. Please try again."
        )


@router.post("/topics/validate")
async def validate_topic_endpoint(request: TopicValidationRequest, current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Validate a topic using LLM - checks policy compliance and quality.
    
    Args:
        request: TopicValidationRequest with topic and optional niche hint
        
    Returns:
        Validation result with valid flag, score, reason, issues, and suggestions
    """
    try:
        result = await validate_topic(request.topic, request.niche_hint)
        return {
            "success": True,
            **result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Error validating topic: %s", e)
        raise HTTPException(
            status_code=500, 
            detail="An error occurred during topic validation. Please try again."
        )


@router.post("/topics/suggest")
async def suggest_topics(
    request: TopicSuggestionRequest,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Automatic topic suggestion pipeline.

    Full pipeline:
      1. Fetch trending Shorts via YouTube API (get_trending_shorts)
      2. Filter videos by engagement ratio (likes+comments)/views
      3. Build a compact trend summary for the LLM
      4. Call Gemini to generate ranked topic suggestions
      5. Return Top-N topics with rationale and virality scores

    Results are cached in Redis for 30 minutes (configurable).
    """
    niche = request.niche.strip()
    if not niche:
        raise HTTPException(status_code=400, detail="Niche cannot be empty.")

    # Redis cache key scoped to all pipeline params
    cache_key = (
        f"public:topic_suggestions:{niche}:{request.mode}:"
        f"{request.min_engagement}:{request.top_n}"
    )

    cached = redis_cache.get(cache_key)
    if cached:
        logger.info("Cache HIT for topic suggestions: %s", cache_key)
        return cached

    try:
        # ── Step 1: Fetch trends ──────────────────────────────────────────────
        query = niche if request.mode == "analyze_niche" else f"trending {niche} shorts"
        trends = get_trending_shorts(
            query,
            max_results=settings.YOUTUBE_MAX_RESULTS,
            ai_threshold=settings.YOUTUBE_AI_THRESHOLD,
            search_pages=settings.YOUTUBE_SEARCH_PAGES,
        )

        if not trends:
            return {
                "success": True,
                "niche": niche,
                "topics": [],
                "trends_analysed": 0,
                "message": "No trending videos found for this niche. Try a different niche.",
            }

        # ── Step 2: Engagement filter ─────────────────────────────────────────
        filtered = filter_by_engagement(trends, min_ratio=request.min_engagement)
        # Fall back to all trends if filter removes everything
        pool = rank_by_engagement(filtered) if filtered else trends[:15]

        # ── Step 3: Build trend summary for LLM ──────────────────────────────
        trend_summary = build_trend_summary(pool, niche)

        # ── Step 4+5: LLM topic generation (with timeout guard) ───────────────
        topics = await asyncio.wait_for(
            generate_topic_suggestions(trend_summary, niche, top_n=request.top_n),
            timeout=settings.TOPIC_SUGGESTION_TIMEOUT,
        )

        response = {
            "success": True,
            "niche": niche,
            "topics": topics,
            "trends_analysed": len(pool),
        }

        # Cache the result
        if topics:
            redis_cache.set(cache_key, response, ttl=settings.TOPIC_SUGGESTION_CACHE_TTL)

        return response

    except asyncio.TimeoutError:
        logger.error(
            "Topic suggestion timed out after %ds for niche: %s",
            settings.TOPIC_SUGGESTION_TIMEOUT,
            niche,
        )
        raise HTTPException(
            status_code=504,
            detail="Topic suggestion timed out. The AI service is taking too long. Please try again.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error generating topic suggestions: %s", e)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while generating topic suggestions. Please try again.",
        )


@router.post("/stories/generate")
async def generate_story_endpoint(
    request: GenerateStoryRequest,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Generate a Veo 3.1 frame-by-frame video script.

    Accepts topic + creative preferences, returns a validated story JSON
    with full_story overview and frame-by-frame Veo prompts.
    """
    prefs = request.creative_preferences
    try:
        story_result = await asyncio.wait_for(
            generate_story(
                topic=request.topic,
                duration=prefs.duration,
                style=prefs.style,
                camera_motion=prefs.camera_motion,
                composition=prefs.composition,
                focus_and_lens=prefs.focus_and_lens,
                ambiance=prefs.ambiance,
            ),
            timeout=settings.STORY_GENERATION_TIMEOUT,
        )
        return {"success": True, "story": story_result}

    except asyncio.TimeoutError:
        logger.error(
            "Story generation timed out after %ds for topic: %s",
            settings.STORY_GENERATION_TIMEOUT,
            request.topic[:50],
        )
        raise HTTPException(
            status_code=504,
            detail="Story generation timed out. Please try again.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error generating story: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Story generation failed. Please try again later.",
        )


# ==================== Cache Management Endpoints ====================

@router.get("/cache/stats")
async def get_cache_stats(current_user: dict = Depends(get_current_user)):
    """
    Get Redis cache statistics.
    
    Returns cache hits, misses, hit rate, and Redis info.
    """
    from app.core_yt.redis_cache import redis_cache
    
    stats = redis_cache.get_stats()
    return {
        "success": True,
        "cache_stats": stats
    }


@router.get("/cache/keys")
async def get_cache_keys(current_user: dict = Depends(get_current_user)):
    """Get all cached keys."""
    from app.core_yt.redis_cache import redis_cache
    
    keys = redis_cache.get_all_keys()
    return {
        "success": True,
        "total_keys": len(keys),
        "keys": keys
    }


@router.delete("/cache/clear")
async def clear_cache(current_user: dict = Depends(get_current_user)):
    """Clear all cached data."""
    from app.core_yt.redis_cache import redis_cache
    
    success = redis_cache.clear_all()
    return {
        "success": success,
        "message": "Cache cleared successfully" if success else "Failed to clear cache"
    }


@router.delete("/cache/invalidate/{key}")
async def invalidate_cache_key(key: str, current_user: dict = Depends(get_current_user)):
    """Invalidate specific cache entry."""
    from app.core_yt.redis_cache import redis_cache
    
    success = redis_cache.delete(key)
    return {
        "success": success,
        "message": f"Cache key '{key}' invalidated" if success else "Failed to invalidate key"
    }
