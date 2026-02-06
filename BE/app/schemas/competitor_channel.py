from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class CompetitorChannelCreate(BaseModel):
    """경쟁 채널 추가 요청"""
    channel_id: str
    title: str
    description: Optional[str] = None
    custom_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    subscriber_count: int = 0
    view_count: int = 0
    video_count: int = 0
    topic_categories: Optional[List[str]] = None
    keywords: Optional[str] = None
    country: Optional[str] = None
    published_at: Optional[datetime] = None
    raw_data: Optional[dict] = None


class CompetitorChannelResponse(BaseModel):
    """경쟁 채널 응답"""
    id: str
    channel_id: str
    title: str
    description: Optional[str] = None
    custom_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    subscriber_count: int
    view_count: int
    video_count: int
    
    # AI 분석 결과
    strengths: Optional[List[str]] = None
    channel_personality: Optional[str] = None
    target_audience: Optional[str] = None
    content_style: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    analyzed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CompetitorChannelListResponse(BaseModel):
    """경쟁 채널 목록 응답"""
    total: int
    channels: List[CompetitorChannelResponse]
