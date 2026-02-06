import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.db import Base


class CompetitorChannelVideo(Base):
    """경쟁 유튜버의 최신 영상"""
    
    __tablename__ = "competitor_channel_videos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competitor_channel_id = Column(
        UUID(as_uuid=True),
        ForeignKey("competitor_channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # YouTube 영상 정보
    video_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    thumbnail_url = Column(Text)
    published_at = Column(DateTime(timezone=True))
    duration = Column(String)  # ISO 8601 (PT15M30S)
    
    # 통계
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    
    # AI 분석 결과
    analysis_summary = Column(Text)  # 핵심 내용
    analysis_strengths = Column(JSONB)  # 영상 장점 (리스트)
    analysis_weaknesses = Column(JSONB)  # 영상 부족한 점 (리스트)
    audience_reaction = Column(Text)  # 시청자 반응
    
    # 메타
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    analyzed_at = Column(DateTime(timezone=True))  # 분석 시간
    
    # 관계
    competitor_channel = relationship("CompetitorChannel", back_populates="videos")
    
    def __repr__(self):
        return f"<CompetitorChannelVideo(id={self.id}, video_id={self.video_id}, title={self.title})>"
