"""
콘텐츠 주제 추천 API 스키마

채널 맞춤 추천(주간)과 트렌드 기반 추천(일간)을 위한 Pydantic 스키마입니다.
"""
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field


# =============================================================================
# 기본 주제 스키마
# =============================================================================

class TopicBase(BaseModel):
    """주제 기본 정보 (공통)."""
    title: str
    based_on_topic: Optional[str] = None
    trend_basis: Optional[str] = None
    recommendation_reason: Optional[str] = None
    recommendation_type: Optional[str] = None  # viewer_needs | hit_pattern | trend_driven
    recommendation_direction: Optional[str] = None  # 영상 방향성 제안
    source_layer: Optional[str] = None  # core | adjacent
    urgency: str = "normal"  # urgent / normal / evergreen
    search_keywords: List[str] = Field(default_factory=list)  # ["키워드1", "키워드2", ...]
    content_angles: List[str] = Field(default_factory=list)   # ["관점1", "관점2"]
    thumbnail_idea: Optional[str] = None


class TopicResponse(TopicBase):
    """주제 조회 응답."""
    id: str
    channel_id: str
    rank: int
    display_status: str  # shown / queued / skipped
    status: str  # recommended / confirmed / scripting / completed
    scheduled_date: Optional[date] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    topic_type: str  # "channel" 또는 "trend" (FE 구분용)

    class Config:
        from_attributes = True


# =============================================================================
# 채널 맞춤 추천 스키마
# =============================================================================

class ChannelTopicCreate(TopicBase):
    """채널 맞춤 주제 생성용."""
    rank: int
    display_status: str = "queued"


class ChannelTopicResponse(TopicResponse):
    """채널 맞춤 주제 응답."""
    topic_type: str = "channel"


# =============================================================================
# 트렌드 추천 스키마
# =============================================================================

class TrendTopicCreate(TopicBase):
    """트렌드 주제 생성용."""
    rank: int
    display_status: str = "queued"
    urgency: str = "urgent"  # 트렌드는 기본 urgent


class TrendTopicResponse(TopicResponse):
    """트렌드 주제 응답."""
    topic_type: str = "trend"


# =============================================================================
# 상태 변경 스키마
# =============================================================================

class TopicStatusUpdate(BaseModel):
    """주제 상태 변경 요청."""
    status: str  # confirmed / scripting / completed
    scheduled_date: Optional[date] = None  # 확정 시 날짜 지정


class TopicSkipResponse(BaseModel):
    """주제 건너뛰기(새로고침) 응답."""
    skipped_topic_id: str
    new_topic: Optional[TopicResponse] = None  # 다음 후보 (없으면 None)
    remaining_queued: int  # 남은 대기 주제 수


# =============================================================================
# 통합 조회 스키마
# =============================================================================

class TopicsListResponse(BaseModel):
    """전체 추천 주제 목록 응답 (채널 + 트렌드)."""
    channel_topics: List[ChannelTopicResponse] = []  # shown 상태인 채널 맞춤 (최대 5개)
    trend_topics: List[TrendTopicResponse] = []      # shown 상태인 트렌드 (최대 2개)
    channel_expires_at: Optional[datetime] = None    # 채널 추천 만료 시간
    trend_expires_at: Optional[datetime] = None      # 트렌드 추천 만료 시간


# =============================================================================
# 생성 응답 스키마
# =============================================================================

class TopicGenerateResponse(BaseModel):
    """추천 생성 응답."""
    success: bool
    message: str
    generated_count: int = 0
    shown_count: int = 0


class ChannelTopicsGenerateResponse(TopicGenerateResponse):
    """채널 맞춤 추천 생성 응답."""
    topics: List[ChannelTopicResponse] = []  # shown 상태인 것만


class TrendTopicsGenerateResponse(TopicGenerateResponse):
    """트렌드 추천 생성 응답."""
    topics: List[TrendTopicResponse] = []  # shown 상태인 것만


# =============================================================================
# 레거시 호환 (기존 API 지원용 - 점진적 마이그레이션)
# =============================================================================

class RecommendationItem(TopicBase):
    """
    개별 추천 항목 (레거시 호환).

    기존 FE에서 사용하던 형식을 유지합니다.
    신규 개발에서는 TopicResponse 사용을 권장합니다.
    """
    pass


class RecommendationResponse(BaseModel):
    """
    추천 결과 조회 응답 (레거시 호환).

    기존 API 형식을 유지합니다.
    """
    channel_id: str
    recommendations: List[RecommendationItem]
    generated_at: datetime
    expires_at: datetime
    is_expired: bool


class RecommendationGenerateResponse(BaseModel):
    """추천 생성 응답 (레거시 호환)."""
    success: bool
    message: str
    data: Optional[RecommendationResponse] = None
