import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Date,
    Integer,
    BigInteger,
    ForeignKey,
    Float,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.db import Base


class YouTubeChannel(Base):
    """YouTube 채널 기본 정보."""

    __tablename__ = "youtube_channels"

    channel_id = Column(String, primary_key=True)  # youtube_channel_id
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=True)
    description = Column(String, nullable=True)
    country = Column(String, nullable=True)
    keywords = Column(String, nullable=True)
    raw_channel_json = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    stats = relationship("YTChannelStatsDaily", back_populates="channel", cascade="all, delete-orphan")
    topics = relationship("YTChannelTopic", back_populates="channel", cascade="all, delete-orphan")
    audiences = relationship("YTAudienceDaily", back_populates="channel", cascade="all, delete-orphan")
    geos = relationship("YTGeoDaily", back_populates="channel", cascade="all, delete-orphan")


class YTChannelStatsDaily(Base):
    """채널 일일 통계."""

    __tablename__ = "yt_channel_stats_daily"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(String, ForeignKey("youtube_channels.channel_id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, default=date.today)

    subscriber_count = Column(Integer, nullable=True)
    view_count = Column(BigInteger, nullable=True)
    video_count = Column(Integer, nullable=True)
    comment_count = Column(Integer, nullable=True)
    raw_stats_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    channel = relationship("YouTubeChannel", back_populates="stats")

    __table_args__ = (
        UniqueConstraint("channel_id", "date", name="uq_stats_channel_date"),
        Index("ix_stats_channel_id", "channel_id"),
        Index("ix_stats_date", "date"),
    )


class YTChannelTopic(Base):
    """채널 토픽."""

    __tablename__ = "yt_channel_topics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(String, ForeignKey("youtube_channels.channel_id", ondelete="CASCADE"), nullable=False)
    topic_category_url = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    channel = relationship("YouTubeChannel", back_populates="topics")

    __table_args__ = (
        UniqueConstraint("channel_id", "topic_category_url", name="uq_topics_channel_topic"),
        Index("ix_topics_channel_id", "channel_id"),
    )


class YTAudienceDaily(Base):
    """연령/성별별 일일 시청자 통계."""

    __tablename__ = "yt_audience_daily"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(String, ForeignKey("youtube_channels.channel_id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    age_group = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    viewer_percentage = Column(Float, nullable=True)
    views = Column(Integer, nullable=True)
    watch_time_minutes = Column(Float, nullable=True)
    raw_report_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    channel = relationship("YouTubeChannel", back_populates="audiences")

    __table_args__ = (
        UniqueConstraint("channel_id", "date", "age_group", "gender", name="uq_audience_channel_date_age_gender"),
        Index("ix_audience_channel_id", "channel_id"),
        Index("ix_audience_date", "date"),
    )


class YTGeoDaily(Base):
    """국가별 일일 시청자 통계."""

    __tablename__ = "yt_geo_daily"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_id = Column(String, ForeignKey("youtube_channels.channel_id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    country = Column(String, nullable=False)
    viewer_percentage = Column(Float, nullable=True)
    views = Column(Integer, nullable=True)
    watch_time_minutes = Column(Float, nullable=True)
    raw_report_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    channel = relationship("YouTubeChannel", back_populates="geos")

    __table_args__ = (
        UniqueConstraint("channel_id", "date", "country", name="uq_geo_channel_date_country"),
        Index("ix_geo_channel_id", "channel_id"),
        Index("ix_geo_date", "date"),
    )
