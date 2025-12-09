"""
Trend Fetcher Module - Handles fetching trends from YouTube API.
"""
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from fetchtrend import get_trending_shorts


def fetch_trends(mode: str, niche: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
    """
    Fetch trending videos based on mode.
    
    Args:
        mode: Either 'search_trends' or 'analyze_niche'
        niche: Niche to analyze (required for analyze_niche mode)
        limit: Maximum number of results
    
    Returns:
        Dictionary with trends data
    """
    if mode == "analyze_niche":
        if not niche or not niche.strip():
            raise HTTPException(status_code=400, detail="Niche is required for analyze mode.")
        query = niche.strip()
    elif mode == "search_trends":
        query = "trending ai shorts"
    else:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}")
    
    # Fetch from YouTube API
    trends = get_trending_shorts(query, max_results=limit)
    
    if not trends:
        raise HTTPException(
            status_code=502,
            detail="Unable to fetch trends. Please check your YouTube API key and try again."
        )
    
    # Format response
    return {
        "mode": mode,
        "query_used": query,
        "total_results": len(trends),
        "trends": trends,
    }

