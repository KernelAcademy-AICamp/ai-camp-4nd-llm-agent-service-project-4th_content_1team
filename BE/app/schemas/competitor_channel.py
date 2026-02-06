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


class CompetitorChannelVideoResponse(BaseModel):
    """경쟁 채널 영상 응답"""
    id: str
    video_id: str
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    published_at: Optional[datetime] = None
    duration: Optional[str] = None
    view_count: int
    like_count: int
    comment_count: int
    
    # AI 분석
    analysis_summary: Optional[str] = None
    analysis_strengths: Optional[List[str]] = None
    analysis_weaknesses: Optional[List[str]] = None
    audience_reaction: Optional[str] = None
    analyzed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


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
    
    # 최신 영상 (relationship)
    recent_videos: Optional[List[CompetitorChannelVideoResponse]] = None
    
    created_at: datetime
    updated_at: datetime
    analyzed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CompetitorChannelListResponse(BaseModel):
    """경쟁 채널 목록 응답"""
    total: int
    channels: List[CompetitorChannelResponse]
