"""
주제 추천 모델

트렌드 기반 추천 결과를 저장합니다.
하루 단위로 갱신되며, 대시보드에서 조회됩니다.
"""
import uuid
from datetime import datetime, timedelta
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.db import Base


def default_expires_at():
    """기본 만료 시간: 24시간 후."""
    return datetime.utcnow() + timedelta(hours=24)


class TopicRecommendation(Base):
    """주제 추천 결과."""

    __tablename__ = "topic_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(
        String,
        ForeignKey("youtube_channels.channel_id", ondelete="CASCADE"),
        unique=True,  # 채널당 1개의 추천 결과만 저장
        nullable=False,
    )

    # =========================================================================
    # 추천 결과
    # =========================================================================
    recommendations = Column(JSONB, nullable=False, default=list)
    # [
    #   {
    #     "title": "클릭 유도 제목",
    #     "based_on_topic": "AI Robot",
    #     "trend_basis": "GPT-5 발표로 AI 관심 급증",
    #     "recommendation_reason": "AI 개발 채널에 적합",
    #     "search_keywords": {"youtube": [...], "google": [...]},
    #     "content_angles": ["관점1", "관점2"],
    #     "thumbnail_idea": "썸네일 아이디어",
    #     "urgency": "urgent|normal|evergreen"
    #   },
    #   ...
    # ]

    # =========================================================================
    # 메타데이터
    # =========================================================================
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, default=default_expires_at)

    # 생성에 사용된 페르소나 정보 (디버깅/추적용)
    persona_snapshot = Column(JSONB, nullable=True)
    # {
    #   "preferred_categories": ["Technology"],
    #   "preferred_subcategories": ["AI", "Software"]
    # }

    def is_expired(self) -> bool:
        """추천 결과가 만료되었는지 확인."""
        return datetime.utcnow() > self.expires_at
