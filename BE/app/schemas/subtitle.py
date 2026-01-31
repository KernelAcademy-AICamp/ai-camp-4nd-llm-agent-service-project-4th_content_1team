from pydantic import BaseModel, Field
from typing import List, Optional


# ── Request ──

class SubtitleFetchRequest(BaseModel):
    """YouTube 자막 조회 요청"""
    video_ids: List[str] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="YouTube 영상 ID 리스트 (최대 20개)"
    )
    languages: List[str] = Field(
        default=["ko", "en"],
        description="우선순위 언어 코드 리스트"
    )


# ── Response ──

class SubtitleCue(BaseModel):
    """자막 큐 (타임스탬프 포함)"""
    start: float
    end: float
    text: str


class SubtitleTrack(BaseModel):
    """단일 언어 트랙"""
    language_code: str
    language_name: str
    is_auto_generated: bool = False
    cues: List[SubtitleCue] = []


class SubtitleResult(BaseModel):
    """영상 1개의 자막 결과"""
    video_id: str
    status: str  # "success" | "no_subtitle" | "failed"
    source: Optional[str] = None
    tracks: List[SubtitleTrack] = []
    no_captions: bool = False
    error: Optional[str] = None


class SubtitleFetchResponse(BaseModel):
    """자막 조회 응답"""
    results: List[SubtitleResult]
