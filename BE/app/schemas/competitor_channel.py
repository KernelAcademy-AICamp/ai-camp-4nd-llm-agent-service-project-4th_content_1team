from pydantic import BaseModel, Field
from typing import Dict, List, Optional
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
    applicable_points: Optional[List[str]] = None
    comment_insights: Optional[Dict] = None  # { reactions: [...], needs: [...] }
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


class RecentVideoAnalyzeRequest(BaseModel):
    """영상 AI 분석 요청"""
    video_id: str


class CommentInsights(BaseModel):
    """댓글 분석 결과"""
    reactions: List[str] = []
    needs: List[str] = []


class RecentVideoAnalyzeResponse(BaseModel):
    """영상 AI 분석 응답"""
    video_id: str
    analysis_strengths: List[str]
    analysis_weaknesses: List[str]
    applicable_points: List[str]
    comment_insights: CommentInsights
    analyzed_at: datetime


class CompetitorTopicItem(BaseModel):
    """경쟁자 분석 기반 추천 주제 항목"""
    title: str
    recommendation_reason: str
    content_angles: List[str] = []
    urgency: str = "normal"
    search_keywords: List[str] = []
    trend_basis: Optional[str] = None


class CompetitorTopicsGenerateResponse(BaseModel):
    """경쟁자 분석 기반 주제 추천 응답"""
    success: bool
    message: str
    topics: List[CompetitorTopicItem] = []
