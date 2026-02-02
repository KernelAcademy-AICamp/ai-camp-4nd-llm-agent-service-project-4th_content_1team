"""
채널 영상 메타데이터 및 성과 통계 모델

사용자 채널의 영상 목록과 성과 데이터를 저장합니다.
페르소나 생성을 위한 분석에 사용됩니다.
"""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Date,
    Integer,
    BigInteger,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.db import Base


class YTChannelVideo(Base):
    """채널 영상 메타데이터."""

    __tablename__ = "yt_channel_videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(
        String,
        ForeignKey("youtube_channels.channel_id", ondelete="CASCADE"),
        nullable=False,
    )
    video_id = Column(String, nullable=False)  # YouTube video ID
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)  # 영상 길이 (초)
    tags = Column(JSONB, nullable=True)  # ["태그1", "태그2"]
    thumbnail_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    channel = relationship("YouTubeChannel", backref="videos")
    stats = relationship(
        "YTVideoStats",
        back_populates="video",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("channel_id", "video_id", name="uq_channel_video"),
        Index("ix_channel_videos_channel_id", "channel_id"),
        Index("ix_channel_videos_published_at", "published_at"),
    )


class YTVideoStats(Base):
    """영상별 성과 통계."""

    __tablename__ = "yt_video_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_id = Column(
        UUID(as_uuid=True),
        ForeignKey("yt_channel_videos.id", ondelete="CASCADE"),
        nullable=False,
    )
    date = Column(Date, nullable=False, default=date.today)
    view_count = Column(BigInteger, nullable=True)
    like_count = Column(Integer, nullable=True)
    comment_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    video = relationship("YTChannelVideo", back_populates="stats")

    __table_args__ = (
        UniqueConstraint("video_id", "date", name="uq_video_stats_date"),
        Index("ix_video_stats_video_id", "video_id"),
        Index("ix_video_stats_date", "date"),
    )
