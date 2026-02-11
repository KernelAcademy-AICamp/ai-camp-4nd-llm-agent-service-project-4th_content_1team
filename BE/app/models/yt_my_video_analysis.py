"""
내 채널 영상별 분석 모델

페르소나 생성 시 내 채널 영상의 자막을 분석한 결과를 저장합니다.
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


class YTMyVideoAnalysis(Base):
    """내 채널 영상별 자막 기반 LLM 분석 결과."""

    __tablename__ = "yt_my_video_analysis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(
        String,
        ForeignKey("youtube_channels.channel_id", ondelete="CASCADE"),
        nullable=False,
    )
    video_id = Column(
        UUID(as_uuid=True),
        ForeignKey("yt_channel_videos.id", ondelete="CASCADE"),
        nullable=False,
    )

    # =========================================================================
    # 분석 결과
    # =========================================================================
    video_type = Column(String, nullable=True)           # "정보형", "튜토리얼형", "리뷰형" 등
    content_structure = Column(Text, nullable=True)      # "인트로→문제제기→해결책→CTA"
    tone_manner = Column(Text, nullable=True)            # "~거든요 체, 친근하지만 전문적"
    key_topics = Column(JSONB, nullable=True)            # ["React", "상태관리"]
    summary = Column(Text, nullable=True)                # 핵심 내용 요약 2~3문장
    strengths = Column(JSONB, nullable=True)             # ["실습 예제가 구체적"]
    weaknesses = Column(JSONB, nullable=True)            # ["후반부 급하게 마무리"]
    performance_insight = Column(Text, nullable=True)    # "자극적 제목+실용적 내용이 높은 조회수로"

    # =========================================================================
    # 시청자 반응 분석 (댓글 기반)
    # =========================================================================
    viewer_reactions = Column(JSONB, nullable=True)      # ["반응1", "반응2"]
    viewer_needs = Column(JSONB, nullable=True)          # ["니즈1", "니즈2"]
    performance_reason = Column(Text, nullable=True)     # "이 영상이 hit/low인 이유"

    # =========================================================================
    # 자막 원본 (캐싱용)
    # =========================================================================
    transcript_text = Column(Text, nullable=True)

    # =========================================================================
    # 메타
    # =========================================================================
    selection_reason = Column(String, nullable=False)    # "hit" / "low" / "latest"
    analyzed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # =========================================================================
    # Relationships
    # =========================================================================
    channel = relationship("YouTubeChannel", backref="video_analyses")
    video = relationship("YTChannelVideo", backref="analysis")

    __table_args__ = (
        Index("ix_yt_my_video_analysis_channel_id", "channel_id"),
        Index("ix_yt_my_video_analysis_video_id", "video_id"),
    )

    def to_dict(self) -> dict:
        """분석 결과를 딕셔너리로 변환."""
        return {
            "id": str(self.id),
            "channel_id": self.channel_id,
            "video_id": str(self.video_id),
            "video_type": self.video_type,
            "content_structure": self.content_structure,
            "tone_manner": self.tone_manner,
            "key_topics": self.key_topics,
            "summary": self.summary,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "performance_insight": self.performance_insight,
            "viewer_reactions": self.viewer_reactions,
            "viewer_needs": self.viewer_needs,
            "performance_reason": self.performance_reason,
            "transcript_text": self.transcript_text,
            "selection_reason": self.selection_reason,
            "analyzed_at": self.analyzed_at.isoformat() if self.analyzed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
