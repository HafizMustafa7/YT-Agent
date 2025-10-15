from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class VideoAnalytics(BaseModel):
    video_id: str
    title: str
    thumbnail: str
    published_at: str
    views: int
    likes: int
    comments: int
    duration: str
    engagement_rate: float

class ChannelInfo(BaseModel):
    id: str
    user_id: Optional[str] = None
    youtube_channel_id: str
    youtube_channel_name: str
    access_token: str
    refresh_token: str
    token_expiry: Optional[str] = None
    created_at: str

class AnalyticsResponse(BaseModel):
    videos: List[VideoAnalytics]
    total_videos: int
    total_views: int
    total_subscribers: int
