"""
채널 페르소나 모델

채널 분석을 통해 생성된 페르소나 정보를 저장합니다.
규칙 기반 해석 + LLM 해석의 종합 결과입니다.
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.db import Base


class ChannelPersona(Base):
    """채널 페르소나."""

    __tablename__ = "channel_personas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(
        String,
        ForeignKey("youtube_channels.channel_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # =========================================================================
    # 종합 서술
    # =========================================================================
    persona_summary = Column(Text, nullable=True)  # 자연스러운 3~5문장 요약

    # =========================================================================
    # 정체성
    # =========================================================================
    one_liner = Column(String, nullable=True)       # 한 줄 정의 (예: "노션 전문 생산성 유튜버")
    main_topics = Column(JSONB, nullable=True)      # ["노션", "생산성", "업무자동화"]
    content_style = Column(String, nullable=True)   # "깔끔한 화면 녹화 + 차분한 설명"
    differentiator = Column(String, nullable=True)  # 차별화 포인트

    # =========================================================================
    # 타겟 시청자
    # =========================================================================
    target_audience = Column(String, nullable=True)   # "20대 중반~30대 초반 직장인 남성"
    audience_needs = Column(String, nullable=True)    # "업무 효율화, 반복 작업 줄이기"

    # =========================================================================
    # 성공 공식
    # =========================================================================
    hit_topics = Column(JSONB, nullable=True)         # ["노션 활용법", "생산성 팁"]
    title_patterns = Column(JSONB, nullable=True)     # ["~하는 법", "N가지 팁"]
    optimal_duration = Column(String, nullable=True)  # "10~15분"

    # =========================================================================
    # 성장 기회
    # =========================================================================
    growth_opportunities = Column(JSONB, nullable=True)  # ["AI 도구 활용", "원격근무"]

    # =========================================================================
    # 근거 (투명성)
    # =========================================================================
    evidence = Column(JSONB, nullable=True)  # [{signal, interpretation, category}, ...]

    # =========================================================================
    # 카테고리 (주제 추천 필터용)
    # =========================================================================
    # 채널 분석에서 자동 추출
    analyzed_categories = Column(JSONB, nullable=True)      # ["Technology", "Education"]
    analyzed_subcategories = Column(JSONB, nullable=True)   # ["AI", "Programming", "Career"]

    # 사용자가 온보딩에서 선택
    preferred_categories = Column(JSONB, nullable=True)     # ["Technology"]
    preferred_subcategories = Column(JSONB, nullable=True)  # ["AI", "Software"]

    # =========================================================================
    # 매칭용 키워드
    # =========================================================================
    topic_keywords = Column(JSONB, nullable=True)    # 주제 추천 필터용
    style_keywords = Column(JSONB, nullable=True)    # 스타일 매칭용

    # =========================================================================
    # 메타
    # =========================================================================
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    channel = relationship("YouTubeChannel", backref="persona", uselist=False)

    __table_args__ = (
        Index("ix_channel_personas_channel_id", "channel_id"),
    )

    def to_dict(self) -> dict:
        """페르소나를 딕셔너리로 변환."""
        return {
            "id": str(self.id),
            "channel_id": self.channel_id,
            "persona_summary": self.persona_summary,
            "one_liner": self.one_liner,
            "main_topics": self.main_topics,
            "content_style": self.content_style,
            "differentiator": self.differentiator,
            "target_audience": self.target_audience,
            "audience_needs": self.audience_needs,
            "hit_topics": self.hit_topics,
            "title_patterns": self.title_patterns,
            "optimal_duration": self.optimal_duration,
            "growth_opportunities": self.growth_opportunities,
            "evidence": self.evidence,
            "analyzed_categories": self.analyzed_categories,
            "analyzed_subcategories": self.analyzed_subcategories,
            "preferred_categories": self.preferred_categories,
            "preferred_subcategories": self.preferred_subcategories,
            "topic_keywords": self.topic_keywords,
            "style_keywords": self.style_keywords,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
