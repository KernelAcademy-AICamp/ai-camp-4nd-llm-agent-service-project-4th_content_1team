import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.db import Base


class VideoContentAnalysis(Base):
    """경쟁 영상 자막 기반 LLM 분석 결과."""

    __tablename__ = "video_content_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competitor_video_id = Column(
        UUID(as_uuid=True),
        ForeignKey("competitor_videos.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    summary = Column(Text, nullable=False)
    strengths = Column(JSONB, nullable=False)  # List[str]
    weaknesses = Column(JSONB, nullable=False)  # List[str]
    analyzed_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    video = relationship("CompetitorVideo", back_populates="content_analysis")
