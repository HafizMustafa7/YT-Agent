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
    SuggestCreativeParamsRequest,
)
from app.services.youtube_service import get_trending_shorts
from app.core_yt.topic_validator import validate_topic
from app.services.story_service import generate_story, suggest_dynamic_creative_params
from app.core_yt.engagement_filter import filter_by_engagement, rank_by_engagement
from app.core_yt.trend_summary_builder import build_trend_summary
from app.core_yt.topic_suggestion_engine import generate_topic_suggestions
from app.core_yt.redis_cache import redis_cache
from app.core_yt.creative_builder import build_creative_brief
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
        
        loop = asyncio.get_running_loop()
        is_niche = request.mode == "analyze_niche"

        # ── Primary fetch: full AI threshold (e.g. 30) ──────────────────────
        trends = await loop.run_in_executor(
            None,
            lambda: get_trending_shorts(
                query,
                max_results=settings.YOUTUBE_MAX_RESULTS,
                ai_threshold=settings.YOUTUBE_AI_THRESHOLD,
                search_pages=settings.YOUTUBE_SEARCH_PAGES,
                ai_filter=True,  # Always filter for AI content
                days_window=settings.YOUTUBE_DAYS_WINDOW,
            )
        )

        # ── Graduated fallback (niche mode only) ────────────────────────────
        # For niche searches, AI-generated videos may use softer signals
        # (e.g. no "AI" in the title but tagged with #aivideo). If fewer than
        # 5 videos pass the primary threshold, retry with a lower threshold
        # to widen the net while still requiring some AI relevance.
        if is_niche and len(trends) < 5:
            logger.info(
                "Niche '%s': only %d results at threshold %d — retrying at fallback threshold %d",
                query, len(trends), settings.YOUTUBE_AI_THRESHOLD, settings.YOUTUBE_AI_THRESHOLD_FALLBACK,
            )
            fallback_trends = await loop.run_in_executor(
                None,
                lambda: get_trending_shorts(
                    query,
                    max_results=settings.YOUTUBE_MAX_RESULTS,
                    ai_threshold=settings.YOUTUBE_AI_THRESHOLD_FALLBACK,
                    search_pages=settings.YOUTUBE_SEARCH_PAGES,
                    ai_filter=True,
                    days_window=settings.YOUTUBE_DAYS_WINDOW,
                )
            )
            if len(fallback_trends) > len(trends):
                trends = fallback_trends
                logger.info("Fallback threshold yielded %d results for niche '%s'", len(trends), query)

        if not trends:
            if is_niche:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"No AI-generated trending videos found for '{query}' in the last "
                        f"{settings.YOUTUBE_DAYS_WINDOW} days. Try a different niche or keyword."
                    ),
                )
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
        # ── Step 1: Fetch trends — run_in_executor so the sync YouTube call
        # does not block the event loop (each .execute() can take up to 60 s)
        loop = asyncio.get_running_loop()
        query = niche if request.mode == "analyze_niche" else f"trending {niche} shorts"
        is_niche = request.mode == "analyze_niche"

        # ── Primary fetch with full AI threshold ────────────────────────────
        trends = await loop.run_in_executor(
            None,
            lambda: get_trending_shorts(
                query,
                max_results=settings.YOUTUBE_MAX_RESULTS,
                ai_threshold=settings.YOUTUBE_AI_THRESHOLD,
                search_pages=settings.YOUTUBE_SEARCH_PAGES,
                ai_filter=True,
                days_window=settings.YOUTUBE_DAYS_WINDOW,
            )
        )

        # ── Graduated fallback for niche mode ───────────────────────────────
        if is_niche and len(trends) < 5:
            fallback_trends = await loop.run_in_executor(
                None,
                lambda: get_trending_shorts(
                    query,
                    max_results=settings.YOUTUBE_MAX_RESULTS,
                    ai_threshold=settings.YOUTUBE_AI_THRESHOLD_FALLBACK,
                    search_pages=settings.YOUTUBE_SEARCH_PAGES,
                    ai_filter=True,
                    days_window=settings.YOUTUBE_DAYS_WINDOW,
                )
            )
            if len(fallback_trends) > len(trends):
                trends = fallback_trends

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
        if filtered:
            # Sort filtered videos by engagement ratio descending
            pool = rank_by_engagement(filtered)
        else:
            # No video met the min_engagement threshold (common for new/small niches).
            # Fall back to the full trend list already sorted by views from YouTube.
            # Attach engagement_ratio=0.0 so build_trend_summary doesn't fail on the key.
            pool = [{**v, "engagement_ratio": 0.0} for v in trends]
            logger.info(
                "Engagement filter removed all %d videos for niche '%s' — "
                "falling back to view-sorted pool.",
                len(trends), niche,
            )

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


@router.post("/suggest-creative-params")
async def suggest_creative_params_endpoint(
    request: SuggestCreativeParamsRequest,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Generate dynamic creative parameters (styles, camera motions, etc.) 
    tailored to a specific topic using the LLM.
    """
    try:
        suggestions = await suggest_dynamic_creative_params(request.topic, request.context)
        return {
            "success": True,
            "suggestions": suggestions
        }
    except Exception as e:
        logger.error("Error generating creative params: %s", e)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while suggesting creative parameters. Please try again."
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
        # DATA-2: validate & sanitise all creative preferences through creative_builder
        # before they reach the LLM prompt.  Invalid values are silently snapped to
        # their allowed defaults (cinematic, dolly shot, wide shot, etc.).
        validated_prefs = build_creative_brief(prefs.model_dump())

        story_result = await asyncio.wait_for(
            generate_story(
                topic=request.topic,
                duration=validated_prefs["duration"],
                style=validated_prefs["style"],
                camera_motion=validated_prefs["camera_motion"],
                composition=validated_prefs["composition"],
                focus_and_lens=validated_prefs["focus_and_lens"],
                ambiance=validated_prefs["ambiance"],
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
