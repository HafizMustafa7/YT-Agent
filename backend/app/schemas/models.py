"""
Pydantic models for API request and response validation.
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Literal


class TrendRequest(BaseModel):
    """Request model for fetching trends."""
    mode: Literal["search_trends", "analyze_niche"] = Field(
        ..., 
        description="Mode for fetching trends: 'search_trends' or 'analyze_niche'"
    )
    niche: Optional[str] = Field(
        None, 
        description="Niche to analyze (required for analyze_niche mode)"
    )


class TopicValidationRequest(BaseModel):
    """Request model for topic validation."""
    topic: str = Field(..., description="Topic to validate", max_length=500)
    niche_hint: Optional[str] = Field(
        None, 
        description="Optional niche hint for context",
        max_length=200
    )


class CreativePreferencesRequest(BaseModel):
    """Request model for creative preferences using Veo specification."""
    resolution: str = Field(..., description="Video resolution")
    aspect_ratio: str = Field(..., description="Video aspect ratio")
    duration: int = Field(..., description="Target duration in seconds")
    style: str = Field(..., description="Visual style")
    camera_motion: str = Field(..., description="Camera motion technique")
    composition: str = Field(..., description="Scene composition")
    focus_and_lens: str = Field(..., description="Camera focus and lens type")
    ambiance: str = Field(..., description="Lighting and atmosphere")


class GenerateStoryRequest(BaseModel):
    """Request model for story generation."""
    topic: str = Field(..., description="Topic for the story", max_length=500)
    selected_video: Dict[str, Any] = Field(
        ..., 
        description="Selected video data or custom video object"
    )
    creative_preferences: CreativePreferencesRequest = Field(
        ..., 
        description="Creative direction preferences"
    )


# ----- Video generation -----


class FrameInput(BaseModel):
    """One frame for video project creation."""
    frame_num: int = Field(..., ge=1)
    ai_video_prompt: str = Field(..., min_length=1, max_length=5000)
    scene_description: Optional[str] = None
    duration_seconds: Literal[8, 15, 32, 46, 60] = Field(8, description="Target duration specified by Veo")


class CreateVideoProjectRequest(BaseModel):
    """Request to create a video project from story frames."""
    title: str = Field("Story Video", max_length=255, min_length=1)
    channel_id: Optional[str] = Field(None, description="YouTube Channel ID to associate with the project")
    frames: List[FrameInput] = Field(..., min_length=1)


class GenerateFrameRequest(BaseModel):
    """Request to generate a single frame (frame_id from project_frames)."""
    frame_id: str = Field(..., description="UUID of project_frames row")


# ----- Topic Suggestion -----


class TopicSuggestionRequest(BaseModel):
    """Request model for automatic topic suggestion pipeline."""
    niche: str = Field(..., max_length=200, description="Content niche / query used to fetch trends")
    mode: Literal["search_trends", "analyze_niche"] = Field(
        "search_trends",
        description="Trend fetch mode passed through to youtube_service"
    )
    min_engagement: float = Field(
        0.01,
        ge=0.0,
        le=1.0,
        description="Minimum (likes+comments)/views ratio to include a video in the analysis"
    )
    top_n: int = Field(5, ge=1, le=10, description="Number of topic suggestions to return")


class SuggestedTopic(BaseModel):
    """A single ranked topic suggestion from the LLM."""
    rank: int = Field(..., description="Rank position (1 = best)")
    topic: str = Field(..., description="Specific topic title / concept")
    rationale: str = Field(..., description="One-sentence explanation of viral potential")
    score: int = Field(..., ge=0, le=100, description="LLM virality score 0-100")


class TopicSuggestionResponse(BaseModel):
    """Response model for the topic suggestion endpoint."""
    success: bool
    niche: str
    topics: List[SuggestedTopic]
    trends_analysed: int = Field(..., description="Number of videos fed to the LLM after filtering")
