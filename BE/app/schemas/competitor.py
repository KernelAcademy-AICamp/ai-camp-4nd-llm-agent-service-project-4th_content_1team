from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID


class CompetitorVideoIn(BaseModel):
    """저장할 개별 영상 정보."""

    youtube_video_id: str
    url: str
    title: str
    channel_title: Optional[str] = None
    published_at: Optional[datetime] = None
    duration_sec: Optional[int] = None
    metrics_json: Optional[dict] = None
    caption_meta_json: Optional[dict] = None
    selection_json: Optional[dict] = None


class CompetitorSaveRequest(BaseModel):
    """경쟁 영상 저장 요청."""

    policy_json: Optional[dict] = None
    videos: List[CompetitorVideoIn] = Field(..., min_length=1)


class CompetitorSaveResponse(BaseModel):
    """경쟁 영상 저장 응답."""

    collection_id: UUID
    generated_at: datetime
    video_count: int
