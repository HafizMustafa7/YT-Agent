"""
Engagement filter for YouTube trend videos.

Computes a simple engagement ratio: (likes + comments) / views
and filters/sorts a list of trend dicts by that metric.
Pure functions — no I/O, fully unit-testable.
"""
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def compute_engagement_ratio(likes: int, comments: int, views: int) -> float:
    """
    Calculate (likes + comments) / views.

    Returns 0.0 when views == 0 to avoid division-by-zero.
    """
    if views <= 0:
        return 0.0
    return (likes + comments) / views


def filter_by_engagement(
    videos: List[Dict],
    min_ratio: float = 0.01,
) -> List[Dict]:
    """
    Filter a list of trend video dicts to only those meeting the minimum
    engagement ratio threshold.

    Each surviving video gets an 'engagement_ratio' field attached.

    Args:
        videos:    List of video dicts (must have 'likes', 'comments', 'views').
        min_ratio: Minimum (likes + comments) / views.  Default 0.01 (1 %).

    Returns:
        Filtered list with 'engagement_ratio' field added to each item.
    """
    results = []
    for video in videos:
        likes = int(video.get("likes") or 0)
        comments = int(video.get("comments") or 0)
        views = int(video.get("views") or 0)

        ratio = compute_engagement_ratio(likes, comments, views)

        if ratio >= min_ratio:
            enriched = {**video, "engagement_ratio": round(ratio, 6)}
            results.append(enriched)

    logger.debug(
        "Engagement filter: %d/%d videos passed (min_ratio=%.4f)",
        len(results),
        len(videos),
        min_ratio,
    )
    return results


def rank_by_engagement(videos: List[Dict]) -> List[Dict]:
    """
    Sort a list of videos (already filtered) by engagement_ratio descending.

    Args:
        videos: List of video dicts with an 'engagement_ratio' field.

    Returns:
        Sorted list, highest engagement first.
    """
    return sorted(videos, key=lambda v: v.get("engagement_ratio", 0.0), reverse=True)
