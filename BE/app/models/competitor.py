import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.db import Base


class CompetitorCollection(Base):
    """경쟁 영상 컬렉션."""

    __tablename__ = "competitor_collections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_request_id = Column(UUID(as_uuid=True), nullable=True)
    created_by_run_id = Column(UUID(as_uuid=True), nullable=True)
    policy_json = Column(JSONB, nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    videos = relationship(
        "CompetitorVideo",
        back_populates="collection",
        cascade="all, delete-orphan",
    )


class CompetitorVideo(Base):
    """경쟁 영상 개별 항목."""

    __tablename__ = "competitor_videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("competitor_collections.id", ondelete="CASCADE"),
        nullable=False,
    )
    youtube_video_id = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    channel_title = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    duration_sec = Column(Integer, nullable=True)
    metrics_json = Column(JSONB, nullable=True)
    caption_meta_json = Column(JSONB, nullable=True)
    selection_json = Column(JSONB, nullable=True)

    collection = relationship("CompetitorCollection", back_populates="videos")
    comment_samples = relationship(
        "VideoCommentSample",
        back_populates="video",
        cascade="all, delete-orphan",
    )


class VideoCommentSample(Base):
    """비디오 댓글 샘플."""

    __tablename__ = "video_comment_samples"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competitor_video_id = Column(
        UUID(as_uuid=True),
        ForeignKey("competitor_videos.id", ondelete="CASCADE"),
        nullable=False,
    )
    comment_id = Column(Text, nullable=True)
    text = Column(Text, nullable=False)
    likes = Column(Integer, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

    video = relationship("CompetitorVideo", back_populates="comment_samples")
