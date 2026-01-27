from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class YouTubePopularSearchRequest(BaseModel):
    """Request body for popular YouTube video search."""

    title: str = Field(..., description="Base title or topic for the video.")
    keywords: Optional[List[str]] = Field(
        default=None,
        description="Optional list of additional keywords to refine the search.",
    )


class YouTubeVideoItem(BaseModel):
    """Single YouTube video item with popularity metrics."""

    video_id: str = Field(..., description="YouTube video ID.")
    title: str
    channel_title: str
    published_at: datetime
    url: str
    thumbnail_url: Optional[str] = None

    view_count: int = 0
    like_count: int = 0

    views_per_day: float
    likes_per_day: float
    popularity_score: float


class YouTubePopularSearchResponse(BaseModel):
    """Response model for popular YouTube video search."""

    items: List[YouTubeVideoItem]

