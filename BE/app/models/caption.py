import uuid
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.db import Base


class VideoCaption(Base):
    """영상 자막 데이터."""

    __tablename__ = "video_captions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competitor_video_id = Column(
        UUID(as_uuid=True),
        ForeignKey("competitor_videos.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    segments_json = Column(JSONB, nullable=False)

    video = relationship("CompetitorVideo", backref="caption")
