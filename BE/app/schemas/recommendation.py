"""
주제 추천 API 스키마
"""
from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel


class SearchKeywords(BaseModel):
    """검색 키워드."""
    youtube: List[str] = []
    google: List[str] = []


class RecommendationItem(BaseModel):
    """개별 추천 항목."""
    title: str
    based_on_topic: str
    trend_basis: str
    recommendation_reason: Optional[str] = None
    search_keywords: Optional[SearchKeywords] = None
    content_angles: List[str] = []
    thumbnail_idea: Optional[str] = None
    urgency: str = "normal"  # urgent, normal, evergreen


class RecommendationResponse(BaseModel):
    """추천 결과 조회 응답."""
    channel_id: str
    recommendations: List[RecommendationItem]
    generated_at: datetime
    expires_at: datetime
    is_expired: bool


class RecommendationGenerateResponse(BaseModel):
    """추천 생성 응답."""
    success: bool
    message: str
    data: Optional[RecommendationResponse] = None
