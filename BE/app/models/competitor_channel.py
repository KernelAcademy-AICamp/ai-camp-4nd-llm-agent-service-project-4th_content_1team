import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.db import Base


class CompetitorChannel(Base):
    """경쟁 유튜버 채널"""
    
    __tablename__ = "competitor_channels"
    
    # 기본 정보
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(String, nullable=False, unique=True, index=True)
    
    # YouTube 채널 정보
    title = Column(String, nullable=False)
    description = Column(Text)
    custom_url = Column(String)
    thumbnail_url = Column(Text)
    
    # 통계
    subscriber_count = Column(Integer, default=0)
    view_count = Column(BigInteger, default=0)
    video_count = Column(Integer, default=0)
    
    # 추가 메타데이터
    topic_categories = Column(JSONB)  # YouTube topicDetails
    keywords = Column(Text)  # 채널 키워드
    country = Column(String)
    published_at = Column(DateTime(timezone=True))  # 채널 생성일
    
    # AI 분석 결과 (나중에 채울 수 있음)
    strengths = Column(JSONB)  # 강점 리스트
    channel_personality = Column(Text)  # 채널 성격
    target_audience = Column(Text)  # 시청자 타겟
    content_style = Column(Text)  # 콘텐츠 스타일
    analysis_json = Column(JSONB)  # 추가 분석 데이터
    
    # 추가 정보
    raw_data = Column(JSONB)  # YouTube API 원본 응답
    
    # 메타
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reference_channel_id = Column(String, ForeignKey("youtube_channels.channel_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    analyzed_at = Column(DateTime(timezone=True))  # AI 분석 시간
    
    # 관계
    user = relationship("User")
    reference_channel = relationship("YouTubeChannel", foreign_keys=[reference_channel_id])
    recent_videos = relationship("CompetitorRecentVideo", back_populates="competitor_channel", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<CompetitorChannel(id={self.id}, title={self.title}, subscribers={self.subscriber_count})>"
