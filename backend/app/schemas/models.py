"""
Pydantic models for API request and response validation.
"""
from pydantic import BaseModel, Field
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
    category_id: Optional[str] = Field(
        None,
        description="YouTube category ID (e.g., '24' for Entertainment, '28' for Science & Tech)"
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
    """Request model for creative preferences."""
    tone: str = Field(..., description="Tone of the video (e.g., dynamic, calm)")
    target_audience: str = Field(..., description="Target audience")
    visual_style: str = Field(..., description="Visual style preference")
    camera_movement: str = Field(..., description="Camera movement style")
    effects: str = Field(..., description="Visual effects preference")
    story_format: str = Field(..., description="Story format (e.g., narrative, documentary)")
    duration_seconds: int = Field(..., description="Video duration in seconds")
    constraints: List[str] = Field(
        default_factory=list, 
        description="Additional constraints or requirements"
    )


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
    duration_seconds: Literal[4, 8, 12] = Field(8, description="Must be a valid Sora duration: 4, 8, or 12")


class CreateVideoProjectRequest(BaseModel):
    """Request to create a video project from story frames."""
    title: str = Field("Story Video", max_length=255, min_length=1)
    frames: List[FrameInput] = Field(..., min_length=1)


class GenerateFrameRequest(BaseModel):
    """Request to generate a single frame (frame_id from project_frames)."""
    frame_id: str = Field(..., description="UUID of project_frames row")
