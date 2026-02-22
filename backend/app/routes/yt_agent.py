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
)
from app.services.youtube_service import get_trending_shorts
from app.core_yt.topic_validator import validate_topic
from app.core_yt.creative_builder import build_creative_brief
from app.services.story_service import generate_story_and_frames
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


@router.post("/stories/generate")
async def generate_story(request: GenerateStoryRequest, current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Generate story and frames with creative brief.
    
    Args:
        request: GenerateStoryRequest with topic, video, and creative preferences
        
    Returns:
        Generated story with frames and creative brief
    """
    try:
        # Build creative brief from preferences
        creative_brief = build_creative_brief(request.creative_preferences.model_dump())
        
        # Generate story with creative brief — timeout after 300s
        # (multi-stage LLM pipeline; needs higher ceiling to avoid mid-run cutoff)
        story_result = await asyncio.wait_for(
            generate_story_and_frames(
                selected_video=request.selected_video,
                user_topic=request.topic,
                creative_brief=creative_brief,
                video_duration=creative_brief.get("duration_seconds", settings.DEFAULT_VIDEO_DURATION),
            ),
            timeout=settings.STORY_GENERATION_TIMEOUT,
        )
        
        return {
            "success": True,
            "story": story_result,
            "creative_brief": creative_brief,
        }
        
    except asyncio.TimeoutError:
        logger.error("Story generation timed out after %ds for topic: %s", settings.STORY_GENERATION_TIMEOUT, request.topic[:50])
        raise HTTPException(
            status_code=504,
            detail="Story generation timed out. The AI service is taking too long. Please try again."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error generating story: %s", e)
        raise HTTPException(
            status_code=500, 
            detail="Story generation failed. Please try again later."
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
