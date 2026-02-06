import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.db import Base


class CompetitorRecentVideo(Base):
    """경쟁 유튜버의 최신 영상"""

    __tablename__ = "competitor_recent_videos"
    
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
    competitor_channel = relationship("CompetitorChannel", back_populates="recent_videos")
    comments = relationship("RecentVideoComment", back_populates="video", cascade="all, delete-orphan")
    caption = relationship("RecentVideoCaption", back_populates="video", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CompetitorRecentVideo(id={self.id}, video_id={self.video_id}, title={self.title})>"


class RecentVideoComment(Base):
    """경쟁 유튜버 최신 영상의 댓글 샘플"""

    __tablename__ = "recent_video_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recent_video_id = Column(
        UUID(as_uuid=True),
        ForeignKey("competitor_recent_videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 댓글 정보
    comment_id = Column(String)  # YouTube 댓글 ID
    text = Column(Text, nullable=False)
    author_name = Column(String)
    author_thumbnail = Column(Text)
    likes = Column(Integer, default=0)
    published_at = Column(DateTime(timezone=True))

    # 메타
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # 관계
    video = relationship("CompetitorRecentVideo", back_populates="comments")

    def __repr__(self):
        return f"<RecentVideoComment(id={self.id}, likes={self.likes})>"


class RecentVideoCaption(Base):
    """경쟁 유튜버 최신 영상의 자막"""

    __tablename__ = "recent_video_captions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recent_video_id = Column(
        UUID(as_uuid=True),
        ForeignKey("competitor_recent_videos.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # 자막 데이터 (JSON)
    segments_json = Column(JSONB, nullable=False)

    # 메타
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # 관계
    video = relationship("CompetitorRecentVideo", back_populates="caption")

    def __repr__(self):
        return f"<RecentVideoCaption(id={self.id}, recent_video_id={self.recent_video_id})>"
