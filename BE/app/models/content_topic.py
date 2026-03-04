"""
콘텐츠 주제 모델

채널 맞춤 추천(주간)과 트렌드 기반 추천(일간)을 개별 관리합니다.
각 주제는 독립적인 Row로 저장되어 상태 관리 및 스크립트 연동이 가능합니다.
"""
import uuid
from datetime import datetime, timedelta, date
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Date,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.db import Base


# =============================================================================
# 만료 시간 헬퍼
# =============================================================================

def default_channel_expires_at():
    """채널 맞춤 추천 만료: 7일 후."""
    return datetime.utcnow() + timedelta(days=7)


def default_trend_expires_at():
    """트렌드 추천 만료: 1일 후."""
    return datetime.utcnow() + timedelta(days=1)


# =============================================================================
# 채널 맞춤 추천 (주간)
# =============================================================================

class ChannelTopic(Base):
    """
    채널 맞춤 추천 주제 (주간 갱신)

    채널의 페르소나와 관심 카테고리를 기반으로 추천된 주제입니다.
    10개 생성 → 5개 표시(shown) / 5개 대기(queued)
    """
    __tablename__ = "channel_topics"

    # =========================================================================
    # 기본 정보
    # =========================================================================
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(
        String,
        ForeignKey("youtube_channels.channel_id", ondelete="CASCADE"),
        nullable=False,
    )

    # =========================================================================
    # 순위 및 표시 상태
    # =========================================================================
    rank = Column(Integer, nullable=False)  # 1~10 (낮을수록 우선)
    display_status = Column(
        String(20),
        nullable=False,
        default="queued"
    )  # shown(표시중) / queued(대기) / skipped(건너뜀)

    # =========================================================================
    # 콘텐츠 정보 (Gemini 추천 결과)
    # =========================================================================
    title = Column(String(200), nullable=False)
    based_on_topic = Column(String(100), nullable=True)
    trend_basis = Column(Text, nullable=True)
    recommendation_reason = Column(Text, nullable=True)
    urgency = Column(String(20), default="normal")  # urgent / normal / evergreen

    # 검색 키워드 (단일 배열로 통합)
    search_keywords = Column(JSONB, default=list)  # ["키워드1", "키워드2", ...]

    # 추가 정보
    content_angles = Column(JSONB, default=list)   # ["관점1", "관점2"]
    thumbnail_idea = Column(Text, nullable=True)

    # =========================================================================
    # 상태 관리
    # =========================================================================
    status = Column(
        String(20),
        nullable=False,
        default="recommended"
    )  # recommended / confirmed / scripting / completed

    scheduled_date = Column(Date, nullable=True)  # 확정 시 예정 날짜 (drag&drop용)

    # =========================================================================
    # 연결 (향후 확장)
    # =========================================================================
    script_id = Column(UUID(as_uuid=True), nullable=True)  # 스크립트 FK (나중에)

    # =========================================================================
    # 시간 정보
    # =========================================================================
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, default=default_channel_expires_at)
    confirmed_at = Column(DateTime, nullable=True)  # 확정 시점
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # =========================================================================
    # 인덱스
    # =========================================================================
    __table_args__ = (
        Index("ix_channel_topics_channel_id", "channel_id"),
        Index("ix_channel_topics_display_status", "display_status"),
        Index("ix_channel_topics_status", "status"),
    )

    def is_expired(self) -> bool:
        """추천이 만료되었는지 확인."""
        return datetime.utcnow() > self.expires_at

    def to_dict(self) -> dict:
        """딕셔너리로 변환."""
        return {
            "id": str(self.id),
            "channel_id": self.channel_id,
            "rank": self.rank,
            "display_status": self.display_status,
            "title": self.title,
            "based_on_topic": self.based_on_topic,
            "trend_basis": self.trend_basis,
            "recommendation_reason": self.recommendation_reason,
            "urgency": self.urgency,
            "search_keywords": self.search_keywords,
            "content_angles": self.content_angles,
            "thumbnail_idea": self.thumbnail_idea,
            "status": self.status,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
        }


# =============================================================================
# 트렌드 기반 추천 (일간)
# =============================================================================

class TrendTopic(Base):
    """
    트렌드 기반 추천 주제 (일간 갱신)

    실시간 트렌드와 핫이슈를 기반으로 추천된 주제입니다.
    10개 생성 → 2개 표시(shown) / 8개 대기(queued)
    """
    __tablename__ = "trend_topics"

    # =========================================================================
    # 기본 정보
    # =========================================================================
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(
        String,
        ForeignKey("youtube_channels.channel_id", ondelete="CASCADE"),
        nullable=False,
    )

    # =========================================================================
    # 순위 및 표시 상태
    # =========================================================================
    rank = Column(Integer, nullable=False)  # 1~10
    display_status = Column(
        String(20),
        nullable=False,
        default="queued"
    )  # shown / queued / skipped

    # =========================================================================
    # 콘텐츠 정보 (Gemini 추천 결과)
    # =========================================================================
    title = Column(String(200), nullable=False)
    based_on_topic = Column(String(100), nullable=True)
    trend_basis = Column(Text, nullable=True)
    recommendation_reason = Column(Text, nullable=True)
    recommendation_type = Column(
        String(20), nullable=True,
        comment="viewer_needs | hit_pattern | trend_driven",
    )  # 추천 관점 태그
    recommendation_direction = Column(
        Text, nullable=True,
        comment="영상 방향성 제안 멘트",
    )  # "구독자들이 원하는 AI 입문 콘텐츠, 이 주제로 화답해보는 건 어때요?"
    source_layer = Column(
        String(10), nullable=True,
        comment="core | adjacent",
    )  # 핵심 트렌드 vs 확장 트렌드

    urgency = Column(String(20), default="urgent")  # 트렌드는 기본 urgent

    # 검색 키워드 (단일 배열로 통합)
    search_keywords = Column(JSONB, default=list)  # ["키워드1", "키워드2", ...]

    # 추가 정보
    content_angles = Column(JSONB, default=list)
    thumbnail_idea = Column(Text, nullable=True)

    # =========================================================================
    # 상태 관리
    # =========================================================================
    status = Column(
        String(20),
        nullable=False,
        default="recommended"
    )  # recommended / confirmed / scripting / completed

    scheduled_date = Column(Date, nullable=True)

    # =========================================================================
    # 연결
    # =========================================================================
    script_id = Column(UUID(as_uuid=True), nullable=True)

    # =========================================================================
    # 시간 정보
    # =========================================================================
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, default=default_trend_expires_at)
    confirmed_at = Column(DateTime, nullable=True)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # =========================================================================
    # 인덱스
    # =========================================================================
    __table_args__ = (
        Index("ix_trend_topics_channel_id", "channel_id"),
        Index("ix_trend_topics_display_status", "display_status"),
        Index("ix_trend_topics_status", "status"),
    )

    def is_expired(self) -> bool:
        """추천이 만료되었는지 확인."""
        return datetime.utcnow() > self.expires_at

    def to_dict(self) -> dict:
        """딕셔너리로 변환."""
        return {
            "id": str(self.id),
            "channel_id": self.channel_id,
            "rank": self.rank,
            "display_status": self.display_status,
            "title": self.title,
            "based_on_topic": self.based_on_topic,
            "trend_basis": self.trend_basis,
            "recommendation_reason": self.recommendation_reason,
            "recommendation_type": self.recommendation_type,
            "recommendation_direction": self.recommendation_direction,
            "source_layer": self.source_layer,
            "urgency": self.urgency,
            "search_keywords": self.search_keywords,
            "content_angles": self.content_angles,
            "thumbnail_idea": self.thumbnail_idea,
            "status": self.status,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
        }
