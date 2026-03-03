"""
Trend Summary Builder

Converts a filtered list of YouTube trend dicts into a compact,
structured text block ready to be injected into an LLM prompt.

No external I/O — pure function.
"""
from typing import List, Dict

# Cap at 15 videos to stay well within LLM context limits
_MAX_VIDEOS_IN_SUMMARY = 15


def build_trend_summary(videos: List[Dict], niche: str) -> str:
    """
    Build a human-readable summary of the top trending videos for the LLM.

    Args:
        videos: Filtered & ranked list of trend video dicts.
        niche:  The niche/query that was used to fetch these trends.

    Returns:
        Multi-line string containing the trend summary.
    """
    if not videos:
        return f"No high-engagement trending videos found for niche: '{niche}'."

    capped = videos[:_MAX_VIDEOS_IN_SUMMARY]
    lines = [
        f"NICHE: {niche}",
        f"TOTAL HIGH-ENGAGEMENT TRENDS ANALYSED: {len(capped)}",
        "",
        "TOP TRENDING VIDEOS (sorted by engagement ratio):",
        "",
    ]

    for i, video in enumerate(capped, start=1):
        title = video.get("title", "").strip()
        tags = video.get("tags") or []
        views = video.get("views", 0)
        likes = video.get("likes", 0)
        comments = video.get("comments", 0)
        engagement = video.get("engagement_ratio", 0.0)
        channel = video.get("channel", "Unknown Channel")

        # Format big numbers
        views_fmt = _fmt_number(views)
        likes_fmt = _fmt_number(likes)
        comments_fmt = _fmt_number(comments)

        tag_str = ", ".join(f"#{t}" for t in tags[:8]) if tags else "none"

        lines.append(f"{i}. {title}")
        lines.append(f"   Channel     : {channel}")
        lines.append(f"   Views       : {views_fmt}  |  Likes: {likes_fmt}  |  Comments: {comments_fmt}")
        lines.append(f"   Engagement  : {engagement:.4f} ({engagement * 100:.2f}%)")
        lines.append(f"   Tags        : {tag_str}")
        lines.append("")

    return "\n".join(lines)


def _fmt_number(n: int) -> str:
    """Format a large integer for human readability."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)
