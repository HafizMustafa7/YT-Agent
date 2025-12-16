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


class TopicValidationRequest(BaseModel):
    """Request model for topic validation."""
    topic: str = Field(..., description="Topic to validate")
    niche_hint: Optional[str] = Field(
        None, 
        description="Optional niche hint for context"
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
    topic: str = Field(..., description="Topic for the story")
    selected_video: Dict[str, Any] = Field(
        ..., 
        description="Selected video data or custom video object"
    )
    creative_preferences: CreativePreferencesRequest = Field(
        ..., 
        description="Creative direction preferences"
    )
